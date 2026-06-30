"""Example plugin: Prometheus metric collector."""

from pathlib import Path


class PrometheusMetric:
    """A metric collector that exports to Prometheus format."""

    def __init__(self):
        self.metrics = {}

    def collect(self, project_path: Path) -> dict:
        """Collect metrics from the project."""
        # Example: count Python files
        py_files = list(project_path.rglob("*.py"))
        return {
            "python_files": len(py_files),
            "total_files": len(list(project_path.rglob("*"))),
        }

    def format_prometheus(self, metrics: dict) -> str:
        """Format metrics for Prometheus."""
        lines = []
        for name, value in metrics.items():
            lines.append(f"vortex_{name} {value}")
        return "\n".join(lines)
