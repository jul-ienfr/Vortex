"""Skill library with crystallization for VORTEX."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """An optimization skill."""

    id: str
    name: str
    description: str
    change_template: str
    success_count: int = 0
    failure_count: int = 0
    consecutive_successes: int = 0
    avg_score_delta: float = 0.0
    last_used: str | None = None
    tags: list[str] = field(default_factory=list)
    crystallized: bool = False
    disabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    rejected_reasons: list[str] = field(default_factory=list)


class SkillLibrary:
    """CRUD + crystallization for optimization skills."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.skills_path = project_path / ".vortex" / "skills.json"
        self.skills: list[Skill] = []
        self._rejected_patterns: list[str] = []
        self._load()

    def _load(self) -> None:
        """Load skills from disk."""
        if self.skills_path.exists():
            data = json.loads(self.skills_path.read_text())
            self.skills = [Skill(**s) for s in data.get("skills", [])]
            self._rejected_patterns = data.get("rejected_patterns", [])

    def _save(self) -> None:
        """Persist skills to disk."""
        self.skills_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "skills": [asdict(s) for s in self.skills],
            "rejected_patterns": self._rejected_patterns,
        }
        self.skills_path.write_text(json.dumps(data, indent=2))

    # ── CREATE ────────────────────────────────────────────────

    def create_skill(self, name: str, description: str, change_template: str, tags: list[str] | None = None) -> Skill:
        """Create a new skill."""
        skill = Skill(
            id=f"skill_{int(datetime.now().timestamp())}",
            name=name,
            description=description,
            change_template=change_template,
            tags=tags or [],
        )
        self.skills.append(skill)
        self._save()
        return skill

    def record_success(self, skill_id: str, score_delta: float) -> None:
        """Record a successful use of a skill."""
        skill = self.get_skill(skill_id)
        if not skill:
            return
        skill.success_count += 1
        skill.consecutive_successes += 1
        skill.last_used = datetime.now().isoformat()
        # Update running average
        total = skill.success_count + skill.failure_count
        skill.avg_score_delta = ((skill.avg_score_delta * (total - 1)) + score_delta) / total
        # Auto-crystallize after 3 consecutive successes
        if skill.consecutive_successes >= 3 and not skill.crystallized:
            skill.crystallized = True
            logger.info("Skill %s crystallized after %d consecutive successes", skill.name, skill.consecutive_successes)
        self._save()

    def record_failure(self, skill_id: str, reason: str = "") -> None:
        """Record a failed use of a skill."""
        skill = self.get_skill(skill_id)
        if not skill:
            return
        skill.failure_count += 1
        skill.consecutive_successes = 0
        skill.last_used = datetime.now().isoformat()
        if reason and reason not in skill.rejected_reasons:
            skill.rejected_reasons.append(reason)
        if reason and reason not in self._rejected_patterns:
            self._rejected_patterns.append(reason)
        self._save()

    # ── READ ──────────────────────────────────────────────────

    def get_skill(self, skill_id: str) -> Skill | None:
        """Get a skill by ID."""
        return next((s for s in self.skills if s.id == skill_id), None)

    def list_skills(self, crystallized_only: bool = False) -> list[Skill]:
        """List all skills."""
        result = self.skills
        if crystallized_only:
            result = [s for s in result if s.crystallized]
        return [s for s in result if not s.disabled]

    def get_relevant_skills(self, context: str) -> list[Skill]:
        """Get skills relevant to the context."""
        context_lower = context.lower()
        relevant = []
        for skill in self.skills:
            if skill.disabled:
                continue
            # Simple keyword matching
            if (context_lower in skill.name.lower()
                    or context_lower in skill.description.lower()
                    or any(context_lower in tag.lower() for tag in skill.tags)):
                relevant.append(skill)
        # Sort by score
        relevant.sort(key=lambda s: s.avg_score_delta, reverse=True)
        return relevant

    def get_rejected_patterns(self) -> list[str]:
        """Get patterns that have been rejected."""
        return self._rejected_patterns.copy()

    # ── UPDATE ────────────────────────────────────────────────

    def update_skill(self, skill_id: str, **kwargs) -> Skill | None:
        """Update a skill's properties."""
        skill = self.get_skill(skill_id)
        if not skill:
            return None
        for key, value in kwargs.items():
            if hasattr(skill, key):
                setattr(skill, key, value)
        self._save()
        return skill

    def crystallize_skill(self, skill_id: str) -> None:
        """Manually crystallize a skill."""
        skill = self.get_skill(skill_id)
        if skill:
            skill.crystallized = True
            self._save()

    def enable_skill(self, skill_id: str) -> None:
        """Enable a skill."""
        self.update_skill(skill_id, disabled=False)

    def disable_skill(self, skill_id: str) -> None:
        """Disable a skill."""
        self.update_skill(skill_id, disabled=True)

    # ── DELETE ────────────────────────────────────────────────

    def delete_skill(self, skill_id: str) -> None:
        """Delete a skill."""
        self.skills = [s for s in self.skills if s.id != skill_id]
        self._save()

    def prune(self, min_uses: int = 3, min_age_days: int = 30) -> int:
        """Remove old, unused skills. Returns count of pruned skills."""
        cutoff = datetime.now() - timedelta(days=min_age_days)
        before = len(self.skills)
        self.skills = [
            s for s in self.skills
            if s.crystallized
            or s.success_count + s.failure_count >= min_uses
            or (s.created_at and datetime.fromisoformat(s.created_at) > cutoff)
        ]
        pruned = before - len(self.skills)
        if pruned:
            self._save()
            logger.info("Pruned %d skills", pruned)
        return pruned
