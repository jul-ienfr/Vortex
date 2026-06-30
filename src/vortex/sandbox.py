"""Sandboxed execution for VORTEX."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of a sandboxed execution."""

    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False


class Sandbox:
    """Executes commands in an isolated Docker environment."""

    def __init__(self, image: str = "python:3.12-slim"):
        self.image = image

    def is_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run(self, command: str, project_path: Path, timeout: int = 30) -> SandboxResult:
        """Execute a command in a sandboxed Docker container."""
        if not self.is_docker_available():
            logger.warning("Docker not available, running directly (NOT sandboxed)")
            return self._run_direct(command, project_path, timeout)

        docker_cmd = [
            "docker", "run", "--rm",
            "--network=none",
            "--read-only",
            "--tmpfs", "/tmp:size=10m",
            "--memory=256m",
            "--cpus=1.0",
            "-v", f"{project_path}:/code:ro",
            self.image,
            "sh", "-c", command,
        ]

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr="Command timed out",
                returncode=-1,
                timed_out=True,
            )

    def _run_direct(self, command: str, project_path: Path, timeout: int) -> SandboxResult:
        """Run directly without Docker (fallback)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_path),
            )
            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr="Command timed out",
                returncode=-1,
                timed_out=True,
            )
