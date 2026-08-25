"""Tests for src.audit.retention — old-file pruning."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.audit.retention import RetentionPolicy, cleanup


def _write_audit_file(log_dir: Path, days_old: int, content: str = "{}\n") -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    target = datetime.now(tz=timezone.utc).date() - timedelta(days=days_old)
    path = log_dir / f"{target.strftime('%Y%m%d')}.jsonl"
    path.write_text(content, encoding="utf-8")
    return path


def test_cleanup_deletes_old_files(tmp_path: Path) -> None:
    log_dir = tmp_path / "audit"
    old = _write_audit_file(log_dir, days_old=400)
    _write_audit_file(log_dir, days_old=10)

    deleted = cleanup(log_dir, max_days=365)
    assert deleted == 1
    assert not old.exists()
    # recent file remains
    assert len(list(log_dir.glob("*.jsonl"))) == 1


def test_cleanup_keeps_recent(tmp_path: Path) -> None:
    log_dir = tmp_path / "audit"
    _write_audit_file(log_dir, days_old=5)
    _write_audit_file(log_dir, days_old=30)

    deleted = cleanup(log_dir, max_days=365)
    assert deleted == 0
    assert len(list(log_dir.glob("*.jsonl"))) == 2


def test_cleanup_missing_dir(tmp_path: Path) -> None:
    assert cleanup(tmp_path / "does-not-exist", max_days=365) == 0


def test_retention_policy_apply(tmp_path: Path) -> None:
    log_dir = tmp_path / "audit"
    old = _write_audit_file(log_dir, days_old=500)
    _write_audit_file(log_dir, days_old=1)

    policy = RetentionPolicy(max_days=365)
    assert policy.apply(log_dir) == 1
    assert not old.exists()


def test_retention_policy_zero_days(tmp_path: Path) -> None:
    log_dir = tmp_path / "audit"
    _write_audit_file(log_dir, days_old=1)
    _write_audit_file(log_dir, days_old=10)

    policy = RetentionPolicy(max_days=0)
    assert policy.apply(log_dir) == 2


def test_retention_policy_ignores_non_audit_files(tmp_path: Path) -> None:
    log_dir = tmp_path / "audit"
    log_dir.mkdir(parents=True)
    (log_dir / "notaudit.txt").write_text("ignore me", encoding="utf-8")
    (log_dir / "README.md").write_text("# hi", encoding="utf-8")
    _write_audit_file(log_dir, days_old=400)

    assert cleanup(log_dir, max_days=365) == 1
    assert (log_dir / "notaudit.txt").exists()
    assert (log_dir / "README.md").exists()
