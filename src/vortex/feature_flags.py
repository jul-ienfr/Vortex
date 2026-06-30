"""Feature flags for dynamic enable/disable."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_FLAGS = {
    "debate_enabled": True,
    "tree_search_enabled": True,
    "research_enabled": True,
    "self_improve_enabled": True,
    "skill_library_enabled": True,
    "sandbox_enabled": False,
    "audit_trail_enabled": True,
    "ab_testing_enabled": False,
    "hot_reload_enabled": True,
    "resource_governor_enabled": True,
}


class FeatureFlags:
    """Feature flags that can be toggled dynamically."""

    def __init__(self, project_path: Path):
        self.flags_path = project_path / ".vortex" / "flags.json"
        self.flags: dict[str, bool] = {}
        self._load()

    def _load(self) -> None:
        if self.flags_path.exists():
            self.flags = json.loads(self.flags_path.read_text())
        else:
            self.flags = DEFAULT_FLAGS.copy()

    def _save(self) -> None:
        self.flags_path.parent.mkdir(parents=True, exist_ok=True)
        self.flags_path.write_text(json.dumps(self.flags, indent=2))

    def is_enabled(self, flag: str) -> bool:
        """Check if a flag is enabled."""
        return self.flags.get(flag, DEFAULT_FLAGS.get(flag, False))

    def toggle(self, flag: str) -> bool:
        """Toggle a flag. Returns new state."""
        self.flags[flag] = not self.is_enabled(flag)
        self._save()
        return self.flags[flag]

    def enable(self, flag: str) -> None:
        """Enable a flag."""
        self.flags[flag] = True
        self._save()

    def disable(self, flag: str) -> None:
        """Disable a flag."""
        self.flags[flag] = False
        self._save()

    def list_flags(self) -> dict[str, bool]:
        """List all flags and their states."""
        return {k: self.is_enabled(k) for k in DEFAULT_FLAGS}
