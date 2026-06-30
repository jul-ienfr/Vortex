"""Tests for the main engine and self-improvement."""

from pathlib import Path

from vortex.engine import Optimizer
from vortex.self_improve import MetaSuggestion, PerformanceReport, SelfImprover


def test_self_improve_analyze(tmp_project: Path):
    """Test performance analysis."""
    improver = SelfImprover(tmp_project)
    report = improver.analyze_performance([
        {"decision": "kept", "score_delta": 0.1},
        {"decision": "kept", "score_delta": 0.2},
        {"decision": "reverted", "score_delta": -0.1},
    ])
    assert report.total_cycles == 3
    assert report.success_rate == 2 / 3


def test_self_improve_suggestions(tmp_project: Path):
    """Test suggestion generation."""
    improver = SelfImprover(tmp_project)
    report = PerformanceReport(total_cycles=10, success_rate=0.2, avg_score_delta=0.005)
    suggestions = improver.generate_suggestions(report)
    assert len(suggestions) > 0
    # Should suggest reducing changes due to low success rate
    param_names = [s.parameter for s in suggestions]
    assert "max_changes_per_cycle" in param_names


def test_self_improve_record(tmp_project: Path):
    """Test recording suggestions."""
    improver = SelfImprover(tmp_project)
    suggestion = MetaSuggestion(
        parameter="max_changes_per_cycle",
        current_value="3",
        suggested_value="1",
        reason="Low success rate",
    )
    improver.record_suggestion(suggestion, applied=True)
    history = improver._load_history()
    assert len(history) == 1
    assert history[0]["applied"] is True


def test_optimizer_dry_run(tmp_manifest: Path):
    """Test optimizer in dry-run mode."""
    optimizer = Optimizer(tmp_manifest, dry_run=True)
    # Just verify it initializes
    assert optimizer.manifest.name == "test_project"
    assert optimizer.convergence is not None
