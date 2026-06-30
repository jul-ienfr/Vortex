"""Three-layer memory system for VORTEX.

Layer 1 (CycleHistory):   JSONL-based raw cycle history.
Layer 2 (ReflectionMemory): Verbal reflections stored as episodic memory.
Layer 3 (KnowledgeBase):  Persistent playbooks and hints.

All data is persisted under ``{project_path}/.vortex/``.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CycleResult:
    """Immutable record of one optimisation cycle."""

    cycle_id: str
    timestamp: str
    hypothesis: str
    changes: list[dict]
    baseline_metrics: dict[str, float]
    post_metrics: dict[str, float]
    score_delta: float
    per_metric_delta: dict[str, float]
    decision: str  # "kept" | "reverted"
    reflection: str | None = None
    commit_sha: str | None = None
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Layer 1 — CycleHistory
# ---------------------------------------------------------------------------

class CycleHistory:
    """L1: Raw cycle history stored as an append-only JSONL file."""

    FILENAME = "history.jsonl"

    def __init__(self, project_path: Path) -> None:
        self._dir = project_path / ".vortex"
        self._path = self._dir / self.FILENAME

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- public API ---------------------------------------------------------

    def record(self, result: CycleResult) -> None:
        """Append one cycle result to the JSONL file."""
        self._ensure_dir()
        record = asdict(result)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("Recorded cycle %s (decision=%s, delta=%.4f)", result.cycle_id, result.decision, result.score_delta)

    def get_recent(self, n: int = 5) -> list[dict]:
        """Return the most recent *n* cycle records as dicts."""
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        recent = [json.loads(line) for line in lines[-n:] if line.strip()]
        return recent

    def summary(self) -> dict:
        """Aggregate statistics over all recorded cycles."""
        if not self._path.exists():
            return {"total_cycles": 0, "kept": 0, "reverted": 0, "avg_score_delta": 0.0}

        records: list[dict] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))

        total = len(records)
        kept = sum(1 for r in records if r.get("decision") == "kept")
        reverted = total - kept
        deltas = [r.get("score_delta", 0.0) for r in records]
        avg_delta = sum(deltas) / total if total else 0.0
        best = max(records, key=lambda r: r.get("score_delta", 0.0)) if total else None
        worst = min(records, key=lambda r: r.get("score_delta", 0.0)) if total else None

        return {
            "total_cycles": total,
            "kept": kept,
            "reverted": reverted,
            "avg_score_delta": avg_delta,
            "best_cycle_id": best.get("cycle_id") if best else None,
            "worst_cycle_id": worst.get("cycle_id") if worst else None,
        }


# ---------------------------------------------------------------------------
# Layer 2 — ReflectionMemory
# ---------------------------------------------------------------------------

class ReflectionMemory:
    """L2: Verbal reflections stored as episodic memory (JSON)."""

    FILENAME = "reflections.json"

    def __init__(self, project_path: Path) -> None:
        self._dir = project_path / ".vortex"
        self._path = self._dir / self.FILENAME

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, data: list[dict]) -> None:
        self._ensure_dir()
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # -- public API ---------------------------------------------------------

    def store_reflection(
        self,
        cycle_id: str,
        reflection: str,
        context: dict,
        *,
        score_delta: float = 0.0,
    ) -> None:
        """Store a verbal reflection tied to a specific cycle.

        Args:
            cycle_id:  Identifier of the cycle that produced this reflection.
            reflection: Free-text verbal reflection (the "what worked / what failed" insight).
            context: Arbitrary context dict (hypothesis, changes, etc.).
            score_delta: Overall score delta for the cycle (used to classify success/failure).
        """
        data = self._load()
        entry = {
            "cycle_id": cycle_id,
            "reflection": reflection,
            "context": context,
            "score_delta": score_delta,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data.append(entry)
        self._save(data)
        logger.info("Stored reflection for cycle %s", cycle_id)

    def get_recent_reflections(self, n: int = 5) -> list[str]:
        """Return the most recent *n* reflection texts."""
        data = self._load()
        return [entry["reflection"] for entry in data[-n:]]

    def get_language_gradients(self) -> list[str]:
        """Return reflections from cycles that showed improvement (positive gradient)."""
        data = self._load()
        return [
            entry["reflection"]
            for entry in data
            if entry.get("score_delta", 0.0) > 0
        ]

    def get_success_patterns(self) -> list[str]:
        """Return reflections from successful (kept) cycles."""
        data = self._load()
        return [
            entry["reflection"]
            for entry in data
            if entry.get("score_delta", 0.0) > 0
        ]

    def get_failure_patterns(self) -> list[str]:
        """Return reflections from unsuccessful (reverted) cycles."""
        data = self._load()
        return [
            entry["reflection"]
            for entry in data
            if entry.get("score_delta", 0.0) <= 0
        ]


# ---------------------------------------------------------------------------
# Layer 3 — KnowledgeBase
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """L3: Persistent playbooks and hints."""

    PLAYBOOKS_DIR = "playbooks"
    HINTS_FILE = "hints.json"

    def __init__(self, project_path: Path) -> None:
        self._dir = project_path / ".vortex"
        self._playbooks_dir = self._dir / self.PLAYBOOKS_DIR
        self._hints_path = self._dir / self.HINTS_FILE

    def _ensure_dirs(self) -> None:
        self._playbooks_dir.mkdir(parents=True, exist_ok=True)

    # -- playbooks ----------------------------------------------------------

    def store_playbook(self, name: str, content: str) -> None:
        """Persist a playbook by name."""
        self._ensure_dirs()
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
        path = self._playbooks_dir / f"{safe_name}.json"
        entry = {
            "name": name,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Stored playbook '%s'", name)

    def get_relevant_playbooks(self, context: str) -> list[dict]:
        """Return playbooks whose name or content contain keywords from *context*.

        Performs simple case-insensitive keyword matching: each word in
        *context* is checked against playbook names and content.
        """
        if not self._playbooks_dir.exists():
            return []
        keywords = {w.lower() for w in context.split() if len(w) > 2}
        results: list[dict] = []
        for path in sorted(self._playbooks_dir.glob("*.json")):
            try:
                entry = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            haystack = (entry.get("name", "") + " " + entry.get("content", "")).lower()
            if any(kw in haystack for kw in keywords):
                results.append(entry)
        return results

    # -- hints --------------------------------------------------------------

    def _load_hints(self) -> list[dict]:
        if not self._hints_path.exists():
            return []
        return json.loads(self._hints_path.read_text(encoding="utf-8"))

    def _save_hints(self, data: list[dict]) -> None:
        self._ensure_dirs()
        self._hints_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def store_hint(self, hint: str, tags: list[str]) -> None:
        """Append a tagged hint to the hints store."""
        data = self._load_hints()
        entry = {
            "hint": hint,
            "tags": tags,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data.append(entry)
        self._save_hints(data)
        logger.info("Stored hint with tags %s", tags)
