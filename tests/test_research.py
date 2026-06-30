"""Tests for the research agent."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from vortex.research import Recommendation, ResearchAgent, ResearchFinding, ResearchReport


def test_finding_creation():
    """Test creating a research finding."""
    f = ResearchFinding(title="Test", authors=["A"], summary="Summary", published="2024-01-01", link="http://test.com")
    assert f.title == "Test"
    assert f.relevance_score == 0.0


def test_report_creation():
    """Test creating a research report."""
    r = ResearchReport(findings_count=5, relevant_count=3)
    assert r.findings_count == 5


def test_relevance_scoring():
    """Test relevance scoring."""
    agent = ResearchAgent(Path("/tmp"))
    finding = ResearchFinding(
        title="Self-improving LLM agents",
        authors=[], summary="optimization of language model agents", published="", link=""
    )
    score = agent._score_relevance(finding, "self-improving agents")
    assert score > 0


def test_recommendations():
    """Test recommendation generation."""
    agent = ResearchAgent(Path("/tmp"))
    findings = [
        ResearchFinding(title="Great paper", authors=[], summary="test", published="", link="http://test.com", relevance_score=0.8),
        ResearchFinding(title="Bad paper", authors=[], summary="test", published="", link="", relevance_score=0.1),
    ]
    recs = agent._generate_recommendations(findings)
    assert len(recs) == 1  # only high-relevance
    assert recs[0].priority == "high"


def test_persistence(tmp_project: Path):
    """Test findings persistence."""
    agent = ResearchAgent(tmp_project)
    findings = [ResearchFinding(title="Test", authors=[], summary="s", published="", link="")]
    agent._save_findings(findings)
    loaded = agent.get_recent_findings()
    assert len(loaded) == 1
    assert loaded[0]["title"] == "Test"


def test_empty_topics(tmp_project: Path):
    """Test with empty topics."""
    agent = ResearchAgent(tmp_project)
    report = agent.research_cycle([])
    assert report.findings_count == 0
