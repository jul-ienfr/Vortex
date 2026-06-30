"""Tests for cache, circuit breaker, and incremental analysis."""

from pathlib import Path

from vortex.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from vortex.incremental import IncrementalAnalyzer
from vortex.llm_cache import LLMCache


def test_llm_cache(tmp_project: Path):
    """Test LLM cache get/set."""
    cache = LLMCache(tmp_project / ".cache")
    assert cache.get("test prompt") is None
    cache.set("test prompt", "test response")
    assert cache.get("test prompt") == "test response"


def test_llm_cache_clear(tmp_project: Path):
    """Test cache clearing."""
    cache = LLMCache(tmp_project / ".cache")
    cache.set("p1", "r1")
    cache.set("p2", "r2")
    cleared = cache.clear()
    assert cleared == 2
    assert cache.get("p1") is None


def test_circuit_breaker():
    """Test circuit breaker."""
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=1)

    # Successful calls
    result = cb.call("test", lambda: "ok")
    assert result == "ok"
    assert cb.get_state("test") == "closed"

    # Failures
    for _ in range(3):
        try:
            cb.call("test", lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

    assert cb.get_state("test") == "open"

    # Should raise when open
    try:
        cb.call("test", lambda: "ok")
        assert False, "Should have raised CircuitBreakerOpen"
    except CircuitBreakerOpen:
        pass


def test_incremental_analyzer(tmp_project: Path):
    """Test incremental analysis."""
    analyzer = IncrementalAnalyzer(tmp_project)

    # First run - all files are "new"
    changed = analyzer.get_changed_files()
    assert len(changed) > 0

    # Second run - no changes
    changed = analyzer.get_changed_files()
    assert len(changed) == 0
