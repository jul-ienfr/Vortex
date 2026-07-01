"""Fabrique LLM — crée le bon client selon le manifeste."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from vortex.manifest import ManifestConfig

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Interface commune pour tous les clients LLM."""

    @abstractmethod
    def complete(self, prompt: str, model: str = None, **kwargs) -> str:
        """Envoie un prompt et retourne la réponse."""
        raise NotImplementedError


class ClaudeCodeClient(LLMClient):
    """Client pour Claude Code CLI (PAR DÉFAUT)."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.claude_bin = self._find_claude_bin()

    def _find_claude_bin(self) -> str:
        """Trouve le binaire Claude Code."""
        claude = shutil.which("claude")
        if claude:
            return claude

        common_paths = [
            Path.home() / ".npm-global" / "bin" / "claude",
            Path("/usr/local/bin/claude"),
            Path("/usr/bin/claude"),
        ]
        for path in common_paths:
            if path.is_file():
                return str(path)

        raise FileNotFoundError("Claude Code non trouvé. Installez-le avec: npm install -g @anthropic-ai/claude-code")

    def complete(self, prompt: str, **kwargs) -> str:
        """Exécute Claude Code CLI."""
        try:
            result = subprocess.run(
                [self.claude_bin, "-p", prompt, "--output-format", "json"],
                capture_output=True, text=True, timeout=300,
                cwd=str(self.project_path)
            )
            if result.returncode != 0:
                logger.warning("Claude Code returned non-zero: %s", result.stderr[:200])
            return result.stdout
        except FileNotFoundError:
            logger.error("Claude Code non trouvé")
            return ""
        except subprocess.TimeoutExpired:
            logger.warning("Claude Code timeout")
            return ""


class CodexClient(LLMClient):
    """Client pour Codex CLI."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.codex_bin = self._find_codex_bin()

    def _find_codex_bin(self) -> str:
        """Trouve le binaire Codex."""
        codex = shutil.which("codex")
        if codex:
            return codex

        common_paths = [
            Path.home() / ".npm-global" / "bin" / "codex",
            Path("/usr/local/bin/codex"),
        ]
        for path in common_paths:
            if path.is_file():
                return str(path)

        raise FileNotFoundError("Codex non trouvé. Installez-le avec: npm install -g @openai/codex")

    def complete(self, prompt: str, **kwargs) -> str:
        """Exécute Codex CLI."""
        try:
            result = subprocess.run(
                [self.codex_bin, "exec", prompt, "--json", "--sandbox", "workspace-write"],
                capture_output=True, text=True, timeout=300,
                cwd=str(self.project_path)
            )
            return result.stdout
        except FileNotFoundError:
            logger.error("Codex non trouvé")
            return ""
        except subprocess.TimeoutExpired:
            logger.warning("Codex timeout")
            return ""


class HermesClient(LLMClient):
    """Client pour Hermès via litellm."""

    def __init__(self, proxy: str = None):
        self.proxy = proxy

    def complete(self, prompt: str, **kwargs) -> str:
        """Appelle Hermès via litellm."""
        try:
            import litellm
            response = litellm.completion(
                model="hermes",
                messages=[{"role": "user", "content": prompt}],
                api_base=self.proxy or "http://localhost:8080/v1",
                temperature=0.7,
                max_tokens=4096,
            )
            msg = response.choices[0].message
            content = msg.content or ""
            if not content and hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                content = msg.reasoning_content
            return content
        except Exception as e:
            logger.error("Hermes error: %s", e)
            return ""


class LitellmClient(LLMClient):
    """Client pour litellm (fallback)."""

    def __init__(self, model: str = "mimo-v2.5", proxy: str = None):
        self.model = model
        self.proxy = proxy

    def complete(self, prompt: str, **kwargs) -> str:
        """Appelle litellm."""
        try:
            import litellm

            model = self.model
            if self.proxy and not model.startswith("openai/"):
                model = f"openai/{model}"

            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                api_base=self.proxy,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
            )

            msg = response.choices[0].message
            content = msg.content or ""
            if not content and hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                content = msg.reasoning_content
            if not content:
                fields = getattr(msg, 'provider_specific_fields', {})
                details = fields.get('reasoning_details', [])
                if details:
                    content = details[0].get('text', '')
            return content
        except Exception as e:
            logger.error("Litellm error: %s", e)
            return ""


def create_client(manifest: ManifestConfig) -> LLMClient:
    """Crée le bon client LLM selon le manifeste.

    Par défaut: Claude Code CLI.
    """
    cli = manifest.optimizer.cli

    if cli == "claude":
        return ClaudeCodeClient(manifest.project_path)
    elif cli == "codex":
        return CodexClient(manifest.project_path)
    elif cli == "hermes":
        return HermesClient(proxy=manifest.optimizer.model_proxy)
    elif cli == "litellm":
        return LitellmClient(
            model=manifest.optimizer.model or "mimo-v2.5",
            proxy=manifest.optimizer.model_proxy
        )
    else:
        # Défaut: Claude Code
        return ClaudeCodeClient(manifest.project_path)
