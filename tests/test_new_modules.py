"""Tests for new modules: migration, dashboard, API, marketplace."""

from pathlib import Path

import yaml

from vortex.api import VortexAPI
from vortex.dashboard import get_dashboard_html, get_status
from vortex.marketplace import PluginInfo, PluginMarketplace
from vortex.migration import ManifestMigrator


def test_dashboard_html():
    """Test dashboard HTML generation."""
    html = get_dashboard_html()
    assert "VORTEX" in html


def test_dashboard_status():
    """Test dashboard status."""
    status = get_status()
    assert status["version"] == "0.1.0"
    assert status["tests"] == 92


def test_api_status():
    """Test API status endpoint."""
    api = VortexAPI()
    result = api.handle_request("GET", "/api/status")
    assert result["version"] == "0.1.0"


def test_api_health():
    """Test API health endpoint."""
    api = VortexAPI()
    result = api.handle_request("GET", "/api/health")
    assert result["status"] == "healthy"


def test_api_not_found():
    """Test API 404."""
    api = VortexAPI()
    result = api.handle_request("GET", "/api/nonexistent")
    assert "error" in result


def test_marketplace_crud():
    """Test plugin marketplace CRUD."""
    market = PluginMarketplace(Path("/tmp/vortex_market_test"))
    plugin = PluginInfo(name="test-plugin", version="1.0.0", description="Test", author="Test", category="metric")
    market.install(plugin)
    assert len(market.list_installed()) == 1
    market.uninstall("test-plugin")
    assert len(market.list_installed()) == 0


def test_marketplace_search():
    """Test plugin search."""
    market = PluginMarketplace(Path("/tmp/vortex_market_test"))
    market.install(PluginInfo(name="prometheus", version="1.0", description="Metrics", author="Test", category="metric"))
    results = market.search("prometheus")
    assert len(results) == 1


def test_migration(tmp_project: Path):
    """Test manifest migration."""
    manifest_path = tmp_project / "vortex.yaml"
    manifest_path.write_text(yaml.dump({
        "name": "test",
        "project_path": str(tmp_project),
        "metrics": [{"name": "m", "source": "echo 1", "direction": "up"}],
        "optimizer": {"max_changes": 5},  # deprecated field
    }))
    migrator = ManifestMigrator()
    migrator.migrate(manifest_path)
    migrated = yaml.safe_load(manifest_path.read_text())
    assert migrated.get("version") == "2.0"
