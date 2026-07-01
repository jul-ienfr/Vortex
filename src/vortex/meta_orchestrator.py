"""Meta-Orchestrator — Chef Architecte qui pense stratégiquement."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from vortex.debate import DebateEngine
from vortex.history import CycleHistory, CycleResult
from vortex.manifest import ManifestConfig
from vortex.skill_library import SkillLibrary

logger = logging.getLogger(__name__)


@dataclass
class StrategicDecision:
    """Décision stratégique du Chef Architecte."""

    action: str  # "optimize", "stop", "research", "create_debate_method"
    target: str  # fichier ou composant cible
    rationale: str
    confidence: float  # 0.0 - 1.0
    agent_opinions: dict = field(default_factory=dict)
    debate_results: list = field(default_factory=list)


@dataclass
class SpecialistOpinion:
    """Avis d'un agent spécialiste."""

    role: str
    opinion: str
    priority: float  # 0.0 - 1.0


class MetaOrchestrator:
    """Chef Architecte qui pense stratégiquement et organise des débats."""

    def __init__(self, manifest: ManifestConfig):
        self.manifest = manifest
        self.debate_engine = DebateEngine()
        self.history = CycleHistory(manifest.project_path)
        self.skills = SkillLibrary(manifest.project_path)
        self.project_path = manifest.project_path

    def think(self, context: dict) -> StrategicDecision:
        """Le Chef Architecte réfléchit à ce qu'il faut faire."""
        # 1. Analyse le contexte (son propre avis)
        own_analysis = self._analyze_context(context)

        # 2. Demande l'avis d'agents spécialisés
        agent_opinions = self._consult_specialists(own_analysis)

        # 3. Combine son analyse avec celles des agents
        combined = self._combine_analyses(own_analysis, agent_opinions)

        # 4. Identifie les questions stratégiques
        questions = self._generate_strategic_questions(combined)

        # 5. Organise des débats
        debates = self._organize_debats(questions)

        # 6. Tire les conclusions
        conclusions = self._draw_conclusions(debates)

        # 7. Prend une décision
        decision = self._make_decision(conclusions)

        return decision

    def _analyze_context(self, context: dict) -> dict:
        """Analyse le contexte actuel."""
        return {
            "metrics": context.get("current_metrics", {}),
            "baseline": context.get("baseline_metrics", {}),
            "history": self.history.get_recent(5),
            "skills": [s.name for s in self.skills.list_skills()[:5]],
            "project_files": self._list_project_files(),
        }

    def _list_project_files(self) -> list[str]:
        """Liste les fichiers du projet."""
        files = []
        for f in sorted(self.project_path.rglob("*.py")):
            if "venv" not in str(f) and "__pycache__" not in str(f) and ".vortex" not in str(f):
                files.append(str(f.relative_to(self.project_path)))
        return files[:30]

    def _consult_specialists(self, own_analysis: dict) -> dict:
        """Demande l'avis d'agents spécialisés (1 seul appel LLM)."""
        # Un seul appel LLM pour tous les avis
        prompt = f"""Tu es un expert en Python. Voici le contexte du projet:
{json.dumps(own_analysis, indent=2)[:500]}

Donne 3 améliorations possibles (une pour performance, une pour qualité, une pour sécurité).
Format: {{"performance": "...", "qualite": "...", "securite": "..."}}"""
        try:
            response = self._call_llm(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return {"general": "Amélioration générale du code"}

    def _has_tests(self) -> bool:
        """Vérifie si le projet a des tests."""
        return any(self.project_path.rglob("test_*.py"))

    def _has_api(self) -> bool:
        """Vérifie si le projet a une API."""
        return any(self.project_path.rglob("*api*.py")) or any(self.project_path.rglob("*route*.py"))

    def _has_database(self) -> bool:
        """Vérifie si le projet utilise une BDD."""
        return any(self.project_path.rglob("*.db")) or any(self.project_path.rglob("*database*.py"))

    def _ask_specialist(self, role: str, question: str, context: dict) -> str:
        """Demande l'avis d'un agent spécialiste via LLM."""
        prompt = f"""Tu es un expert en {role} pour un projet Python.

Contexte:
{json.dumps(context, indent=2)}

Question: {question}

Donne ton avis en 2-3 phrases. Sois spécifique et actionnable."""
        return self._call_llm(prompt)

    def _combine_analyses(self, own: dict, agents: dict) -> dict:
        """Combine l'analyse du Chef avec celles des agents."""
        combined = own.copy()
        combined["agent_opinions"] = agents
        all_improvements = own.get("improvements", [])
        for role, opinion in agents.items():
            all_improvements.append({"source": role, "improvement": opinion})
        combined["all_improvements"] = all_improvements
        return combined

    def _generate_strategic_questions(self, analysis: dict) -> list[str]:
        """Génère des questions stratégiques."""
        questions = []

        # Questions sur les métriques
        metrics = analysis.get("metrics", {})
        if metrics.get("lint_issues", 0) > 100:
            questions.append("Faut-il améliorer le code quality ?")
        if metrics.get("test_count", 0) < 100:
            questions.append("Faut-il ajouter des tests ?")

        # Questions sur les échecs précédents (REFLEXION)
        failure_reflections = analysis.get("failure_reflections", [])
        if failure_reflections:
            last_failure = failure_reflections[-1]
            questions.append(
                f"Un cycle a échoué: {last_failure[:200]}. "
                f"Comment éviter cet échec ?"
            )

        # Questions sur l'historique
        history = analysis.get("history", [])
        if history:
            last = history[-1]
            if last.get("decision") == "reverted":
                questions.append("Pourquoi le dernier cycle a-t-il échoué ?")

        # Questions sur les skills
        if not analysis.get("skills"):
            questions.append("Faut-il créer de nouvelles skills ?")

        # Questions sur les améliorations des agents
        for role, opinion in analysis.get("agent_opinions", {}).items():
            if opinion:
                questions.append(f"Amélioration {role}: {opinion[:100]}")

        return questions[:5]  # Limiter à 5 questions

    def _organize_debats(self, questions: list[str]) -> list:
        """Organise des débats pour chaque question."""
        from vortex.debate import DebateEngine

        debates = []
        for question in questions:
            method = self._choose_debate_method(question)
            # Créer un nouvel engine avec la méthode choisie
            engine = DebateEngine(method, models=['mimo-v2.5', 'deepseek-v4-flash'])
            team = engine.create_team(3)
            result = engine.debate(question, team)
            debates.append(result)
        return debates

    def _choose_debate_method(self, question: str) -> str:
        """Choisit la méthode de débat appropriée."""
        q = question.lower()
        if "risque" in q or "échec" in q:
            return "premortem"
        elif "gain" in q or "bénéfice" in q:
            return "tradeoff"
        elif "priorité" in q:
            return "oxford"
        elif "idées" in q or "innovation" in q:
            return "brainstorm"
        elif "pourquoi" in q:
            return "socratic"
        else:
            return "standard"

    def _draw_conclusions(self, debates: list) -> list[dict]:
        """Tire les conclusions des débats."""
        conclusions = []
        for debate in debates:
            # Analyser les positions des agents
            positions = []
            for round_data in debate.rounds:
                if "positions" in round_data:
                    positions.extend(round_data["positions"].values())
                elif "argument" in round_data:
                    positions.append(round_data["argument"])

            # Identifier le consensus
            consensus = self._find_consensus(positions)
            conclusions.append({
                "topic": debate.topic,
                "consensus": consensus,
                "num_positions": len(positions),
            })

        return conclusions

    def _find_consensus(self, positions: list[str]) -> str:
        """Identifie le consensus parmi les positions."""
        if not positions:
            return "Aucune position"
        # Retourne la position la plus fréquente (simplifié)
        return positions[0] if positions else "Aucune position"

    def _make_decision(self, conclusions: list[dict]) -> StrategicDecision:
        """Prend une décision basée sur les conclusions."""
        # Évaluer chaque conclusion
        if not conclusions:
            return StrategicDecision(
                action="stop",
                target="",
                rationale="Aucune amélioration identifiée",
                confidence=0.0,
            )

        # Prendre la décision basée sur la première conclusion
        best = conclusions[0]
        return StrategicDecision(
            action="optimize",
            target=best.get("topic", ""),
            rationale=best.get("consensus", ""),
            confidence=0.7,
            debate_results=conclusions,
        )

    def _call_llm(self, prompt: str) -> str:
        """Appelle le LLM pour obtenir une réponse."""
        try:
            import litellm
            import os

            model = self.manifest.optimizer.model or "mimo-v2.5"
            if self.manifest.optimizer.model_proxy and not model.startswith("openai/"):
                model = f"openai/{model}"

            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500,
            }

            if self.manifest.optimizer.model_proxy:
                kwargs["api_base"] = self.manifest.optimizer.model_proxy
                if not os.environ.get("OPENAI_API_KEY"):
                    kwargs["api_key"] = "not-needed"

            response = litellm.completion(**kwargs)
            msg = response.choices[0].message
            content = msg.content or ""
            if not content and hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                content = msg.reasoning_content
            return content or "No response"
        except Exception as e:
            logger.warning("LLM call failed: %s", e)
            return f"[Error: {e}]"

    def create_debate_method(self, name: str, description: str, steps: list[str]) -> None:
        """Crée une nouvelle méthode de débat."""
        self.debate_engine.add_method(name, description, steps)
        logger.info("Created new debate method: %s", name)
