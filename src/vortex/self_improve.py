"""Self-improvement engine for VORTEX."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Analysis of the optimizer's own performance."""

    total_cycles: int = 0
    success_rate: float = 0.0
    avg_score_delta: float = 0.0
    best_performing_cli: str = ""
    most_effective_patterns: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    cost_per_improvement: float = 0.0
    skill_hit_rate: float = 0.0
    gate_pass_rate: float = 0.0


@dataclass
class MetaSuggestion:
    """A suggestion for improving the optimizer itself."""

    parameter: str
    current_value: str
    suggested_value: str
    reason: str
    confidence: float = 0.0


class SelfImprover:
    """Analyzes and improves the optimizer itself."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.history_path = project_path / ".vortex" / "self_improve_history.json"

    def analyze_performance(self, cycle_history: list[dict]) -> PerformanceReport:
        """Analyze the optimizer's own performance from cycle history."""
        if not cycle_history:
            return PerformanceReport()

        total = len(cycle_history)
        kept = sum(1 for c in cycle_history if c.get("decision") == "kept")
        reverted = sum(1 for c in cycle_history if c.get("decision") == "reverted")

        score_deltas = [c.get("score_delta", 0) for c in cycle_history]
        avg_delta = sum(score_deltas) / len(score_deltas) if score_deltas else 0

        return PerformanceReport(
            total_cycles=total,
            success_rate=kept / total if total > 0 else 0,
            avg_score_delta=avg_delta,
        )

    def generate_suggestions(self, report: PerformanceReport) -> list[MetaSuggestion]:
        """Generate suggestions for improving the optimizer."""
        suggestions = []

        # If success rate is low, reduce changes per cycle
        if report.success_rate < 0.3:
            suggestions.append(MetaSuggestion(
                parameter="max_changes_per_cycle",
                current_value="3",
                suggested_value="1",
                reason=f"Low success rate ({report.success_rate:.0%}) — reduce change volume",
                confidence=0.8,
            ))

        # If score is stagnating, increase reflection depth
        if report.avg_score_delta < 0.01 and report.total_cycles > 5:
            suggestions.append(MetaSuggestion(
                parameter="reflection_depth",
                current_value="1",
                suggested_value="3",
                reason="Scores stagnating — deeper reflection may help",
                confidence=0.6,
            ))

        # If cost per improvement is high, suggest simpler CLI
        if report.cost_per_improvement > 1.0:
            suggestions.append(MetaSuggestion(
                parameter="cli",
                current_value="claude",
                suggested_value="codex",
                reason=f"High cost per improvement (${report.cost_per_improvement:.2f})",
                confidence=0.5,
            ))

        return suggestions

    def record_suggestion(self, suggestion: MetaSuggestion, applied: bool) -> None:
        """Record that a suggestion was made (and whether it was applied)."""
        record = {
            "parameter": suggestion.parameter,
            "suggested_value": suggestion.suggested_value,
            "reason": suggestion.reason,
            "applied": applied,
        }
        history = self._load_history()
        history.append(record)
        self._save_history(history)

    def _load_history(self) -> list[dict]:
        if self.history_path.exists():
            return json.loads(self.history_path.read_text())
        return []

    def _save_history(self, history: list[dict]) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(json.dumps(history, indent=2))
