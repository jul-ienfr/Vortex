"""Comprehensive end-to-end test of the full optimization loop."""

from pathlib import Path

import yaml

from vortex.ab_testing import ABTestManager
from vortex.audit import AuditTrail
from vortex.circuit_breaker import CircuitBreaker
from vortex.config import ConfigManager
from vortex.convergence import ConvergenceConfig, ConvergenceDetector
from vortex.debate import DebateEngine
from vortex.engine import Optimizer
from vortex.execution import Change, ExecutionEngine
from vortex.explainability import ExplainabilityEngine
from vortex.feature_flags import FeatureFlags
from vortex.history import CycleHistory, CycleResult, ReflectionMemory
from vortex.hooks import HookManager
from vortex.incremental import IncrementalAnalyzer
from vortex.llm_cache import LLMCache
from vortex.manifest import ManifestConfig
from vortex.metrics import BaselineManager, MetricsCollector
from vortex.metrics_exporter import MetricsExporter
from vortex.registry import ProjectRegistry
from vortex.resource_governor import ResourceGovernor
from vortex.skill_library import SkillLibrary
from vortex.swarm import SwarmExploration
from vortex.tree_search import TreeSearch
from vortex.wal import WAL
from vortex.webhooks import WebhookManager


def test_full_system_integration(tmp_project: Path):
    """Test all components working together."""
    # 1. Create manifest
    manifest_path = tmp_project / "vortex.yaml"
    manifest_path.write_text(yaml.dump({
        "name": "integration_test",
        "project_path": str(tmp_project),
        "metrics": [
            {"name": "test_metric", "source": "echo 42", "direction": "up"},
        ],
        "optimizer": {
            "cli": "claude",
            "max_changes_per_cycle": 1,
            "self_improve_enabled": False,
            "debate_enabled": True,
            "skill_library_enabled": True,
        },
    }))

    # 2. Initialize all components
    manifest = ManifestConfig.from_yaml(manifest_path)
    collector = MetricsCollector(manifest)
    baseline = BaselineManager(manifest)
    history = CycleHistory(tmp_project)
    reflections = ReflectionMemory(tmp_project)
    skills = SkillLibrary(tmp_project)
    flags = FeatureFlags(tmp_project)
    wal = WAL(tmp_project)
    audit = AuditTrail(tmp_project)
    cache = LLMCache(tmp_project / ".cache")
    governor = ResourceGovernor()
    analyzer = IncrementalAnalyzer(tmp_project)
    hooks = HookManager(tmp_project)
    registry = ProjectRegistry(tmp_project / ".vortex")
    webhooks = WebhookManager(tmp_project)
    cb = CircuitBreaker()
    exporter = MetricsExporter()
    explain = ExplainabilityEngine(tmp_project)

    # 3. Establish baseline
    bl = baseline.establish_baseline(collector)
    assert "test_metric" in bl

    # 4. Collect current metrics
    current = collector.collect()
    score, deltas = baseline.score(current, bl)

    # 5. Record metrics
    exporter.record("optimization_score", score)
    exporter.record("baseline_value", bl["test_metric"])

    # 6. Create a skill
    skill = skills.create_skill("test_opt", "Test optimization", "modify file")
    skills.record_success(skill.id, 0.1)

    # 7. Create a hook
    hooks.create_hook("test_hook", "before_cycle", "echo test")

    # 8. Register a project
    registry.register("test_project", tmp_project, manifest_path)

    # 9. Run tree search
    search = TreeSearch(max_depth=2, branching_factor=2)
    changes = search.search({"metrics": current})

    # 10. Run debate
    engine = DebateEngine("standard")
    team = engine.create_team(3)
    debate_result = engine.debate("Optimize test_metric", team)

    # 11. Run swarm
    swarm = SwarmExploration(swarm_size=3)
    swarm_results = swarm.evolve([{"fitness": 0.5} for _ in range(3)], generations=2)

    # 12. Run convergence check
    conv = ConvergenceDetector(ConvergenceConfig(min_cycles=0))
    conv.record_score(score, 0)
    should_stop, reason = conv.should_stop()

    # 13. Record in history
    cycle_result = CycleResult(
        cycle_id="test_cycle_1",
        timestamp="2026-01-01T00:00:00",
        hypothesis="Test optimization",
        changes=[],
        baseline_metrics=bl,
        post_metrics=current,
        score_delta=score,
        per_metric_delta=deltas,
        decision="kept",
    )
    history.record(cycle_result)

    # 14. Store reflection
    reflections.store_reflection("test_cycle_1", "Test reflection", {"score": score})

    # 15. Log audit
    audit.log("optimization_cycle", "test", {"score": score})

    # 16. WAL
    op_id = wal.log_operation("test_cycle", {"score": score})
    wal.mark_completed(op_id)

    # 17. Feature flags
    assert flags.is_enabled("debate_enabled") is True

    # 18. Resource governor
    assert governor.check_api_call() is True

    # 19. Explain
    explanation = explain.explain_cycle({
        "decision": "kept",
        "score_delta": score,
        "hypothesis": "Test",
        "files_changed": [],
    })
    assert "accepté" in explanation

    # 20. Verify all components work
    assert len(history.get_recent(1)) == 1
    assert len(reflections.get_recent_reflections(1)) == 1
    assert len(skills.list_skills()) == 1
    assert len(hooks.list_hooks()) == 1
    assert len(registry.list_projects()) == 1
    assert len(search.archive.nodes) > 0
    assert len(swarm_results) == 3
    assert conv.get_stats()["total_cycles"] == 1
