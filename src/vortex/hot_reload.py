"""Hot reload for manifest changes."""

from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class ManifestWatcher:
    """Watches for manifest changes and triggers reload."""

    def __init__(self, manifest_path: Path, on_change):
        self.manifest_path = manifest_path
        self.on_change = on_change
        self.last_mtime: float = 0
        if manifest_path.exists():
            self.last_mtime = manifest_path.stat().st_mtime

    def check(self) -> bool:
        """Check if the manifest has changed. Returns True if changed."""
        if not self.manifest_path.exists():
            return False
        current_mtime = self.manifest_path.stat().st_mtime
        if current_mtime > self.last_mtime:
            self.last_mtime = current_mtime
            logger.info("Manifest changed, reloading...")
            try:
                from vortex.manifest import ManifestConfig
                new_manifest = ManifestConfig.from_yaml(self.manifest_path)
                self.on_change(new_manifest)
                return True
            except Exception as e:
                logger.error("Failed to reload manifest: %s", e)
                return False
        return False

    def watch(self, interval: float = 1.0) -> None:
        """Watch for changes in a loop."""
        logger.info("Watching %s for changes...", self.manifest_path)
        try:
            while True:
                self.check()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Stopped watching.")
