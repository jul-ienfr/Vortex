"""Project registry for multi-project management."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ProjectEntry:
    """A registered project."""

    id: str
    name: str
    path: str
    manifest_path: str
    status: str = "active"
    created_at: str = field(default_factory=lambda: str(int(time.time())))
    last_optimized: str | None = None
    optimization_cycles: int = 0
    best_score: float = 0.0
    tags: list[str] = field(default_factory=list)


class ProjectRegistry:
    """Registry of projects managed by VORTEX."""

    def __init__(self, vortex_home: Path | None = None):
        self.home = vortex_home or Path.home() / ".vortex"
        self.registry_path = self.home / "registry.json"
        self.projects: list[ProjectEntry] = []
        self._load()

    def _load(self) -> None:
        if self.registry_path.exists():
            data = json.loads(self.registry_path.read_text())
            self.projects = [ProjectEntry(**p) for p in data.get("projects", [])]

    def _save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps({"projects": [asdict(p) for p in self.projects]}, indent=2))

    def register(self, name: str, path: Path, manifest_path: Path) -> ProjectEntry:
        entry = ProjectEntry(
            id=f"proj_{int(time.time())}",
            name=name,
            path=str(path),
            manifest_path=str(manifest_path),
        )
        self.projects.append(entry)
        self._save()
        return entry

    def unregister(self, project_id: str) -> None:
        self.projects = [p for p in self.projects if p.id != project_id]
        self._save()

    def list_projects(self, status: str | None = None) -> list[ProjectEntry]:
        if status:
            return [p for p in self.projects if p.status == status]
        return self.projects

    def get_project(self, project_id: str) -> ProjectEntry | None:
        return next((p for p in self.projects if p.id == project_id), None)
