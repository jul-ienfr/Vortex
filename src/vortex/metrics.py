"""Metrics collection and baseline management for VORTEX."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from vortex.manifest import ManifestConfig, MetricDef

logger = logging.getLogger(__name__)


class MetricsCollectionError(Exception):
    """Raised when a metric command fails."""


class MetricsCollector:
    """Collects metrics by running shell commands defined in the manifest."""

    def __init__(self, manifest: ManifestConfig):
        self.manifest = manifest

    def collect(self) -> dict[str, float | None]:
        """Run all metric source commands and return {metric_name: value}."""
        results: dict[str, float | None] = {}
        for metric in self.manifest.metrics:
            try:
                value = self._run_metric(metric)
                results[metric.name] = value
                logger.info("Metric %s = %s", metric.name, value)
            except Exception as e:
                logger.warning("Failed to collect metric %s: %s", metric.name, e)
                results[metric.name] = None
        return results

    def _run_metric(self, metric: MetricDef) -> float | None:
        """Run a single metric command and parse the output."""
        try:
            result = subprocess.run(
                metric.source,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.manifest.project_path),
            )
            if result.returncode != 0:
                raise MetricsCollectionError(
                    f"Command failed (exit {result.returncode}): {result.stderr}"
                )
            return self._parse_output(result.stdout.strip())
        except subprocess.TimeoutExpired:
            raise MetricsCollectionError(f"Command timed out: {metric.source}")

    def _parse_output(self, stdout: str) -> float | None:
        """Parse metric output (JSON or bare number)."""
        if not stdout:
            return None
        # Try JSON first
        try:
            data = json.loads(stdout)
            if isinstance(data, dict):
                # Look for 'value' key
                if "value" in data:
                    return float(data["value"])
                # If it's a simple dict, return None (ambiguous)
                return None
            if isinstance(data, (int, float)):
                return float(data)
        except (json.JSONDecodeError, ValueError):
            pass
        # Try bare number
        try:
            return float(stdout)
        except ValueError:
            return None


class BaselineManager:
    """Establishes and manages baselines for comparison."""

    def __init__(self, manifest: ManifestConfig):
        self.manifest = manifest
        self.baseline_path = manifest.project_path / ".optimizer_baseline.json"

    def establish_baseline(self, collector: MetricsCollector) -> dict[str, float]:
        """Collect metrics N times (baseline_samples), average, and persist."""
        all_samples: dict[str, list[float]] = {m.name: [] for m in self.manifest.metrics}

        # Collect samples
        for sample_idx in range(max(m.baseline_samples for m in self.manifest.metrics)):
            results = collector.collect()
            for name, value in results.items():
                if value is not None:
                    all_samples[name].append(value)

        # Average
        baseline: dict[str, float] = {}
        for name, values in all_samples.items():
            if values:
                baseline[name] = sum(values) / len(values)
            else:
                baseline[name] = 0.0

        self.save_baseline(baseline)
        logger.info("Baseline established: %s", baseline)
        return baseline

    def load_baseline(self) -> dict[str, float] | None:
        """Load previously persisted baseline."""
        if not self.baseline_path.exists():
            return None
        return json.loads(self.baseline_path.read_text())

    def save_baseline(self, metrics: dict[str, float]) -> None:
        """Persist baseline to disk."""
        self.baseline_path.write_text(json.dumps(metrics, indent=2))

    def score(self, current: dict[str, float | None], baseline: dict[str, float]) -> tuple[float, dict[str, float]]:
        """Compute weighted delta score. Positive = improvement.

        Returns:
            (total_score, per_metric_deltas)
        """
        deltas: dict[str, float] = {}
        for m in self.manifest.metrics:
            if m.name not in current or m.name not in baseline:
                continue
            c = current[m.name]
            b = baseline[m.name]
            if c is None:
                continue
            if b == 0:
                delta = 0.0 if c == 0 else (1.0 if m.direction == "up" else -1.0)
            else:
                delta = (c - b) / abs(b)
            # Apply direction
            if m.direction == "down":
                delta = -delta
            # Apply minimum improvement threshold
            if abs(delta) < m.min_improvement_pct / 100:
                delta = 0.0
            deltas[m.name] = delta * m.weight
        return sum(deltas.values()), deltas
