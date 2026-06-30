"""Resource governor for limiting CPU, memory, disk, and API usage."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Limits for resource usage."""

    max_memory_mb: int = 512
    max_disk_mb: int = 1000
    max_cpu_percent: float = 80.0
    max_api_calls_per_minute: int = 60
    max_llm_tokens_per_hour: int = 100_000


class ResourceGovernor:
    """Monitors and limits resource usage."""

    def __init__(self, limits: ResourceLimits | None = None):
        self.limits = limits or ResourceLimits()
        self.api_calls: list[float] = []
        self.llm_tokens: int = 0
        self.llm_tokens_reset: float = time.time()

    def check_api_call(self) -> bool:
        """Check if an API call is allowed (rate limiting)."""
        now = time.time()
        # Remove calls older than 1 minute
        self.api_calls = [t for t in self.api_calls if now - t < 60]
        if len(self.api_calls) >= self.limits.max_api_calls_per_minute:
            logger.warning("API rate limit reached: %d calls/min", len(self.api_calls))
            return False
        self.api_calls.append(now)
        return True

    def record_llm_tokens(self, tokens: int) -> None:
        """Record LLM token usage."""
        now = time.time()
        # Reset hourly counter
        if now - self.llm_tokens_reset > 3600:
            self.llm_tokens = 0
            self.llm_tokens_reset = now
        self.llm_tokens += tokens

    def check_llm_budget(self) -> bool:
        """Check if LLM token budget is available."""
        if self.llm_tokens >= self.limits.max_llm_tokens_per_hour:
            logger.warning("LLM token budget exhausted: %d/%d", self.llm_tokens, self.limits.max_llm_tokens_per_hour)
            return False
        return True

    def get_usage(self) -> dict:
        """Get current resource usage."""
        return {
            "api_calls_last_minute": len(self.api_calls),
            "api_limit": self.limits.max_api_calls_per_minute,
            "llm_tokens_this_hour": self.llm_tokens,
            "llm_token_limit": self.limits.max_llm_tokens_per_hour,
        }

    def should_stop(self) -> tuple[bool, str]:
        """Check if any resource limit is exceeded."""
        if not self.check_api_call():
            return True, "API rate limit exceeded"
        if not self.check_llm_budget():
            return True, "LLM token budget exhausted"
        return False, ""
