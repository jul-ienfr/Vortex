"""Tests for the Meta-Orchestrator."""

from pathlib import Path

from vortex.manifest import ManifestConfig
from vortex.meta_orchestrator import MetaOrchestrator, StrategicDecision


def test_meta_orchestrator_creation(tmp_project: Path):
    """Test creating a MetaOrchestrator."""
    manifest_path = tmp_project / "vortex.yaml"
    manifest_path.write_text("""
name: test
project_path: {}
metrics:
  - name: test_metric
    source: "echo 42"
    direction: up
""".format(tmp_project))

    manifest = ManifestConfig.from_yaml(manifest_path)
    orchestrator = MetaOrchestrator(manifest)
    assert orchestrator.manifest.name == "test"


def test_strategic_decision():
    """Test StrategicDecision creation."""
    decision = StrategicDecision(
        action="optimize",
        target="src/vortex/engine.py",
        rationale="Improve performance",
        confidence=0.8,
    )
    assert decision.action == "optimize"
    assert decision.confidence == 0.8
