"""Immutable audit trail for VORTEX."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class AuditEntry:
    """A single audit trail entry."""

    timestamp: str
    action: str
    actor: str
    details: dict = field(default_factory=dict)
    result: str = ""  # "success", "failure", "reverted"
    prev_hash: str = ""  # hash of previous entry (chain)
    entry_hash: str = ""  # hash of this entry


class AuditTrail:
    """Immutable audit trail with chain hashing."""

    def __init__(self, project_path: Path):
        self.trail_path = project_path / ".vortex" / "audit.jsonl"
        self.trail_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, action: str, actor: str, details: dict, result: str = "success") -> str:
        """Log an action. Returns the entry hash."""
        prev_hash = self._get_last_hash()

        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            actor=actor,
            details=details,
            result=result,
            prev_hash=prev_hash,
        )

        # Compute hash of this entry (without the hash field itself)
        entry_dict = asdict(entry)
        entry_dict.pop("entry_hash", None)
        entry.entry_hash = hashlib.sha256(json.dumps(entry_dict, sort_keys=True).encode()).hexdigest()

        with open(self.trail_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

        return entry.entry_hash

    def verify_integrity(self) -> bool:
        """Verify the chain of hashes is unbroken."""
        if not self.trail_path.exists():
            return True

        prev_hash = None
        with open(self.trail_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if prev_hash and entry.get("prev_hash") != prev_hash:
                    return False
                prev_hash = entry.get("entry_hash")

        return True

    def get_entries(self, n: int | None = None) -> list[dict]:
        """Get the last N audit entries."""
        if not self.trail_path.exists():
            return []
        entries = []
        with open(self.trail_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        if n:
            entries = entries[-n:]
        return entries

    def _get_last_hash(self) -> str:
        """Get the hash of the last entry."""
        if not self.trail_path.exists():
            return ""
        with open(self.trail_path) as f:
            last_line = ""
            for line in f:
                if line.strip():
                    last_line = line.strip()
            if last_line:
                entry = json.loads(last_line)
                return entry.get("entry_hash", "")
        return ""
