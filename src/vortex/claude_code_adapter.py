"""Adaptateur pour Claude Code CLI."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProjectAnalysis:
    """Analyse d'un projet par Claude Code."""

    files: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Résultat d'une optimisation par Claude Code."""

    success: bool
    changes_made: list[str] = field(default_factory=list)
    tests_passed: bool = False
    output: str = ""
    error: str = ""


class ClaudeCodeAdapter:
    """Adaptateur pour Claude Code CLI."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.claude_bin = self._find_claude_bin()

    def _find_claude_bin(self) -> str:
        """Trouve le binaire Claude Code."""
        # Chercher sur le PATH
        claude = shutil.which("claude")
        if claude:
            return claude

        # Chercher dans les emplacements communs
        common_paths = [
            Path.home() / ".npm-global" / "bin" / "claude",
            Path("/usr/local/bin/claude"),
            Path("/usr/bin/claude"),
        ]
        for path in common_paths:
            if path.is_file():
                return str(path)

        raise FileNotFoundError("Claude Code non trouvé. Installez-le avec: npm install -g @anthropic-ai/claude-code")

    def is_available(self) -> bool:
        """Vérifie si Claude Code est disponible."""
        try:
            result = subprocess.run(
                [self.claude_bin, "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def analyze_project(self) -> ProjectAnalysis:
        """Demande à Claude d'analyser le projet."""
        prompt = f"""Analyse le projet Python à {self.project_path}.

Liste les fichiers Python, identifie les problèmes potentiels, et suggère des améliorations.

Réponds en JSON:
{{
  "files": ["fichier1.py", "fichier2.py"],
  ["issues": ["problème1", "problème2"],
  "improvements": ["amélioration1", "amélioration2"]
}}"""

        result = self._run_claude(prompt)
        return self._parse_analysis(result)

    def optimize(self, task: str, context: dict) -> OptimizationResult:
        """Demande à Claude d'optimiser le projet."""
        prompt = self._build_optimization_prompt(task, context)
        result = self._run_claude(prompt)
        return self._parse_optimization(result)

    def _build_optimization_prompt(self, task: str, context: dict) -> str:
        """Construit le prompt d'optimisation."""
        constraints = context.get("constraints", [])
        metrics = context.get("current_metrics", {})

        return f"""Tu es un optimiseur de code pour le projet à {self.project_path}.

TÂCHE: {task}

CONTRAINTES:
{chr(10).join(f'- {c}' for c in constraints)}

MÉTRIQUES ACTUELLES:
{json.dumps(metrics, indent=2)}

Actionne les changements nécessaires et lance les tests.
Le code doit être du Python valide. Ne réécris PAS les fichiers entiers."""

    def _run_claude(self, prompt: str) -> str:
        """Exécute Claude Code CLI."""
        try:
            result = subprocess.run(
                [self.claude_bin, "-p", prompt, "--output-format", "json"],
                capture_output=True, text=True, timeout=300,
                cwd=str(self.project_path)
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning("Claude Code timeout")
            return '{"error": "timeout"}'
        except Exception as e:
            logger.error("Claude Code error: %s", e)
            return json.dumps({"error": str(e)})

    def _parse_analysis(self, result: str) -> ProjectAnalysis:
        """Parse la réponse d'analyse."""
        try:
            data = json.loads(result)
            return ProjectAnalysis(
                files=data.get("files", []),
                issues=data.get("issues", []),
                improvements=data.get("improvements", []),
            )
        except (json.JSONDecodeError, KeyError):
            return ProjectAnalysis()

    def _parse_optimization(self, result: str) -> OptimizationResult:
        """Parse la réponse d'optimisation."""
        try:
            data = json.loads(result)
            return OptimizationResult(
                success=data.get("success", False),
                changes_made=data.get("changes_made", []),
                tests_passed=data.get("tests_passed", False),
                output=data.get("output", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return OptimizationResult(success=False, error="Failed to parse response")
