"""Incremental analysis - only scan changed files."""

from __future__ import annotations

import json
from pathlib import Path


class IncrementalAnalyzer:
    """Analyzes only files modified since the last analysis."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.snapshot_file = project_path / ".vortex" / "file_snapshot.json"

    def get_changed_files(self) -> list[Path]:
        """Return files modified since last snapshot."""
        current = self._get_all_files()
        previous = self._load_snapshot()

        changed = []
        for path_str, mtime in current.items():
            if path_str not in previous or mtime > previous[path_str]:
                changed.append(self.project_path / path_str)

        self._save_snapshot(current)
        return changed

    def has_changed(self) -> bool:
        """Check if any files have changed."""
        return len(self.get_changed_files()) > 0

    def _get_all_files(self) -> dict[str, float]:
        """Get {path: mtime} for all source files."""
        result = {}
        for f in self.project_path.rglob("*"):
            if f.is_file() and not f.name.startswith(".") and "__pycache__" not in str(f) and ".vortex" not in str(f):
                try:
                    result[str(f.relative_to(self.project_path))] = f.stat().st_mtime
                except OSError:
                    pass
        return result

    def _load_snapshot(self) -> dict[str, float]:
        if self.snapshot_file.exists():
            return json.loads(self.snapshot_file.read_text())
        return {}

    def _save_snapshot(self, snapshot: dict[str, float]) -> None:
        self.snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_file.write_text(json.dumps(snapshot))
