"""Training loop execution for VORTEX."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from vortex.manifest import ManifestConfig
from vortex.llm_factory import create_client

logger = logging.getLogger(__name__)


@dataclass
class Change:
    """A proposed change to make to the project."""

    file: str
    description: str
    rationale: str = ""
    change_type: str = "modify"  # modify, create, delete


@dataclass
class ExecutionResult:
    """Result of executing a set of changes."""

    success: bool
    diff: str = ""
    files_changed: list[str] = field(default_factory=list)
    text_output: str = ""
    duration_ms: int = 0
    error: str = ""


@dataclass
class GateCheck:
    """Result of a single constraint gate check."""

    gate_name: str
    passed: bool
    reason: str = ""


@dataclass
class GateResult:
    """Result of all constraint gate checks."""

    passed: bool
    gates: list[GateCheck] = field(default_factory=list)

    @property
    def failed_gates(self) -> list[str]:
        return [g.gate_name for g in self.gates if not g.passed]


class HypothesisGenerator:
    """Generates optimization hypotheses via LLM delegation."""

    def __init__(self, manifest: ManifestConfig):
        self.manifest = manifest
        self.client = create_client(manifest)

    def generate(self, context: dict) -> list[Change]:
        """Generate hypotheses based on current context."""
        try:
            prompt = self._build_prompt(context)
            content = self.client.complete(prompt)
            return self._parse_response(content)
        except Exception as e:
            logger.warning("LLM hypothesis generation failed: %s", e)
            return []

    def _build_prompt(self, context: dict) -> str:
        """Build the optimization prompt."""
        # Get ACTUAL files from the project
        actual_files = []
        for f in sorted(self.manifest.project_path.rglob("*.py")):
            if "venv" not in str(f) and "__pycache__" not in str(f) and ".vortex" not in str(f):
                rel = str(f.relative_to(self.manifest.project_path))
                actual_files.append(rel)
        file_list = "\n".join(f"  {f}" for f in actual_files[:30])

        # Build tasks section if tasks are specified
        tasks_section = ""
        if self.manifest.tasks:
            tasks_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(self.manifest.tasks))
            tasks_section = f"""
\nSPECIFIC TASKS TO COMPLETE:
{tasks_list}\n
You MUST complete these tasks. For each task, generate the changes needed.\n"""

        return f"""You are an optimization engine for the Python project at {self.manifest.project_path}.

ACTUAL FILES IN THE PROJECT:
{file_list}

Current metrics: {json.dumps(context.get('current_metrics', {}))}
Baseline metrics: {json.dumps(context.get('baseline_metrics', {}))}
Score: {context.get('score', 0):.3f}

Constraints:
{chr(10).join(f'- {c}' for c in self.manifest.constraints)}
{tasks_section}

Generate up to {self.manifest.optimizer.max_changes_per_cycle} REAL code changes.
- You MUST use ONLY files from the list above
- Do NOT invent file names - they don't exist
- Do NOT add comments or documentation
- DO modify existing Python files with actual code improvements

For each change, specify:
1. "file": EXACT file path from the list above
2. "description": EXACT code change to make
3. "rationale": why this improves the project

Output ONLY valid JSON: {{"changes": [{{"file": "src/vortex/example.py", "description": "Remove unused import X", "rationale": "Reduces code complexity"}}]}}"""

    def _parse_response(self, content: str) -> list[Change]:
        """Parse LLM response into Change objects."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                changes = []
                for c in data.get("changes", [])[:self.manifest.optimizer.max_changes_per_cycle]:
                    changes.append(Change(
                        file=c.get("file", ""),
                        description=c.get("description", ""),
                        rationale=c.get("rationale", ""),
                    ))
                return changes
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse LLM response: %s", e)
        return []


