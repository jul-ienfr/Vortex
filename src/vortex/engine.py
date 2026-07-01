"""Main optimization engine for VORTEX."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from vortex.convergence import ConvergenceConfig, ConvergenceDetector
from vortex.execution import Change, ExecutionEngine, ExecutionResult, HypothesisGenerator
from vortex.history import CycleHistory, CycleResult, ReflectionMemory
from vortex.manifest import ManifestConfig
from vortex.metrics import BaselineManager, MetricsCollector
from vortex.meta_orchestrator import MetaOrchestrator
from vortex.self_improve import PerformanceReport, SelfImprover
from vortex.skill_library import SkillLibrary
from vortex.tree_search import TreeSearch

logger = logging.getLogger(__name__)


class Optimizer:
    """Main optimization engine."""

    def __init__(self, manifest_path: Path, dry_run: bool = False):
        self.manifest = ManifestConfig.from_yaml(manifest_path)
        self.dry_run = dry_run

        # Core components
        self.collector = MetricsCollector(self.manifest)
        self.baseline = BaselineManager(self.manifest)
        self.generator = HypothesisGenerator(self.manifest)
        self.executor = ExecutionEngine(self.manifest)

        # Memory
        self.history = CycleHistory(self.manifest.project_path)
        self.reflections = ReflectionMemory(self.manifest.project_path)

        # Skills
        self.skills = SkillLibrary(self.manifest.project_path) if self.manifest.optimizer.skill_library_enabled else None

        # Tree search
        self.tree = TreeSearch(
            max_depth=3,
            branching_factor=self.manifest.optimizer.tree_search_branches,
        ) if self.manifest.optimizer.tree_search_branches > 1 else None

        # Self-improvement
        self.self_improver = SelfImprover(self.manifest.project_path) if self.manifest.optimizer.self_improve_enabled else None

        # Meta-orchestrator (Chef Architecte)
        self.orchestrator = MetaOrchestrator(self.manifest)

        # Convergence
        from vortex.convergence import ConvergenceConfig, ConvergenceDetector
        self.convergence = ConvergenceDetector(ConvergenceConfig(
            stagnation_limit=self.manifest.optimizer.convergence_stagnation_limit,
            window_size=self.manifest.optimizer.convergence_window_size,
            convergence_threshold=self.manifest.optimizer.convergence_threshold,
            target_score=self.manifest.optimizer.convergence_target_score,
            min_cycles=self.manifest.optimizer.convergence_min_cycles,
        ))

    def run(self, max_cycles: int | None = None) -> None:
        """Main optimization loop."""
        # Establish baseline
        if self.dry_run:
            baseline = self.baseline.load_baseline() or {}
            if not baseline:
                logger.info("Dry run: no baseline found, collecting...")
                baseline = self.baseline.establish_baseline(self.collector)
        else:
            baseline = self.baseline.establish_baseline(self.collector)

        logger.info("Baseline: %s", baseline)

        cycles = max_cycles or self.manifest.optimizer.max_cycles or float("inf")
        cycle_num = 0

        while cycle_num < cycles:
            # Check convergence
            if cycle_num >= self.convergence.config.min_cycles:
                should_stop, reason = self.convergence.should_stop()
                if should_stop:
                    logger.info("Stopping: %s", reason)
                    break

            # Run single cycle
            result = self._run_cycle(cycle_num, baseline)
            self.convergence.record_score(result.score_delta, cycle_num)

            # Update baseline if improved
            if result.score_delta > 0:
                baseline = result.post_metrics
                self.baseline.save_baseline(baseline)

            # Record history
            self.history.record(result)

            # Store reflection
            if result.reflection:
                self.reflections.store_reflection(
                    result.cycle_id,
                    result.reflection,
                    {"score_delta": result.score_delta, "decision": result.decision},
                )

            stats = self.convergence.get_stats()
            logger.info(
                "Cycle %d: score=%.3f, best=%.3f, status=%s",
                cycle_num, result.score_delta, stats["best_score"], stats["convergence_status"],
            )

            cycle_num += 1

        # Final summary
        stats = self.convergence.get_stats()
        logger.info(
            "Done after %d cycles. Best score: %.3f (cycle %d)",
            stats["total_cycles"], stats["best_score"], stats["best_cycle"],
        )

    def _generate_failure_reflection(self, changes: list[Change], old_score: float,
                                      new_score: float, old_deltas: dict, new_deltas: dict) -> str:
        """Generate a reflection about why a cycle failed, using a DEBATE."""
        # Identify which metrics got worse
        worse_metrics = []
        for metric, new_delta in new_deltas.items():
            old_delta = old_deltas.get(metric, 0)
            if new_delta < old_delta:
                worse_metrics.append(f"{metric}: {old_delta:.3f} → {new_delta:.3f}")

        # Identify what changes were made
        change_descriptions = [f"{c.file}: {c.description}" for c in changes]

        # Organize a DEBATE about the failure
        from vortex.debate import DebateEngine
        debate = DebateEngine("premortem", models=['mimo-v2.5'])
        agent = debate.create_team(1)[0]

        failure_context = (
            f"Un cycle d'optimisation a ÉCHOUÉ.\n"
            f"Score: {old_score:.3f} → {new_score:.3f} (régression).\n"
            f"Changements tentés: {', '.join(change_descriptions)}\n"
            f"Métriques dégradées: {', '.join(worse_metrics) if worse_metrics else 'aucune identifiée'}\n\n"
            f"Analyse POURQUOI cet échec a eu lieu.\n"
            f"Propose comment ÉVITER cet échec dans le futur."
        )

        debate_result = debate.debate(failure_context, [agent])
        reflection = debate_result.rounds[0]["argument"] if debate_result.rounds else "No reflection generated"

        return reflection

    def _run_cycle(self, cycle_num: int, baseline: dict[str, float]) -> CycleResult:
        """Run a single optimization cycle using the Meta-Orchestrator."""
        cycle_id = f"cycle_{cycle_num}_{int(__import__('time').time())}"
        start_time = __import__('time').time()

        # Collect current metrics
        current = self.collector.collect()
        score, deltas = self.baseline.score(current, baseline)

        # Build context for the orchestrator
        # Include failure reflections from previous cycles
        recent_cycles = self.history.get_recent(5)
        failure_reflections = [
            c.get("reflection", "")
            for c in recent_cycles
            if c.get("decision") == "reverted" and c.get("reflection")
        ]

        context = {
            "current_metrics": current,
            "baseline_metrics": baseline,
            "score": score,
            "previous_cycles": recent_cycles,
            "failure_reflections": failure_reflections,  # NEW: past failures
            "project_path": str(self.manifest.project_path),
            "constraints": self.manifest.constraints,
        }

        # Use Meta-Orchestrator to think strategically
        decision = self.orchestrator.think(context)

        # Generate changes based on the decision
        if decision.action == "optimize":
            changes = self.generator.generate(context)
        else:
            changes = []

        # Execute changes
        if changes and not self.dry_run:
            commit_sha = self.executor.setup_cycle()
            execution = self.executor.execute(changes, context)

            if not execution.success:
                self.executor.rollback(commit_sha)
                return CycleResult(
                    cycle_id=cycle_id,
                    timestamp=__import__('datetime').datetime.now().isoformat(),
                    hypothesis="",
                    changes=[],
                    baseline_metrics=baseline,
                    post_metrics=current,
                    score_delta=0,
                    per_metric_delta=deltas,
                    decision="reverted",
                    commit_sha=commit_sha,
                )

            # Re-measure after changes
            post = self.collector.collect()
            post_score, post_deltas = self.baseline.score(post, baseline)

            if post_score < score:
                # Regression — rollback
                self.executor.rollback(commit_sha)
                # Generate reflection about WHY it failed
                reflection = self._generate_failure_reflection(
                    changes, score, post_score, deltas, post_deltas
                )
                return CycleResult(
                    cycle_id=cycle_id,
                    timestamp=__import__('datetime').datetime.now().isoformat(),
                    hypothesis=str([c.description for c in changes]),
                    changes=[{"file": c.file, "description": c.description} for c in changes],
                    baseline_metrics=baseline,
                    post_metrics=post,
                    score_delta=post_score,
                    per_metric_delta=post_deltas,
                    decision="reverted",
                    commit_sha=commit_sha,
                    reflection=reflection,
                )
            else:
                # Improvement — commit
                final_sha = self.executor.commit_changes(cycle_id)
                return CycleResult(
                    cycle_id=cycle_id,
                    timestamp=__import__('datetime').datetime.now().isoformat(),
                    hypothesis=str([c.description for c in changes]),
                    changes=[{"file": c.file, "description": c.description} for c in changes],
                    baseline_metrics=baseline,
                    post_metrics=post,
                    score_delta=post_score,
                    per_metric_delta=post_deltas,
                    decision="kept",
                    commit_sha=final_sha,
                )
        else:
            # No changes generated
            duration_ms = int((__import__('time').time() - start_time) * 1000)
            return CycleResult(
                cycle_id=cycle_id,
                timestamp=__import__('datetime').datetime.now().isoformat(),
                hypothesis="No hypotheses generated",
                changes=[],
                baseline_metrics=baseline,
                post_metrics=current,
                score_delta=score,
                per_metric_delta=deltas,
                decision="kept",
                duration_ms=duration_ms,
            )

# VORTEX: Clean up unused imports and fix PEP8 style violations (e.g., line length, spacing) to reduce lint_issues.
