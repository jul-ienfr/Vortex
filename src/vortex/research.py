"""Research agent for finding new papers and projects."""

from __future__ import annotations

import json
import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass
class ResearchFinding:
    """A research finding from arXiv or other sources."""

    title: str
    authors: list[str]
    summary: str
    published: str
    link: str
    source: str = "arxiv"
    relevance_score: float = 0.0


@dataclass
class Recommendation:
    """An actionable recommendation from research."""

    title: str
    description: str
    source: str
    priority: str = "medium"  # high, medium, low


@dataclass
class ResearchReport:
    """Report from a research cycle."""

    findings_count: int = 0
    relevant_count: int = 0
    recommendations: list[Recommendation] = field(default_factory=list)


class ResearchAgent:
    """Searches for new papers and projects to improve the optimizer."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.knowledge_path = project_path / ".vortex" / "research.json"

    def research_cycle(self, topics: list[str]) -> ResearchReport:
        """Run a complete research cycle."""
        findings: list[ResearchFinding] = []

        for topic in topics:
            try:
                papers = self._search_arxiv(topic, max_results=10)
                findings.extend(papers)
                time.sleep(3)  # arXiv API etiquette
            except Exception as e:
                logger.warning("Failed to search arXiv for '%s': %s", topic, e)

        # Filter by relevance
        relevant = [f for f in findings if f.relevance_score > 0.3]

        # Generate recommendations
        recommendations = self._generate_recommendations(relevant)

        # Persist
        self._save_findings(findings)

        return ResearchReport(
            findings_count=len(findings),
            relevant_count=len(relevant),
            recommendations=recommendations,
        )

    def _search_arxiv(self, topic: str, max_results: int = 10) -> list[ResearchFinding]:
        """Search arXiv for papers on a topic."""
        params = {
            "search_query": f"all:{topic}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        response = requests.get(ARXIV_API, params=params, timeout=30)
        response.raise_for_status()

        return self._parse_arxiv_response(response.text, topic)

    def _parse_arxiv_response(self, xml_text: str, topic: str) -> list[ResearchFinding]:
        """Parse arXiv Atom XML response."""
        findings = []
        root = ET.fromstring(xml_text)

        for entry in root.findall("atom:entry", ARXIV_NS):
            title = entry.find("atom:title", ARXIV_NS)
            summary = entry.find("atom:summary", ARXIV_NS)
            published = entry.find("atom:published", ARXIV_NS)
            link = entry.find("atom:id", ARXIV_NS)

            authors = []
            for author in entry.findall("atom:author", ARXIV_NS):
                name = author.find("atom:name", ARXIV_NS)
                if name is not None:
                    authors.append(name.text or "")

            finding = ResearchFinding(
                title=title.text.strip() if title is not None else "",
                authors=authors,
                summary=summary.text.strip() if summary is not None else "",
                published=published.text if published is not None else "",
                link=link.text if link is not None else "",
            )

            # Score relevance
            finding.relevance_score = self._score_relevance(finding, topic)
            findings.append(finding)

        return findings

    def _score_relevance(self, finding: ResearchFinding, topic: str) -> float:
        """Score relevance based on keyword overlap."""
        topic_words = set(topic.lower().split())
        text = f"{finding.title} {finding.summary}".lower()
        text_words = set(text.split())

        if not topic_words:
            return 0.0

        overlap = len(topic_words & text_words)
        return min(overlap / len(topic_words), 1.0)

    def _generate_recommendations(self, findings: list[ResearchFinding]) -> list[Recommendation]:
        """Generate actionable recommendations."""
        recommendations = []

        for finding in findings:
            if finding.relevance_score > 0.5:
                recommendations.append(Recommendation(
                    title=finding.title,
                    description=finding.summary[:200],
                    source=finding.link,
                    priority="high" if finding.relevance_score > 0.7 else "medium",
                ))

        return recommendations[:10]  # Top 10

    def get_recent_findings(self, n: int = 5) -> list[dict]:
        """Get recent findings from persistence."""
        if not self.knowledge_path.exists():
            return []
        data = json.loads(self.knowledge_path.read_text())
        return data.get("findings", [])[-n:]

    def _save_findings(self, findings: list[ResearchFinding]) -> None:
        """Persist findings to disk."""
        self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "findings": [
                {
                    "title": f.title,
                    "authors": f.authors,
                    "summary": f.summary[:500],
                    "published": f.published,
                    "link": f.link,
                    "relevance_score": f.relevance_score,
                }
                for f in findings
            ]
        }
        self.knowledge_path.write_text(json.dumps(data, indent=2))
