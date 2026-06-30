"""Centralized configuration for VORTEX."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class VortexConfig:
    """Global VORTEX configuration."""

    # Paths
    vortex_home: str = "~/.vortex"
    default_manifest: str = "vortex.yaml"

    # LLM
    default_model: str = "claude-sonnet-4-6"
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    llm_cache_ttl_hours: int = 24

    # Optimization
    default_max_cycles: int = 100
    default_budget_usd: float = 10.0
    convergence_stagnation_limit: int = 10

    # Safety
    sandbox_enabled: bool = False
    audit_trail_enabled: bool = True
    max_command_timeout: int = 30

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None

    # Webhooks
    webhooks_enabled: bool = False


class ConfigManager:
    """Manages VORTEX configuration."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or Path.home() / ".vortex" / "config.json"
        self.config = VortexConfig()
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            data = json.loads(self.config_path.read_text())
            for key, value in data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

    def _save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(asdict(self.config), indent=2))

    def get(self, key: str) -> any:
        """Get a config value."""
        return getattr(self.config, key, None)

    def set(self, key: str, value: any) -> None:
        """Set a config value."""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self._save()

    def reset(self) -> None:
        """Reset to defaults."""
        self.config = VortexConfig()
        self._save()