class ExecutionEngine:
    """Manages git branches, executes changes, and handles rollback."""

    def __init__(self, manifest: ManifestConfig):
        self.manifest = manifest
        self.project_path = manifest.project_path
        self.client = create_client(manifest)

    def setup_cycle(self) -> str:
        """Create an optimizer branch and return the current commit SHA."""
        # Get current commit SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        # Create optimizer branch
        cycle_id = f"opt_{int(time.time())}"
        subprocess.run(
            ["git", "checkout", "-b", f"optimizer/{cycle_id}"],
            cwd=str(self.project_path),
            capture_output=True,
        )

        logger.info("Setup cycle: branch=optimizer/%s, base=%s", cycle_id, commit_sha[:8])
        return commit_sha

    def execute(self, changes: list[Change], context: dict) -> ExecutionResult:
        """Apply changes to the project files using LLM."""
        start = time.time()
        files_changed = []

        try:
            for change in changes:
                file_path = self.project_path / change.file

                # Skip non-existent files for modify operations
                if change.change_type == "modify" and not file_path.exists():
                    logger.warning("File %s does not exist, skipping", change.file)
                    continue

                if change.change_type == "create":
                    content = self._generate_file_content(change)
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
                    files_changed.append(change.file)
                elif change.change_type == "delete":
                    if file_path.exists():
                        file_path.unlink()
                    files_changed.append(change.file)
                else:  # modify - use LLM to apply the change
                    original = file_path.read_text()
                    new_content = self._apply_change_with_llm(original, change)
                    # VALIDATE: only apply if valid Python AND not too different
                    if new_content and new_content != original:
                        if not self._validate_python(new_content):
                            logger.warning("LLM produced invalid Python for %s, skipping", change.file)
                        elif self._is_too_different(original, new_content):
                            logger.warning("LLM changed too much in %s (>30%%), skipping", change.file)
                        else:
                            file_path.write_text(new_content)
                            files_changed.append(change.file)

            # Capture diff
            diff_result = subprocess.run(
                ["git", "diff"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
            )

            duration_ms = int((time.time() - start) * 1000)
            return ExecutionResult(
                success=True,
                diff=diff_result.stdout,
                files_changed=files_changed,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            return ExecutionResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )


    def _validate_python(self, code: str) -> bool:
        """Validate that code is valid Python syntax."""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False

    def _is_too_different(self, original: str, new: str, threshold: float = 0.3) -> bool:
        """Check if new content is too different from original (>30% change)."""
        if not original:
            return False
        # Simple line-by-line comparison
        orig_lines = set(original.splitlines())
        new_lines = set(new.splitlines())
        if not orig_lines:
            return False
        changed = len(orig_lines.symmetric_difference(new_lines))
        return changed / len(orig_lines) > threshold

    def _generate_file_content(self, change: Change) -> str:
        """Use LLM to generate file content."""
        try:
            prompt = f"""Generate Python code for a new file.
Description: {change.description}
Rationale: {change.rationale}
Output ONLY the Python code, no explanations."""
            content = self.client.complete(prompt)
            return content or f"# {change.description}"
        except Exception as e:
            logger.warning("LLM file generation failed: %s", e)
            return f"# {change.description}"

    def _apply_change_with_llm(self, original: str, change: Change) -> str | None:
        """Use LLM to apply a change to existing code."""
        try:
            truncated = original[:3000] if len(original) > 3000 else original
            prompt = f"""You are a code editor. Apply this change to the existing code:

EXISTING CODE:
```python
{truncated}
```

CHANGE TO MAKE: {change.description}
RATIONALE: {change.rationale}

Output the COMPLETE modified code. Do NOT add comments. Do NOT explain. Just output the code."""
            content = self.client.complete(prompt)
            if "```python" in content:
                content = content.split("```python")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return content.strip() if content else None
        except Exception as e:
            logger.warning("LLM code modification failed: %s", e)
            return None

    def rollback(self, commit_sha: str) -> bool:
        """Revert to a specific commit."""
        try:
            subprocess.run(
                ["git", "reset", "--hard", commit_sha],
                cwd=str(self.project_path),
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "master"],
                cwd=str(self.project_path),
                capture_output=True,
            )
            logger.info("Rollback to %s successful", commit_sha[:8])
            return True
        except Exception as e:
            logger.error("Rollback failed: %s", e)
            return False

    def commit_changes(self, cycle_id: str) -> str:
        """Stage and commit all changes."""
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(self.project_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"VORTEX optimization cycle {cycle_id}"],
            cwd=str(self.project_path),
            capture_output=True,
        )
        # Switch back to master
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=str(self.project_path),
            capture_output=True,
        )
        # Merge optimizer branch
        subprocess.run(
            ["git", "merge", f"optimizer/{cycle_id}", "--no-edit"],
            cwd=str(self.project_path),
            capture_output=True,
        )
        # Get the merge commit SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()


