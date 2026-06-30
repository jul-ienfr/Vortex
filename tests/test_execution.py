"""Tests for execution engine and convergence detection."""

from pathlib import Path

from vortex.convergence import ConvergenceConfig, ConvergenceDetector
from vortex.execution import (
    Change,
    ConstraintGates,
    ExecutionEngine,
    ExecutionResult,
    GateResult,
    HypothesisGenerator,
)
from vortex.manifest import ManifestConfig


def test_convergence_stagnation():
    """Test stagnation detection."""
    detector = ConvergenceDetector(ConvergenceConfig(stagnation_limit=3, min_cycles=0))
    for i in range(5):
        detector.record_score(0.5, i)
    should_stop, reason = detector.should_stop()
    assert should_stop
    assert "Stagnation" in reason


def test_convergence_improving():
    """Test that improving scores don't trigger stop."""
    detector = ConvergenceDetector(ConvergenceConfig(stagnation_limit=3, min_cycles=0))
    for i in range(5):
        detector.record_score(0.5 + i * 0.1, i)
    should_stop, _ = detector.should_stop()
    assert not should_stop


def test_convergence_target():
    """Test target score detection."""
    detector = ConvergenceDetector(ConvergenceConfig(target_score=0.8, min_cycles=0))
    detector.record_score(0.9, 0)
    should_stop, reason = detector.should_stop()
    assert should_stop
    assert "Target reached" in reason


def test_convergence_stats():
    """Test statistics output."""
    detector = ConvergenceDetector(ConvergenceConfig(min_cycles=0))
    detector.record_score(0.5, 0)
    detector.record_score(0.7, 1)
    stats = detector.get_stats()
    assert stats["total_cycles"] == 2
    assert stats["best_score"] == 0.7
    assert stats["best_cycle"] == 1


def test_execution_engine_setup(tmp_manifest: Path):
    """Test cycle setup creates branch."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    engine = ExecutionEngine(manifest)
    commit_sha = engine.setup_cycle()
    assert len(commit_sha) == 40  # SHA-1 hash


def test_execution_engine_execute(tmp_manifest: Path):
    """Test executing changes."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    engine = ExecutionEngine(manifest)
    engine.setup_cycle()

    changes = [Change(file="test.py", description="Add optimization")]
    result = engine.execute(changes, {})
    assert result.success
    assert "test.py" in result.files_changed


def test_execution_engine_rollback(tmp_manifest: Path):
    """Test rollback to commit."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    engine = ExecutionEngine(manifest)
    commit_sha = engine.setup_cycle()
    result = engine.rollback(commit_sha)
    assert result


def test_constraint_gates(tmp_manifest: Path):
    """Test constraint gate validation."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    gates = ConstraintGates(manifest)
    execution = ExecutionResult(success=True, files_changed=["test.py"])
    result = gates.validate(execution, {})
    assert isinstance(result, GateResult)
    assert len(result.gates) == 5


def test_constraint_gate_size_limit(tmp_manifest: Path):
    """Test size limit gate."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    gates = ConstraintGates(manifest)
    execution = ExecutionResult(success=True, files_changed=["large_file.py"])
    # Check size gate individually
    size_gate = gates._check_sizes(execution)
    assert size_gate.passed  # file doesn't exist, so passes


def test_hypothesis_generator(tmp_manifest: Path):
    """Test hypothesis generation (stub)."""
    manifest = ManifestConfig.from_yaml(tmp_manifest)
    gen = HypothesisGenerator(manifest)
    changes = gen.generate({"current_metrics": {}, "baseline_metrics": {}})
    assert isinstance(changes, list)
