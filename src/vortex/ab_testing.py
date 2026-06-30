"""A/B testing for optimization strategies."""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ABTest:
    """An A/B test between two strategies."""

    id: str
    name: str
    strategy_a: dict = field(default_factory=dict)
    strategy_b: dict = field(default_factory=dict)
    results_a: list[float] = field(default_factory=list)
    results_b: list[float] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: str(int(time.time())))


@dataclass
class ABTestResult:
    """Result of an A/B test analysis."""

    winner: str  # "a", "b", or "tie"
    score_a: float = 0.0
    score_b: float = 0.0
    improvement: float = 0.0
    samples: int = 0


class ABTestManager:
    """Manages A/B tests between optimization strategies."""

    def __init__(self, project_path: Path):
        self.tests_path = project_path / ".vortex" / "ab_tests.json"
        self.tests: list[ABTest] = []
        self._load()

    def _load(self) -> None:
        if self.tests_path.exists():
            data = json.loads(self.tests_path.read_text())
            self.tests = [ABTest(**t) for t in data.get("tests", [])]

    def _save(self) -> None:
        self.tests_path.parent.mkdir(parents=True, exist_ok=True)
        self.tests_path.write_text(json.dumps({"tests": [asdict(t) for t in self.tests]}, indent=2))

    def create_test(self, name: str, strategy_a: dict, strategy_b: dict) -> ABTest:
        """Create a new A/B test."""
        test = ABTest(
            id=f"ab_{int(time.time())}",
            name=name,
            strategy_a=strategy_a,
            strategy_b=strategy_b,
        )
        self.tests.append(test)
        self._save()
        return test

    def assign(self, test_id: str) -> str:
        """Randomly assign to strategy A or B."""
        return random.choice(["a", "b"])

    def record_result(self, test_id: str, strategy: str, score: float) -> None:
        """Record a result for a strategy."""
        test = next((t for t in self.tests if t.id == test_id), None)
        if not test:
            return
        if strategy == "a":
            test.results_a.append(score)
        else:
            test.results_b.append(score)
        self._save()

    def analyze(self, test_id: str) -> ABTestResult:
        """Analyze the results of an A/B test."""
        test = next((t for t in self.tests if t.id == test_id), None)
        if not test:
            return ABTestResult(winner="tie")

        avg_a = sum(test.results_a) / len(test.results_a) if test.results_a else 0
        avg_b = sum(test.results_b) / len(test.results_b) if test.results_b else 0

        if avg_a > avg_b:
            winner = "a"
            improvement = (avg_a - avg_b) / max(abs(avg_b), 0.001)
        elif avg_b > avg_a:
            winner = "b"
            improvement = (avg_b - avg_a) / max(abs(avg_a), 0.001)
        else:
            winner = "tie"
            improvement = 0.0

        return ABTestResult(
            winner=winner,
            score_a=avg_a,
            score_b=avg_b,
            improvement=improvement,
            samples=len(test.results_a) + len(test.results_b),
        )

    def list_tests(self) -> list[ABTest]:
        """List all tests."""
        return self.tests
