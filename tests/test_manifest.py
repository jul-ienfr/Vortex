"""Tests for manifest parsing and validation."""

from pathlib import Path

import yaml

from vortex.manifest import ManifestConfig, MetricDef, OptimizerConfig


def test_manifest_from_yaml(tmp_manifest: Path):
    """Test loading a manifest from YAML."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    assert manifest.name == "test_project"
    assert len(manifest.metrics) == 1
    assert manifest.metrics[0].name == "test_metric"
    assert manifest.metrics[0].direction == "up"


def test_manifest_defaults(tmp_project: Path):
    """Test default values."""
    manifest_path = tmp_project / "minimal.yaml"
    manifest_path.write_text(yaml.dump({
        "name": "minimal",
        "project_path": str(tmp_project),
        "metrics": [{"name": "m", "source": "echo 1", "direction": "up"}],
    }))
    manifest = ManifestConfig.from_yaml(manifest_path)
    assert manifest.optimizer.cli == "claude"
    assert manifest.optimizer.max_changes_per_cycle == 3
    assert manifest.optimizer.rollback_on_regression is True
    assert manifest.optimizer.debate_enabled is True


def test_metric_def():
    """Test MetricDef validation."""
    m = MetricDef(name="test", source="echo 1", direction="up")
    assert m.weight == 1.0
    assert m.baseline_samples == 1
    assert m.min_improvement_pct == 0.0


def test_optimizer_config():
    """Test OptimizerConfig defaults."""
    config = OptimizerConfig()
    assert config.tree_search_branches == 3
    assert config.reflection_depth == 1
    assert config.skill_library_enabled is True
    assert config.self_improve_enabled is True
    assert config.max_moves_per_cycle is None  # unlimited
    assert config.model is None
    assert config.budget_limit_usd == 5.0
