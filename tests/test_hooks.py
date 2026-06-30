"""Tests for hooks and registry."""

from pathlib import Path

from vortex.hooks import HookManager
from vortex.registry import ProjectRegistry


def test_hook_crud(tmp_project: Path):
    """Test hook CRUD operations."""
    manager = HookManager(tmp_project)
    hook = manager.create_hook("test", "before_cycle", "echo test")
    assert hook.name == "test"
    assert manager.get_hook(hook.id) is not None
    manager.delete_hook(hook.id)
    assert manager.get_hook(hook.id) is None


def test_hook_list(tmp_project: Path):
    """Test listing hooks."""
    manager = HookManager(tmp_project)
    manager.create_hook("h1", "before_cycle", "echo 1")
    manager.create_hook("h2", "after_cycle", "echo 2")
    assert len(manager.list_hooks()) == 2
    assert len(manager.list_hooks(trigger="before_cycle")) == 1


def test_registry():
    """Test project registry."""
    registry = ProjectRegistry(Path("/tmp/vortex_test"))
    entry = registry.register("test", Path("/tmp/test"), Path("/tmp/test/vortex.yaml"))
    assert entry.name == "test"
    assert len(registry.list_projects()) == 1
    registry.unregister(entry.id)
    assert len(registry.list_projects()) == 0
