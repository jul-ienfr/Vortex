"""Simple API for VORTEX."""

from __future__ import annotations

import json
from pathlib import Path

from vortex.dashboard import get_status


class VortexAPI:
    """Simple REST-like API for VORTEX."""

    def __init__(self, vortex_home: Path | None = None):
        self.home = vortex_home or Path.home() / ".vortex"

    def handle_request(self, method: str, path: str, body: dict | None = None) -> dict:
        """Handle an API request."""
        if method == "GET" and path == "/api/status":
            return get_status()
        elif method == "GET" and path == "/api/projects":
            return self._list_projects()
        elif method == "GET" and path.startswith("/api/projects/") and path.endswith("/metrics"):
            project_id = path.split("/")[3]
            return self._get_project_metrics(project_id)
        elif method == "POST" and path == "/api/projects":
            return self._add_project(body or {})
        elif method == "GET" and path == "/api/health":
            return {"status": "healthy", "version": "0.1.0"}
        else:
            return {"error": f"Not found: {method} {path}"}

    def _list_projects(self) -> dict:
        registry_path = self.home / "registry.json"
        if registry_path.exists():
            data = json.loads(registry_path.read_text())
            return {"projects": data.get("projects", [])}
        return {"projects": []}

    def _get_project_metrics(self, project_id: str) -> dict:
        return {"project_id": project_id, "metrics": {}}

    def _add_project(self, body: dict) -> dict:
        return {"status": "added", "project": body.get("name", "unknown")}
