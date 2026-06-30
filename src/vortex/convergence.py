"""Convergence detection for VORTEX optimization cycles."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConvergenceConfig:
    """Configuration for convergence detection."""

    stagnation_limit: int = 10
    window_size: int = 20
    convergence_threshold: float = 0.001
    target_score: float | None = None
    budget_limit_usd: float | None = None
    min_cycles: int = 5


class ConvergenceDetector:
    """Detects when the optimizer has reached an optimal state."""

    def __init__(self, config: ConvergenceConfig | None = None):
        self.config = config or ConvergenceConfig()
        self.history: list[float] = []
        self.no_improvement_count: int = 0
        self.best_score: float = 0.0
        self.best_cycle: int = 0
        self.total_cost: float = 0.0

    def record_score(self, score: float, cycle_num: int) -> None:
        """Record the score of a cycle."""
        self.history.append(score)

        if score > self.best_score:
            self.best_score = score
            self.best_cycle = cycle_num
            self.no_improvement_count = 0
        else:
            self.no_improvement_count += 1

    def record_cost(self, cost: float) -> None:
        """Record accumulated cost."""
        self.total_cost += cost

    def should_stop(self) -> tuple[bool, str]:
        """Determine if the optimizer should stop."""
        # Minimum cycles
        if len(self.history) < self.config.min_cycles:
            return False, ""

        # Stagnation
        if self.no_improvement_count >= self.config.stagnation_limit:
            return True, f"Stagnation: no improvement for {self.no_improvement_count} cycles"

        # Variance-based convergence
        if len(self.history) >= self.config.window_size:
            recent = self.history[-self.config.window_size :]
            variance = max(recent) - min(recent)
            if variance < self.config.convergence_threshold:
                return True, f"Convergence: variance {variance:.6f} < threshold {self.config.convergence_threshold}"

        # Target score
        if self.config.target_score is not None and self.best_score >= self.config.target_score:
            return True, f"Target reached: score {self.best_score:.3f} >= target {self.config.target_score}"

        # Budget
        if self.config.budget_limit_usd is not None and self.total_cost >= self.config.budget_limit_usd:
            return True, f"Budget exhausted: ${self.total_cost:.2f} >= ${self.config.budget_limit_usd}"

        return False, ""

    def get_stats(self) -> dict:
        """Return convergence statistics."""
        return {
            "total_cycles": len(self.history),
            "best_score": self.best_score,
            "best_cycle": self.best_cycle,
            "current_score": self.history[-1] if self.history else 0,
            "no_improvement_count": self.no_improvement_count,
            "convergence_status": self._convergence_status(),
            "total_cost": self.total_cost,
        }

    def _convergence_status(self) -> str:
        """Return convergence status string."""
        if self.no_improvement_count == 0:
            return "improving"
        elif self.no_improvement_count < self.config.stagnation_limit:
            return "slowing"
        else:
            return "converged"
