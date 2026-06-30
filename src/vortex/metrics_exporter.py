"""Metrics export for Prometheus or JSON format."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Metric:
    """A single metric value."""

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsExporter:
    """Exports metrics in Prometheus or JSON format."""

    def __init__(self):
        self.metrics: list[Metric] = []

    def record(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a metric."""
        self.metrics.append(Metric(name=name, value=value, labels=labels or {}))

    def to_json(self) -> str:
        """Export metrics as JSON."""
        data = []
        for m in self.metrics:
            data.append({
                "name": m.name,
                "value": m.value,
                "labels": m.labels,
                "timestamp": m.timestamp,
            })
        return json.dumps(data, indent=2)

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        for m in self.metrics:
            label_str = ""
            if m.labels:
                labels = ",".join(f'{k}="{v}"' for k, v in m.labels.items())
                label_str = f"{{{labels}}}"
            lines.append(f"{m.name}{label_str} {m.value} {int(m.timestamp * 1000)}")
        return "\n".join(lines)

    def save(self, path: Path, fmt: str = "json") -> None:
        """Save metrics to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "prometheus":
            path.write_text(self.to_prometheus())
        else:
            path.write_text(self.to_json())

    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
