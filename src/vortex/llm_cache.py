"""LLM response cache to avoid redundant API calls."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


class LLMCache:
    """Cache for LLM responses to reduce costs."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, prompt: str) -> str | None:
        """Get a cached response for a prompt."""
        key = self._hash_prompt(prompt)
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        data = json.loads(cache_file.read_text())
        if datetime.fromisoformat(data["timestamp"]) + self.ttl < datetime.now():
            cache_file.unlink()
            return None
        return data["response"]

    def set(self, prompt: str, response: str) -> None:
        """Cache a response."""
        key = self._hash_prompt(prompt)
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "response": response,
        }))

    def clear(self) -> int:
        """Clear all cached responses. Returns count of removed entries."""
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """Hash a prompt for cache key."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
