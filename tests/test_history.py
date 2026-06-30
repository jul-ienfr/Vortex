"""Tests for the three-layer memory system."""

from __future__ import annotations

from pathlib import Path

import pytest

from vortex.history import CycleHistory, CycleResult, KnowledgeBase, ReflectionMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    cycle_id: str = "cycle-1",
    decision: str = "kept",
    score_delta: float = 0.05,
) -> CycleResult:
    """Build a CycleResult with sensible defaults."""
    return CycleResult(
        cycle_id=cycle_id,
        timestamp="2026-06-30T12:00:00Z",
        hypothesis="Improve throughput by batching writes",
        changes=[{"file": "src/app.py", "action": "edit", "lines_changed": 10}],
        baseline_metrics={"throughput": 100.0, "latency": 50.0},
        post_metrics={"throughput": 105.0, "latency": 48.0},
        score_delta=score_delta,
        per_metric_delta={"throughput": 0.05, "latency": 0.04},
        decision=decision,
        reflection="Batching reduced syscalls significantly.",
        commit_sha="abc1234",
        duration_ms=1200,
    )


# ===========================================================================
# Layer 1 — CycleHistory
# ===========================================================================

class TestCycleHistory:
    def test_record_and_get_recent(self, tmp_path: Path) -> None:
        hist = CycleHistory(tmp_path)
        result = _make_result()
        hist.record(result)

        recent = hist.get_recent(n=5)
        assert len(recent) == 1
        assert recent[0]["cycle_id"] == "cycle-1"
        assert recent[0]["decision"] == "kept"
        assert recent[0]["commit_sha"] == "abc1234"

    def test_get_recent_empty(self, tmp_path: Path) -> None:
        hist = CycleHistory(tmp_path)
        assert hist.get_recent() == []

    def test_get_recent_respects_n(self, tmp_path: Path) -> None:
        hist = CycleHistory(tmp_path)
        for i in range(10):
            hist.record(_make_result(cycle_id=f"cycle-{i}"))

        recent = hist.get_recent(n=3)
        assert len(recent) == 3
        assert [r["cycle_id"] for r in recent] == ["cycle-7", "cycle-8", "cycle-9"]

    def test_summary_empty(self, tmp_path: Path) -> None:
        hist = CycleHistory(tmp_path)
        summary = hist.summary()
        assert summary["total_cycles"] == 0
        assert summary["kept"] == 0
        assert summary["reverted"] == 0

    def test_summary_mixed_decisions(self, tmp_path: Path) -> None:
        hist = CycleHistory(tmp_path)
        hist.record(_make_result(cycle_id="c1", decision="kept", score_delta=0.1))
        hist.record(_make_result(cycle_id="c2", decision="reverted", score_delta=-0.05))
        hist.record(_make_result(cycle_id="c3", decision="kept", score_delta=0.2))

        summary = hist.summary()
        assert summary["total_cycles"] == 3
        assert summary["kept"] == 2
        assert summary["reverted"] == 1
        assert summary["best_cycle_id"] == "c3"
        assert summary["worst_cycle_id"] == "c2"
        assert abs(summary["avg_score_delta"] - (0.1 + (-0.05) + 0.2) / 3) < 1e-9

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        hist1 = CycleHistory(tmp_path)
        hist1.record(_make_result(cycle_id="c1"))

        hist2 = CycleHistory(tmp_path)
        recent = hist2.get_recent()
        assert len(recent) == 1
        assert recent[0]["cycle_id"] == "c1"


# ===========================================================================
# Layer 2 — ReflectionMemory
# ===========================================================================

class TestReflectionMemory:
    def test_store_and_retrieve(self, tmp_path: Path) -> None:
        mem = ReflectionMemory(tmp_path)
        mem.store_reflection("c1", "Batching helps throughput.", {"hypothesis": "batch"})

        refs = mem.get_recent_reflections(n=5)
        assert len(refs) == 1
        assert refs[0] == "Batching helps throughput."

    def test_get_recent_reflections_n(self, tmp_path: Path) -> None:
        mem = ReflectionMemory(tmp_path)
        for i in range(8):
            mem.store_reflection(f"c{i}", f"Reflection {i}", {})

        recent = mem.get_recent_reflections(n=3)
        assert recent == ["Reflection 5", "Reflection 6", "Reflection 7"]

    def test_language_gradients(self, tmp_path: Path) -> None:
        mem = ReflectionMemory(tmp_path)
        mem.store_reflection("c1", "Success: caching", {}, score_delta=0.1)
        mem.store_reflection("c2", "Failure: broke tests", {}, score_delta=-0.05)
        mem.store_reflection("c3", "Success: profiling", {}, score_delta=0.08)

        grads = mem.get_language_gradients()
        assert len(grads) == 2
        assert "Success: caching" in grads
        assert "Success: profiling" in grads

    def test_success_patterns(self, tmp_path: Path) -> None:
        mem = ReflectionMemory(tmp_path)
        mem.store_reflection("c1", "Good: parallel IO", {}, score_delta=0.1)
        mem.store_reflection("c2", "Bad: broke compat", {}, score_delta=-0.02)

        patterns = mem.get_success_patterns()
        assert len(patterns) == 1
        assert patterns[0] == "Good: parallel IO"

    def test_failure_patterns(self, tmp_path: Path) -> None:
        mem = ReflectionMemory(tmp_path)
        mem.store_reflection("c1", "Good: parallel IO", {}, score_delta=0.1)
        mem.store_reflection("c2", "Bad: broke compat", {}, score_delta=-0.02)
        mem.store_reflection("c3", "Neutral: no change", {}, score_delta=0.0)

        patterns = mem.get_failure_patterns()
        assert len(patterns) == 2
        assert "Bad: broke compat" in patterns
        assert "Neutral: no change" in patterns

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        mem1 = ReflectionMemory(tmp_path)
        mem1.store_reflection("c1", "First reflection", {"key": "val"})

        mem2 = ReflectionMemory(tmp_path)
        refs = mem2.get_recent_reflections()
        assert refs == ["First reflection"]


