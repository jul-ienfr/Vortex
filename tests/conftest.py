"""Shared test fixtures for VORTEX."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


def pytest_configure(config):
    config.addinivalue_line("testpaths", ".")
    config.addinivalue_line("python_files", "test_*.py")
    config.addinivalue_line("python_classes", "Test*")
    config.addinivalue_line("python_functions", "test_*")
    config.addinivalue_line("addopts", "--tb=short -q --count=132")


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary git project for testing."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_path, capture_output=True)

    # Create a test file
    (project_path / "test.py").write_text("def test(): return 42")
    subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=project_path, capture_output=True)

    return project_path


@pytest.fixture
def tmp_manifest(tmp_project: Path) -> Path:
    """Create a temporary VORTEX manifest."""
    manifest_path = tmp_project / "vortex.yaml"
    manifest_data = {
        "name": "test_project",
        "project_path": str(tmp_project),
        "metrics": [
            {
                "name": "test_metric",
                "source": "echo 42",
                "direction": "up",
            }
        ],
        "optimizer": {
            "cli": "claude",
            "max_changes_per_cycle": 1,
        },
    }
    manifest_path.write_text(yaml.dump(manifest_data))
    return manifest_path