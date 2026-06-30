"""Templates de prompts pour VORTEX."""

from __future__ import annotations

import json


STRATEGIC_ANALYSIS_PROMPT = """Tu es le Chef Architecte du projet VORTEX.

CONTEXTE:
- Projet: {project_path}
- Métriques actuelles: {current_metrics}
- Métriques baseline: {baseline_metrics}
- Derniers cycles: {recent_history}
- Skills disponibles: {available_skills}
- Fichiers du projet: {project_files}

ANALYSE:
1. Qu'est-ce qui fonctionne bien ?
2. Qu'est-ce qui pourrait être amélioré ?
3. Quels sont les risques ?
4. Quels sont les gains potentiels ?

Réponds en JSON: {{"analysis": "...", "improvements": ["improvement1", "improvement2"], "risks": ["risk1", "risk2"]}}"""


SPECIALIST_PROMPT = """Tu es un expert en {role} pour un projet Python.

Contexte:
{context}

Question: {question}

Donne ton avis en 2-3 phrases. Sois spécifique et actionnable."""


DEBATE_PROMPT = """Tu es un participant à un débat sur le projet VORTEX.

Sujet: {topic}
Type de débat: {debate_method}
Ton rôle: {agent_role}

Contexte:
{context}

Donne ta position en 2-3 phrases. Sois spécifique et argumenté."""


EXECUTION_PROMPT = """Tu es un optimiseur de code pour le projet à {project_path}.

TÂCHE: {task}

CONTRAINTES:
{constraints}

MÉTRIQUES ACTUELLES:
{current_metrics}

Actionne les changements nécessaires et lance les tests.
Le code doit être du Python valide. Ne réécris PAS les fichiers entiers."""


STRATEGIC_DECISION_PROMPT = """Tu es le Chef Architecte. Prends une décision basée sur ces conclusions:

{conclusions}

Réponds en JSON: {{"action": "optimize|stop|research", "target": "...", "rationale": "...", "confidence": 0.0-1.0}}"""


REVIEW_PROMPT = """Tu es un reviewer de code. Voici un changement proposé:

Fichier: {file_path}
Changement: {change_description}
Code actuel:
```python
{current_code}
```

Évalue:
1. Le changement est-il correct ?
2. Est-ce qu'il améliore le code ?
3. Est-ce qu'il pourrait casser quelque chose ?

Réponds JSON: {{"approved": true/false, "reason": "...", "confidence": 0.0-1.0}}"""


def build_strategic_analysis_prompt(context: dict) -> str:
    """Construit le prompt d'analyse stratégique."""
    return STRATEGIC_ANALYSIS_PROMPT.format(
        project_path=context.get("project_path", ""),
        current_metrics=json.dumps(context.get("current_metrics", {}), indent=2),
        baseline_metrics=json.dumps(context.get("baseline_metrics", {}), indent=2),
        recent_history=json.dumps(context.get("recent_history", []), indent=2),
        available_skills=json.dumps(context.get("available_skills", []), indent=2),
        project_files=json.dumps(context.get("project_files", []), indent=2),
    )


def build_specialist_prompt(role: str, question: str, context: dict) -> str:
    """Construit le prompt pour un agent spécialiste."""
    return SPECIALIST_PROMPT.format(
        role=role,
        context=json.dumps(context, indent=2),
        question=question,
    )


def build_execution_prompt(task: str, context: dict) -> str:
    """Construit le prompt d'exécution."""
    return EXECUTION_PROMPT.format(
        project_path=context.get("project_path", ""),
        task=task,
        constraints="\n".join(f"- {c}" for c in context.get("constraints", [])),
        current_metrics=json.dumps(context.get("current_metrics", {}), indent=2),
    )


def build_review_prompt(file_path: str, change_description: str, current_code: str) -> str:
    """Construit le prompt de review."""
    return REVIEW_PROMPT.format(
        file_path=file_path,
        change_description=change_description,
        current_code=current_code[:2000],  # Limiter la taille
    )
