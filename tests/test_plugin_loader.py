"""Tests for plugin loader."""

from pathlib import Path

from vortex.plugin_loader import PluginLoader, PluginManifest


def test_plugin_registration(tmp_project: Path):
    """Test plugin registration."""
    loader = PluginLoader(tmp_project)
    manifest = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        description="Test plugin",
        author="Test",
        plugin_type="metric",
        entry_point="test:TestPlugin",
    )
    loader.register(manifest)
    assert len(loader.list_plugins()) == 1


def test_plugin_unregister(tmp_project: Path):
    """Test plugin unregistration."""
    loader = PluginLoader(tmp_project)
    manifest = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        description="Test",
        author="Test",
        plugin_type="metric",
        entry_point="test:TestPlugin",
    )
    loader.register(manifest)
    loader.unregister("test-plugin")
    assert len(loader.list_plugins()) == 0


def test_plugin_load_failure(tmp_project: Path):
    """Test plugin load failure."""
    loader = PluginLoader(tmp_project)
    manifest = PluginManifest(
        name="bad-plugin",
        version="1.0.0",
        description="Bad",
        author="Test",
        plugin_type="metric",
        entry_point="nonexistent.module:Plugin",
    )
    loader.register(manifest)
    try:
        loader.load_plugin("bad-plugin")
        assert False, "Should have raised"
    except Exception:
        pass
