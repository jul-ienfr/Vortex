"""Dynamic plugin loading for VORTEX."""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    """Manifest for a VORTEX plugin."""

    name: str
    version: str
    description: str
    author: str
    plugin_type: str  # "metric", "optimizer", "reporter", "notifier"
    entry_point: str  # module.path:ClassName
    config: dict = field(default_factory=dict)


class PluginLoader:
    """Loads and manages VORTEX plugins."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.plugins_path = project_path / ".vortex" / "plugins.json"
        self.manifests: list[PluginManifest] = []
        self.loaded: dict[str, any] = {}
        self._load()

    def _load(self) -> None:
        if self.plugins_path.exists():
            data = json.loads(self.plugins_path.read_text())
            self.manifests = [PluginManifest(**p) for p in data.get("plugins", [])]

    def _save(self) -> None:
        self.plugins_path.parent.mkdir(parents=True, exist_ok=True)
        self.plugins_path.write_text(json.dumps({
            "plugins": [asdict(m) for m in self.manifests]
        }, indent=2))

    def register(self, manifest: PluginManifest) -> None:
        """Register a plugin."""
        self.manifests.append(manifest)
        self._save()

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        self.manifests = [m for m in self.manifests if m.name != name]
        self.loaded.pop(name, None)
        self._save()

    def load_plugin(self, name: str) -> any:
        """Load a plugin by name."""
        if name in self.loaded:
            return self.loaded[name]

        manifest = next((m for m in self.manifests if m.name == name), None)
        if not manifest:
            raise ValueError(f"Plugin {name} not found")

        try:
            module_path, class_name = manifest.entry_point.rsplit(":", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            instance = cls()
            self.loaded[name] = instance
            logger.info("Loaded plugin: %s", name)
            return instance
        except Exception as e:
            logger.error("Failed to load plugin %s: %s", name, e)
            raise

    def load_all(self) -> dict[str, any]:
        """Load all registered plugins."""
        for manifest in self.manifests:
            try:
                self.load_plugin(manifest.name)
            except Exception as e:
                logger.warning("Skipping plugin %s: %s", manifest.name, e)
        return self.loaded

    def list_plugins(self) -> list[PluginManifest]:
        """List all registered plugins."""
        return self.manifests
