"""Tests for WAL, sandbox, and audit trail."""

from pathlib import Path

from vortex.audit import AuditTrail
from vortex.sandbox import Sandbox, SandboxResult
from vortex.wal import WAL


def test_wal_log_and_recover(tmp_project: Path):
    """Test WAL logging and recovery."""
    wal = WAL(tmp_project)
    op_id = wal.log_operation("test_op", {"key": "value"})
    pending = wal.recover()
    assert len(pending) == 1
    assert pending[0].operation_type == "test_op"


def test_wal_mark_completed(tmp_project: Path):
    """Test marking operations as completed."""
    wal = WAL(tmp_project)
    op_id = wal.log_operation("test_op")
    wal.mark_completed(op_id)
    pending = wal.recover()
    assert len(pending) == 0


def test_wal_cleanup(tmp_project: Path):
    """Test cleanup removes completed entries."""
    wal = WAL(tmp_project)
    op1 = wal.log_operation("op1")
    op2 = wal.log_operation("op2")
    wal.mark_completed(op1)
    removed = wal.cleanup()
    assert removed == 1
    pending = wal.recover()
    assert len(pending) == 1


def test_sandbox_direct():
    """Test sandbox runs commands directly when Docker unavailable."""
    sandbox = Sandbox()
    result = sandbox.run("echo hello", Path("/tmp"))
    assert result.stdout.strip() == "hello"
    assert result.returncode == 0


def test_sandbox_timeout():
    """Test sandbox timeout handling."""
    sandbox = Sandbox()
    result = sandbox.run("sleep 10", Path("/tmp"), timeout=1)
    assert result.timed_out


def test_audit_log(tmp_project: Path):
    """Test audit trail logging."""
    trail = AuditTrail(tmp_project)
    h1 = trail.log("test_action", "user", {"detail": "test"})
    h2 = trail.log("test_action2", "user", {})
    assert len(h1) == 64  # SHA-256 hash
    assert len(h2) == 64


def test_audit_integrity(tmp_project: Path):
    """Test audit trail integrity verification."""
    trail = AuditTrail(tmp_project)
    trail.log("action1", "user", {})
    trail.log("action2", "user", {})
    assert trail.verify_integrity()


def test_audit_entries(tmp_project: Path):
    """Test getting audit entries."""
    trail = AuditTrail(tmp_project)
    trail.log("a1", "user", {})
    trail.log("a2", "user", {})
    entries = trail.get_entries(1)
    assert len(entries) == 1
