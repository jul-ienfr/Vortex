"""Tests for new modules: feature flags, resource governor, explainability, A/B testing, hot reload."""

from pathlib import Path

from vortex.ab_testing import ABTestManager
from vortex.explainability import ExplainabilityEngine
from vortex.feature_flags import FeatureFlags
from vortex.hot_reload import ManifestWatcher
from vortex.resource_governor import ResourceGovernor


def test_feature_flags(tmp_project: Path):
    """Test feature flags."""
    flags = FeatureFlags(tmp_project)
    assert flags.is_enabled("debate_enabled") is True
    flags.toggle("debate_enabled")
    assert flags.is_enabled("debate_enabled") is False
    flags.enable("debate_enabled")
    assert flags.is_enabled("debate_enabled") is True


def test_feature_flags_list(tmp_project: Path):
    """Test listing all flags."""
    flags = FeatureFlags(tmp_project)
    all_flags = flags.list_flags()
    assert "debate_enabled" in all_flags
    assert "sandbox_enabled" in all_flags


def test_resource_governor():
    """Test resource governor."""
    governor = ResourceGovernor()
    assert governor.check_api_call() is True
    usage = governor.get_usage()
    assert "api_calls_last_minute" in usage
    assert "llm_tokens_this_hour" in usage


def test_resource_governor_rate_limit():
    """Test API rate limiting."""
    governor = ResourceGovernor()
    # Make many calls quickly
    for _ in range(60):
        governor.check_api_call()
    # Next call should be rate limited
    assert governor.check_api_call() is False


def test_explainability():
    """Test explainability engine."""
    engine = ExplainabilityEngine(Path("/tmp"))
    explanation = engine.explain_cycle({
        "decision": "kept",
        "score_delta": 0.15,
        "hypothesis": "Optimize cache",
        "files_changed": ["cache.py"],
    })
    assert "accepté" in explanation
    assert "+0.150" in explanation


def test_explainability_rollback():
    """Test rollback explanation."""
    engine = ExplainabilityEngine(Path("/tmp"))
    explanation = engine.explain_rollback({
        "baseline_score": 0.5,
        "post_score": 0.3,
        "score_delta": -0.2,
        "hypothesis": "Bad change",
    })
    assert "Rollback" in explanation
    assert "-0.200" in explanation


def test_ab_testing(tmp_project: Path):
    """Test A/B testing."""
    manager = ABTestManager(tmp_project)
    test = manager.create_test("Test A/B", {"strategy": "fast"}, {"strategy": "thorough"})
    manager.record_result(test.id, "a", 0.8)
    manager.record_result(test.id, "a", 0.9)
    manager.record_result(test.id, "b", 0.7)
    result = manager.analyze(test.id)
    assert result.winner == "a"
    assert result.samples == 3


def test_hot_reload(tmp_project: Path):
    """Test hot reload watcher."""
    changes = []
    watcher = ManifestWatcher(tmp_project / "vortex.yaml", lambda m: changes.append(m))
    assert watcher.check() is False  # no change yet
