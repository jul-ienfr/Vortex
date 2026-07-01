"""Tests for the LLM Factory."""

from pathlib import Path

from vortex.llm_factory import LLMClient, ClaudeCodeClient, LitellmClient, create_client
from vortex.manifest import ManifestConfig


def test_llm_client_interface():
    """Test LLMClient is abstract."""
    try:
        client = LLMClient()
        client.complete("test")
        assert False, "Should have raised NotImplementedError"
    except TypeError:
        pass  # Can't instantiate abstract class


def test_claude_code_client_creation(tmp_project: Path):
    """Test creating a ClaudeCodeClient."""
    # This will fail if Claude Code is not installed, which is expected
    try:
        client = ClaudeCodeClient(tmp_project)
        assert client.project_path == tmp_project
    except FileNotFoundError:
        pass  # Claude Code not installed in test env


def test_litellm_client_creation():
    """Test creating a LitellmClient."""
    client = LitellmClient(model="test-model", proxy="http://localhost:8080/v1")
    assert client.model == "test-model"
    assert client.proxy == "http://localhost:8080/v1"


def test_create_client_default(tmp_project: Path):
    """Test create_client defaults to Claude Code."""
    manifest_path = tmp_project / "vortex.yaml"
    manifest_path.write_text("""
name: test
project_path: {}
metrics:
  - name: test
    source: "echo 42"
    direction: up
optimizer:
  cli: claude
""".format(tmp_project))

    manifest = ManifestConfig.from_yaml(manifest_path)
    client = create_client(manifest)
    assert isinstance(client, ClaudeCodeClient)


def test_create_client_litellm(tmp_project: Path):
    """Test create_client with litellm."""
    manifest_path = tmp_project / "vortex.yaml"
    manifest_path.write_text("""
name: test
project_path: {}
metrics:
  - name: test
    source: "echo 42"
    direction: up
optimizer:
  cli: litellm
  model: mimo-v2.5
  model_proxy: http://192.168.31.59:4000/v1
""".format(tmp_project))

    manifest = ManifestConfig.from_yaml(manifest_path)
    client = create_client(manifest)
    assert isinstance(client, LitellmClient)
