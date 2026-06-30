"""Write-Ahead Log for crash recovery."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class WALEntry:
    """A single WAL entry."""

    operation_id: str
    operation_type: str  # "cycle_start", "metrics_collected", "changes_applied", "cycle_end"
    status: str = "pending"  # "pending", "completed", "failed"
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WAL:
    """Write-Ahead Log for crash recovery.

    Every critical operation is logged BEFORE execution.
    On crash recovery, pending operations are replayed.
    """

    def __init__(self, project_path: Path):
        self.wal_path = project_path / ".vortex" / "wal.jsonl"
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)

    def log_operation(self, operation_type: str, data: dict | None = None) -> str:
        """Log an operation BEFORE executing it. Returns operation_id."""
        op_id = f"op_{int(datetime.now().timestamp() * 1000)}"
        entry = WALEntry(
            operation_id=op_id,
            operation_type=operation_type,
            data=data or {},
        )
        with open(self.wal_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return op_id

    def mark_completed(self, operation_id: str) -> None:
        """Mark an operation as completed."""
        self._update_status(operation_id, "completed")

    def mark_failed(self, operation_id: str, error: str = "") -> None:
        """Mark an operation as failed."""
        self._update_status(operation_id, "failed", {"error": error})

    def recover(self) -> list[WALEntry]:
        """Recover pending operations after a crash."""
        if not self.wal_path.exists():
            return []
        pending = []
        with open(self.wal_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = WALEntry(**json.loads(line))
                if entry.status == "pending":
                    pending.append(entry)
        return pending

    def cleanup(self) -> int:
        """Remove completed entries. Returns count of removed entries."""
        if not self.wal_path.exists():
            return 0
        entries = []
        removed = 0
        with open(self.wal_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry["status"] == "pending":
                    entries.append(json.dumps(entry))
                else:
                    removed += 1
        self.wal_path.write_text("\n".join(entries) + "\n" if entries else "")
        return removed

    def _update_status(self, operation_id: str, status: str, extra: dict | None = None) -> None:
        """Update the status of an operation in the WAL."""
        if not self.wal_path.exists():
            return
        lines = []
        with open(self.wal_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry["operation_id"] == operation_id:
                    entry["status"] = status
                    if extra:
                        entry["data"].update(extra)
                lines.append(json.dumps(entry))
        self.wal_path.write_text("\n".join(lines) + "\n")