# ===========================================================================
# Layer 3 — KnowledgeBase
# ===========================================================================

class TestKnowledgeBase:
    def test_store_and_retrieve_playbook(self, tmp_path: Path) -> None:
        kb = KnowledgeBase(tmp_path)
        kb.store_playbook("caching-strategy", "Use LRU cache for hot paths.")

        playbooks = kb.get_relevant_playbooks("caching strategy hot paths")
        assert len(playbooks) == 1
        assert playbooks[0]["name"] == "caching-strategy"
        assert "LRU cache" in playbooks[0]["content"]

    def test_get_relevant_playbooks_empty(self, tmp_path: Path) -> None:
        kb = KnowledgeBase(tmp_path)
        assert kb.get_relevant_playbooks("anything") == []

    def test_get_relevant_playbooks_keyword_match(self, tmp_path: Path) -> None:
        kb = KnowledgeBase(tmp_path)
        kb.store_playbook("db-optimization", "Add indexes to slow queries.")
        kb.store_playbook("ui-refactor", "Improve button accessibility.")
        kb.store_playbook("query-tuning", "Optimize SQL query plans.")

        # "database query" matches db-optimization (via "queries") and query-tuning (via "query")
        results = kb.get_relevant_playbooks("database query optimization")
        names = {r["name"] for r in results}
        assert "db-optimization" in names
        assert "query-tuning" in names

    def test_store_and_retrieve_hints(self, tmp_path: Path) -> None:
        kb = KnowledgeBase(tmp_path)
        kb.store_hint("Use async for I/O-bound code", ["performance", "async"])
        kb.store_hint("Pin dependency versions", ["packaging", "reliability"])

        hints = kb._load_hints()
        assert len(hints) == 2
        assert hints[0]["hint"] == "Use async for I/O-bound code"
        assert hints[0]["tags"] == ["performance", "async"]
        assert hints[1]["tags"] == ["packaging", "reliability"]

    def test_playbook_special_characters_in_name(self, tmp_path: Path) -> None:
        kb = KnowledgeBase(tmp_path)
        kb.store_playbook("my playbook (v2.0)", "Content here.")

        playbooks = kb.get_relevant_playbooks("playbook content")
        assert len(playbooks) == 1

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        kb1 = KnowledgeBase(tmp_path)
        kb1.store_playbook("test", "Persistent content")
        kb1.store_hint("test hint", ["tag"])

        kb2 = KnowledgeBase(tmp_path)
        playbooks = kb2.get_relevant_playbooks("persistent")
        assert len(playbooks) == 1
        hints = kb2._load_hints()
        assert len(hints) == 1


# ===========================================================================
# Integration — all 3 layers together
# ===========================================================================

class TestIntegrationLifecycle:
    def test_full_cycle_lifecycle(self, tmp_path: Path) -> None:
        """Simulate a complete optimisation cycle through all 3 memory layers."""
        hist = CycleHistory(tmp_path)
        refl = ReflectionMemory(tmp_path)
        kb = KnowledgeBase(tmp_path)

        # --- Cycle 1: success ---
        r1 = _make_result(cycle_id="cycle-1", decision="kept", score_delta=0.15)
        hist.record(r1)

        refl.store_reflection(
            "cycle-1",
            "Batching writes improved throughput by 15% with no regression.",
            {"hypothesis": r1.hypothesis},
            score_delta=r1.score_delta,
        )

        kb.store_playbook("batching-writes", "Group small writes into batches for throughput.")
        kb.store_hint("Batch I/O operations when latency is not critical", ["io", "throughput"])

        # --- Cycle 2: regression, reverted ---
        r2 = _make_result(cycle_id="cycle-2", decision="reverted", score_delta=-0.08)
        hist.record(r2)

        refl.store_reflection(
            "cycle-2",
            "Removing error handling caused test failures. Reverted.",
            {"hypothesis": "Simplify error handling"},
            score_delta=r2.score_delta,
        )

        # --- Assertions ---
        summary = hist.summary()
        assert summary["total_cycles"] == 2
        assert summary["kept"] == 1
        assert summary["reverted"] == 1

        recent_refs = refl.get_recent_reflections(n=2)
        assert len(recent_refs) == 2

        success = refl.get_success_patterns()
        failure = refl.get_failure_patterns()
        assert len(success) == 1
        assert len(failure) == 1

        playbooks = kb.get_relevant_playbooks("batching throughput")
        assert len(playbooks) == 1
        assert playbooks[0]["name"] == "batching-writes"
