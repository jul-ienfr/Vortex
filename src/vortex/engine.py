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

    def _run_cycle(self, cycle_num: int, baseline: dict[str, float]) -> CycleResult:
        """Run a single optimization cycle."""
        cycle_id = f"cycle_{cycle_num}_{int(__import__('time').time())}"
        start_time = __import__('time').time()

        # Collect current metrics
        current = self.collector.collect()
        score, deltas = self.baseline.score(current, baseline)

        # Generate hypotheses
        context = {
            "current_metrics": current,
            "baseline_metrics": baseline,
            "score": score,
            "previous_cycles": self.history.get_recent(3),
        }
        changes = self.generator.generate(context)

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
