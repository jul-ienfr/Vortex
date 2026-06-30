"""Performance benchmarks for VORTEX."""

import time

from vortex.debate import DebateEngine
from vortex.history import CycleHistory, CycleResult
from vortex.manifest import ManifestConfig
from vortex.metrics import BaselineManager, MetricsCollector
from vortex.self_improve import SelfImprover
from vortex.skill_library import SkillLibrary
from vortex.swarm import SwarmExploration
from vortex.tree_search import TreeSearch


def test_benchmark_metrics_collection():
    """Benchmark metrics collection speed."""
    import tempfile, yaml
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        manifest_path = path / "vortex.yaml"
        manifest_path.write_text(yaml.dump({
            "name": "bench",
            "project_path": str(path),
            "metrics": [{"name": f"m{i}", "source": "echo 42", "direction": "up"} for i in range(10)],
        }))
        manifest = ManifestConfig.from_yaml(manifest_path)
        collector = MetricsCollector(manifest)

        start = time.time()
        for _ in range(100):
            collector.collect()
        elapsed = time.time() - start

        # Should collect 10 metrics x 100 iterations in under 30 seconds
        assert elapsed < 30, f"Too slow: {elapsed:.2f}s"


def test_benchmark_tree_search():
    """Benchmark tree search speed."""
    search = TreeSearch(max_depth=3, branching_factor=3)
    start = time.time()
    for _ in range(50):
        search.search({"metrics": {}})
    elapsed = time.time() - start
    # Should complete 50 searches in under 5 seconds
    assert elapsed < 5, f"Too slow: {elapsed:.2f}s"


def test_benchmark_debate():
    """Benchmark debate creation speed."""
    start = time.time()
    for _ in range(100):
        engine = DebateEngine("standard")
        team = engine.create_team(3)
        engine.debate("Test topic", team)
    elapsed = time.time() - start
    # Should complete 100 debates in under 5 seconds
    assert elapsed < 5, f"Too slow: {elapsed:.2f}s"


def test_benchmark_swarm():
    """Benchmark swarm evolution speed."""
    swarm = SwarmExploration(swarm_size=5)
    start = time.time()
    swarm.evolve([{"fitness": 0.5} for _ in range(5)], generations=5)
    elapsed = time.time() - start
    # Should complete evolution in under 2 seconds
    assert elapsed < 2, f"Too slow: {elapsed:.2f}s"
