"""Tests for server and config modules."""

from pathlib import Path

from vortex.config import ConfigManager, VortexConfig
from vortex.server import VortexHandler


def test_config_defaults():
    """Test default config values."""
    config = VortexConfig()
    assert config.default_model == "claude-sonnet-4-6"
    assert config.sandbox_enabled is False
    assert config.audit_trail_enabled is True


def test_config_manager(tmp_project: Path):
    """Test config manager."""
    manager = ConfigManager(tmp_project / ".vortex" / "config.json")
    assert manager.get("default_model") == "claude-sonnet-4-6"
    manager.set("default_model", "gpt-4o")
    assert manager.get("default_model") == "gpt-4o"


def test_config_reset(tmp_project: Path):
    """Test config reset."""
    manager = ConfigManager(tmp_project / ".vortex" / "config.json")
    manager.set("default_model", "custom")
    manager.reset()
    assert manager.get("default_model") == "claude-sonnet-4-6"
