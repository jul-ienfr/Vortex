"""Tests for metrics collection and baseline management."""

from pathlib import Path

import yaml

from vortex.manifest import ManifestConfig
from vortex.metrics import BaselineManager, MetricsCollector


def test_metrics_collector(tmp_manifest: Path):
    """Test collecting metrics from shell commands."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    collector = MetricsCollector(manifest)
    results = collector.collect()
    assert "test_metric" in results
    assert results["test_metric"] == 42.0


def test_metrics_collector_multiple(tmp_project: Path):
    """Test collecting multiple metrics."""
    manifest_path = tmp_project / "multi.yaml"
    manifest_path.write_text(yaml.dump({
        "name": "multi",
        "project_path": str(tmp_project),
        "metrics": [
            {"name": "m1", "source": "echo 10", "direction": "up"},
            {"name": "m2", "source": "echo 20", "direction": "down"},
            {"name": "m3", "source": "echo 30", "direction": "up"},
        ],
    }))
    manifest = ManifestConfig.from_yaml(manifest_path)
    collector = MetricsCollector(manifest)
    results = collector.collect()
    assert results["m1"] == 10.0
    assert results["m2"] == 20.0
    assert results["m3"] == 30.0


def test_baseline_establishment(tmp_manifest: Path):
    """Test baseline establishment."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    collector = MetricsCollector(manifest)
    baseline = BaselineManager(manifest)
    bl = baseline.establish_baseline(collector)
    assert "test_metric" in bl
    assert bl["test_metric"] == 42.0
    # Verify persistence
    loaded = baseline.load_baseline()
    assert loaded is not None
    assert loaded["test_metric"] == 42.0


def test_scoring(tmp_manifest: Path):
    """Test scoring with direction."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    baseline = BaselineManager(manifest)

    # Score improved (up direction)
    score, deltas = baseline.score({"test_metric": 50.0}, {"test_metric": 42.0})
    assert score > 0  # improvement

    # Score degraded (up direction)
    score, deltas = baseline.score({"test_metric": 30.0}, {"test_metric": 42.0})
    assert score < 0  # degradation


def test_scoring_down_direction(tmp_project: Path):
    """Test scoring with 'down' direction (lower is better)."""
    manifest_path = tmp_project / "down.yaml"
    manifest_path.write_text(yaml.dump({
        "name": "down",
        "project_path": str(tmp_project),
        "metrics": [{"name": "latency", "source": "echo 100", "direction": "down"}],
    }))
    manifest = ManifestConfig.from_yaml(manifest_path)
    baseline = BaselineManager(manifest)

    # Score improved (down direction — lower is better)
    score, deltas = baseline.score({"latency": 50.0}, {"latency": 100.0})
    assert score > 0  # improvement (latency decreased)

    # Score degraded (down direction)
    score, deltas = baseline.score({"latency": 200.0}, {"latency": 100.0})
    assert score < 0  # degradation (latency increased)


def test_scoring_weighted(tmp_project: Path):
    """Test weighted scoring."""
    manifest_path = tmp_project / "weighted.yaml"
    manifest_path.write_text(yaml.dump({
        "name": "weighted",
        "project_path": str(tmp_project),
        "metrics": [
            {"name": "important", "source": "echo 10", "direction": "up", "weight": 3.0},
            {"name": "minor", "source": "echo 10", "direction": "up", "weight": 0.5},
        ],
    }))
    manifest = ManifestConfig.from_yaml(manifest_path)
    baseline = BaselineManager(manifest)

    # Both improve by same absolute amount
    score, deltas = baseline.score(
        {"important": 15.0, "minor": 15.0},
        {"important": 10.0, "minor": 10.0},
    )
    # important has 3x weight, so its delta dominates
    assert deltas["important"] > deltas["minor"]
