"""Circuit breaker pattern for VORTEX."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker."""

    failure_count: int = 0
    state: str = "closed"  # closed, open, half-open
    last_failure_time: float = 0.0


class CircuitBreaker:
    """Protects against cascading failures to a failing service."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.states: dict[str, CircuitBreakerState] = {}

    def _get_state(self, name: str) -> CircuitBreakerState:
        if name not in self.states:
            self.states[name] = CircuitBreakerState()
        return self.states[name]

    def call(self, name: str, func, *args, **kwargs):
        """Execute a function with circuit breaker protection."""
        state = self._get_state(name)

        if state.state == "open":
            if time.time() - state.last_failure_time > self.reset_timeout:
                state.state = "half-open"
                logger.info("Circuit breaker %s: half-open", name)
            else:
                raise CircuitBreakerOpen(f"Circuit breaker {name} is open")

        try:
            result = func(*args, **kwargs)
            if state.state == "half-open":
                state.state = "closed"
                state.failure_count = 0
                logger.info("Circuit breaker %s: closed (recovered)", name)
            return result
        except Exception as e:
            state.failure_count += 1
            state.last_failure_time = time.time()
            if state.failure_count >= self.failure_threshold:
                state.state = "open"
                logger.warning("Circuit breaker %s: open (failures=%d)", name, state.failure_count)
            raise

    def get_state(self, name: str) -> str:
        """Get the state of a circuit breaker."""
        return self._get_state(name).state


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is open."""
    pass
