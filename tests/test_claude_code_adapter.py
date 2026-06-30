"""Tests for the Claude Code adapter."""

from pathlib import Path

from vortex.claude_code_adapter import ClaudeCodeAdapter, ProjectAnalysis, OptimizationResult


def test_claude_code_adapter_creation(tmp_project: Path):
    """Test creating a ClaudeCodeAdapter."""
    adapter = ClaudeCodeAdapter(tmp_project)
    assert adapter.project_path == tmp_project


def test_project_analysis():
    """Test ProjectAnalysis creation."""
    analysis = ProjectAnalysis(
        files=["test.py"],
        issues=["issue1"],
        improvements=["improvement1"],
    )
    assert len(analysis.files) == 1
    assert len(analysis.issues) == 1


def test_optimization_result():
    """Test OptimizationResult creation."""
    result = OptimizationResult(
        success=True,
        changes_made=["change1"],
        tests_passed=True,
    )
    assert result.success is True
    assert result.tests_passed is True
