"""Retention policy — prune old audit JSONL files."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path


class RetentionPolicy:
    """Declarative retention policy for the audit log directory.

    ``max_days`` is the number of days of audit files to retain. Files older
    than ``max_days`` (by filename date) are eligible for deletion via
    :meth:`apply`.
    """

    def __init__(self, max_days: int = 365) -> None:
        if max_days < 0:
            raise ValueError("max_days must be non-negative")
        self.max_days = max_days

    def apply(self, log_dir: Path) -> int:
        """Delete audit files older than ``max_days``; return count deleted."""
        return cleanup(log_dir, self.max_days)

    @property
    def cutoff_date(self) -> date:
        return datetime.now(tz=timezone.utc).date() - timedelta(days=self.max_days)


def cleanup(log_dir: Path, max_days: int = 365) -> int:
    """Delete ``<YYYYMMDD>.jsonl`` files in ``log_dir`` older than ``max_days``.

    Returns the count of files deleted.
    """
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return 0

    cutoff = datetime.now(tz=timezone.utc).date() - timedelta(days=max_days)
    deleted = 0
    for path in log_dir.glob("*.jsonl"):
        try:
            file_date = datetime.strptime(path.stem, "%Y%m%d").date()
        except ValueError:
            continue
        if file_date < cutoff:
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted
