"""Plugin marketplace for VORTEX."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class PluginInfo:
    """Information about a plugin."""

    name: str
    version: str
    description: str
    author: str
    category: str  # "metric", "optimizer", "reporter", "notifier", "scheduler"
    tags: list[str] = field(default_factory=list)
    rating: float = 0.0
    installs: int = 0


class PluginMarketplace:
    """Marketplace of plugins for VORTEX."""

    def __init__(self, vortex_home: Path | None = None):
        self.home = vortex_home or Path.home() / ".vortex"
        self.plugins_path = self.home / "marketplace.json"
        self.plugins: list[PluginInfo] = []
        self._load()

    def _load(self) -> None:
        if self.plugins_path.exists():
            data = json.loads(self.plugins_path.read_text())
            self.plugins = [PluginInfo(**p) for p in data.get("plugins", [])]

    def _save(self) -> None:
        self.plugins_path.parent.mkdir(parents=True, exist_ok=True)
        self.plugins_path.write_text(json.dumps({"plugins": [asdict(p) for p in self.plugins]}, indent=2))

    def search(self, query: str, category: str | None = None) -> list[PluginInfo]:
        """Search for plugins."""
        results = self.plugins
        if category:
            results = [p for p in results if p.category == category]
        if query:
            query_lower = query.lower()
            results = [p for p in results if query_lower in p.name.lower() or query_lower in p.description.lower()]
        return results

    def install(self, plugin: PluginInfo) -> None:
        """Install a plugin."""
        self.plugins.append(plugin)
        self._save()

    def uninstall(self, plugin_name: str) -> None:
        """Uninstall a plugin."""
        self.plugins = [p for p in self.plugins if p.name != plugin_name]
        self._save()

    def rate(self, plugin_name: str, rating: float) -> None:
        """Rate a plugin."""
        for p in self.plugins:
            if p.name == plugin_name:
                p.rating = rating
                self._save()
                return

    def list_installed(self) -> list[PluginInfo]:
        """List installed plugins."""
        return self.plugins
