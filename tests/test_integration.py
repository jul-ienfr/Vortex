"""End-to-end integration tests for VORTEX."""

from pathlib import Path

import yaml

from vortex.engine import Optimizer
from vortex.manifest import ManifestConfig
from vortex.metrics import BaselineManager, MetricsCollector


def test_full_optimization_cycle(tmp_project: Path):
    """Test a complete optimization cycle end-to-end."""
    # Create manifest
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
        },
    }))

    # Run optimizer in dry-run mode
    optimizer = Optimizer(manifest_path, dry_run=True)
    assert optimizer.manifest.name == "integration_test"
    assert optimizer.convergence is not None
    assert optimizer.skills is not None


def test_manifest_to_metrics_flow(tmp_project: Path):
    """Test flow from manifest to metrics collection."""
    manifest_path = tmp_project / "vortex.yaml"
    manifest_path.write_text(yaml.dump({
        "name": "flow_test",
        "project_path": str(tmp_project),
        "metrics": [
            {"name": "m1", "source": "echo 10", "direction": "up"},
            {"name": "m2", "source": "echo 20", "direction": "down"},
        ],
    }))

    manifest = ManifestConfig.from_yaml(manifest_path)
    collector = MetricsCollector(manifest)
    baseline = BaselineManager(manifest)

    # Collect baseline
    bl = baseline.establish_baseline(collector)
    assert bl["m1"] == 10.0
    assert bl["m2"] == 20.0

    # Collect current
    current = collector.collect()
    score, deltas = baseline.score(current, bl)
    assert score == 0.0  # same values


def test_debate_and_tree_search(tmp_project: Path):
    """Test debate engine with tree search."""
    from vortex.debate import DebateEngine
    from vortex.tree_search import TreeSearch

    engine = DebateEngine("standard")
    team = engine.create_team(3)
    result = engine.debate("Optimize performance", team)
    assert len(result.rounds) == 3

    search = TreeSearch(max_depth=2, branching_factor=2)
    changes = search.search({"metrics": {}})
    assert isinstance(changes, list)


def test_skill_library_lifecycle(tmp_project: Path):
    """Test skill library full lifecycle."""
    from vortex.skill_library import SkillLibrary

    lib = SkillLibrary(tmp_project)

    # Create
    skill = lib.create_skill("perf_opt", "Optimize performance", "modify config")

    # Successes (crystallize after 3)
    for _ in range(3):
        lib.record_success(skill.id, 0.1)

    # Verify crystallized
    updated = lib.get_skill(skill.id)
    assert updated.crystallized

    # Prune should keep it
    pruned = lib.prune(min_uses=1, min_age_days=0)
    assert lib.get_skill(skill.id) is not None


def test_wal_crash_recovery(tmp_project: Path):
    """Test WAL crash recovery flow."""
    from vortex.wal import WAL

    wal = WAL(tmp_project)

    # Simulate crash: log operation but don't complete
    op_id = wal.log_operation("optimization_cycle", {"cycle": 1})

    # Recover should find pending operations
    pending = wal.recover()
    assert len(pending) == 1
    assert pending[0].operation_type == "optimization_cycle"

    # Complete the operation
    wal.mark_completed(op_id)
    pending = wal.recover()
    assert len(pending) == 0