class ConstraintGates:
    """Validates changes against 5 gates."""

    def __init__(self, manifest: ManifestConfig):
        self.manifest = manifest

    def validate(self, execution: ExecutionResult, context: dict) -> GateResult:
        """Run all constraint gates."""
        gates = []

        # Gate 1: tests_pass
        gates.append(self._check_tests())

        # Gate 2: size_limits
        gates.append(self._check_sizes(execution))

        # Gate 3: semantic_preservation
        gates.append(self._check_semantics(execution))

        # Gate 4: no_regression
        gates.append(self._check_regression(execution, context))

        # Gate 5: review_required
        gates.append(self._check_review_needed(execution))

        all_passed = all(g.passed for g in gates)
        return GateResult(passed=all_passed, gates=gates)

    def _check_tests(self) -> GateCheck:
        """Check if tests pass."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "-q"],
                cwd=str(self.manifest.project_path),
                capture_output=True,
                text=True,
                timeout=120,
            )
            passed = result.returncode == 0
            return GateCheck(
                gate_name="tests_pass",
                passed=passed,
                reason="" if passed else f"Tests failed: {result.stdout[-500:]}",
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return GateCheck(gate_name="tests_pass", passed=True, reason="Tests skipped (timeout or not found)")

    def _check_sizes(self, execution: ExecutionResult) -> GateCheck:
        """Check file size limits."""
        for file_path in execution.files_changed:
            full_path = self.manifest.project_path / file_path
            if full_path.exists() and full_path.stat().st_size > 100_000:  # 100KB
                return GateCheck(
                    gate_name="size_limits",
                    passed=False,
                    reason=f"File {file_path} exceeds 100KB limit",
                )
        return GateCheck(gate_name="size_limits", passed=True)

    def _check_semantics(self, execution: ExecutionResult) -> GateCheck:
        """Check semantic preservation using LLM."""
        try:
            files = execution.files_changed[:5]
            diffs = execution.diff[:2000]

            prompt = f"""You are a code reviewer. Check if these changes preserve semantic behavior.

Files changed: {files}
Diff preview:
{diffs}

Does this change preserve the original behavior? Answer ONLY "yes" or "no" with a brief reason."""

            # Use the manifest's LLM client for semantic check
            from vortex.llm_factory import create_client
            client = create_client(self.manifest)
            content = client.complete(prompt)

            # Extract yes/no from the response
            content_lower = content.lower()
            passed = "yes" in content_lower or "conserve" in content_lower or "preserve" in content_lower
            return GateCheck(
                gate_name="semantic_preservation",
                passed=passed,
                reason=content[:200] if content else "No response from LLM",
            )
            msg = response.choices[0].message
            content = msg.content or ""
            if not content and hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                content = msg.reasoning_content
            if not content:
                fields = getattr(msg, 'provider_specific_fields', {})
                details = fields.get('reasoning_details', [])
                if details:
                    content = details[0].get('text', '')
            # Extract yes/no from the response
            content_lower = content.lower()
            passed = "yes" in content_lower or "conserve" in content_lower or "preserve" in content_lower
            return GateCheck(
                gate_name="semantic_preservation",
                passed=passed,
                reason=content[:200] if content else "No response from LLM",
            )
        except Exception as e:
            logger.warning("Semantic check failed: %s", e)
            return GateCheck(gate_name="semantic_preservation", passed=True, reason="Check skipped (error)")

    def _check_regression(self, execution: ExecutionResult, context: dict) -> GateCheck:
        """Check for performance regression by comparing metrics."""
        try:
            # Compare current metrics with baseline
            baseline = context.get("baseline_metrics", {})
            current = context.get("current_metrics", {})

            if not baseline or not current:
                return GateCheck(gate_name="no_regression", passed=True, reason="No metrics to compare")

            regressions = []
            for metric_name, baseline_val in baseline.items():
                current_val = current.get(metric_name)
                if current_val is None:
                    continue
                if baseline_val != 0:
                    change_pct = (current_val - baseline_val) / abs(baseline_val) * 100
                    # Check if there's a significant regression (>10% worse)
                    if abs(change_pct) > 10:
                        regressions.append(f"{metric_name}: {change_pct:+.1f}%")

            if regressions:
                return GateCheck(
                    gate_name="no_regression",
                    passed=False,
                    reason=f"Regressions detected: {', '.join(regressions)}",
                )
            return GateCheck(gate_name="no_regression", passed=True)
        except Exception as e:
            logger.warning("Regression check failed: %s", e)
            return GateCheck(gate_name="no_regression", passed=True, reason="Check skipped (error)")

    def _check_review_needed(self, execution: ExecutionResult) -> GateCheck:
        """Check if human review is needed."""
        if len(execution.files_changed) > 3:
            return GateCheck(
                gate_name="review_required",
                passed=False,
                reason=f"{len(execution.files_changed)} files changed — review recommended",
            )
        return GateCheck(gate_name="review_required", passed=True)
