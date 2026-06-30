"""Hook management for VORTEX."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Hook:
    """A hook triggered at specific moments."""

    id: str
    name: str
    trigger: str  # "before_cycle", "after_cycle", "on_success", "on_failure", etc.
    command: str
    enabled: bool = True
    priority: int = 0


class HookManager:
    """CRUD for optimization hooks."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.hooks_path = project_path / ".vortex" / "hooks.json"
        self.hooks: list[Hook] = []
        self._load()

    def _load(self) -> None:
        if self.hooks_path.exists():
            data = json.loads(self.hooks_path.read_text())
            self.hooks = [Hook(**h) for h in data.get("hooks", [])]

    def _save(self) -> None:
        self.hooks_path.parent.mkdir(parents=True, exist_ok=True)
        self.hooks_path.write_text(json.dumps({"hooks": [asdict(h) for h in self.hooks]}, indent=2))

    def create_hook(self, name: str, trigger: str, command: str, priority: int = 0) -> Hook:
        hook = Hook(id=f"hook_{len(self.hooks)}", name=name, trigger=trigger, command=command, priority=priority)
        self.hooks.append(hook)
        self._save()
        return hook

    def list_hooks(self, trigger: str | None = None) -> list[Hook]:
        if trigger:
            return [h for h in self.hooks if h.trigger == trigger]
        return self.hooks

    def get_hook(self, hook_id: str) -> Hook | None:
        return next((h for h in self.hooks if h.id == hook_id), None)

    def update_hook(self, hook_id: str, **kwargs) -> Hook | None:
        hook = self.get_hook(hook_id)
        if not hook:
            return None
        for key, value in kwargs.items():
            if hasattr(hook, key):
                setattr(hook, key, value)
        self._save()
        return hook

    def delete_hook(self, hook_id: str) -> None:
        self.hooks = [h for h in self.hooks if h.id != hook_id]
        self._save()

    def trigger(self, event: str, context: dict) -> None:
        matching = sorted(
            [h for h in self.hooks if h.trigger == event and h.enabled],
            key=lambda h: h.priority,
        )
        for hook in matching:
            try:
                cmd = hook.command
                for key, value in context.items():
                    cmd = cmd.replace(f"{{{key}}}", str(value))
                subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            except Exception as e:
                logger.warning("Hook %s failed: %s", hook.name, e)
