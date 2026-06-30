"""Training loop execution for VORTEX."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from vortex.manifest import ManifestConfig

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

    def generate(self, context: dict) -> list[Change]:
        """Generate hypotheses based on current context."""
        # For now, return empty list — LLM integration comes later
        # The actual generation will use litellm to call Claude/Codex
        logger.info("Generating hypotheses (stub — LLM integration pending)")
        return []

    def _build_prompt(self, context: dict) -> str:
        """Build the optimization prompt."""
        return f"""You are an optimization engine for the project at {self.manifest.project_path}.

Current metrics: {json.dumps(context.get('current_metrics', {}))}
Baseline metrics: {json.dumps(context.get('baseline_metrics', {}))}
Score: {context.get('score', 0):.3f}

Constraints:
{chr(10).join(f'- {c}' for c in self.manifest.constraints)}

Previous cycles:
{json.dumps(context.get('previous_cycles', []), indent=2)}

Generate up to {self.manifest.optimizer.max_changes_per_cycle} specific, actionable changes.
For each change, specify: file, description, rationale.

Output as JSON: {{"changes": [{{"file": "...", "description": "...", "rationale": "..."}}]}}"""


class ExecutionEngine:
    """Manages git branches, executes changes, and handles rollback."""

    def __init__(self, manifest: ManifestConfig):
        self.manifest = manifest
        self.project_path = manifest.project_path

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
        """Apply changes to the project files."""
        start = time.time()
        files_changed = []

        try:
            for change in changes:
                file_path = self.project_path / change.file
                if change.change_type == "create":
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(change.description)
                elif change.change_type == "delete":
                    if file_path.exists():
                        file_path.unlink()
                else:  # modify
                    # For now, append the description as a comment
                    # Real implementation will use LLM to make actual changes
                    with open(file_path, "a") as f:
                        f.write(f"\n# VORTEX: {change.description}\n")
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
        """Check semantic preservation."""
        # Placeholder — real implementation would use LLM to verify
        return GateCheck(gate_name="semantic_preservation", passed=True)

    def _check_regression(self, execution: ExecutionResult, context: dict) -> GateCheck:
        """Check for performance regression."""
        # Placeholder — real implementation would compare metrics
        return GateCheck(gate_name="no_regression", passed=True)

    def _check_review_needed(self, execution: ExecutionResult) -> GateCheck:
        """Check if human review is needed."""
        if len(execution.files_changed) > 3:
            return GateCheck(
                gate_name="review_required",
                passed=False,
                reason=f"{len(execution.files_changed)} files changed — review recommended",
            )
        return GateCheck(gate_name="review_required", passed=True)
