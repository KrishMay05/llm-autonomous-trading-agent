"""Audit logger — appends AuditRecord as one JSON line per decision cycle.

Storage layout: ``<log_dir>/YYYYMMDD.jsonl`` (UTC date). One JSON object per line.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.brokers.models import AuditRecord

_DEFAULT_LOG_DIR = Path("logs/audit")


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class AuditLogger:
    """Append-only JSONL audit logger keyed by UTC date.

    Each call to :meth:`log` (or the convenience :meth:`log_decision`) appends a
    single JSON object — the ``AuditRecord`` serialized with ``model_dump`` — to
    ``<log_dir>/<YYYYMMDD>.jsonl``. The directory is created on first use.
    """

    def __init__(self, log_dir: Path = _DEFAULT_LOG_DIR) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    # ── writing ──────────────────────────────────────────────────
    def _path_for(self, dt: datetime) -> Path:
        return self.log_dir / f"{dt.strftime('%Y%m%d')}.jsonl"

    @staticmethod
    def _serialize(record: AuditRecord) -> dict[str, Any]:
        # model_dump(mode="json") renders datetimes/Decimals as ISO/str so the
        # result is json.dumps-safe.
        return record.model_dump(mode="json")

    def log(self, record: AuditRecord) -> None:
        """Append ``record`` as a single JSON line to today's audit file."""
        line = json.dumps(self._serialize(record), default=str, sort_keys=False)
        path = self._path_for(record.timestamp)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def log_decision(
        self,
        symbol: str,
        decision: str,
        strategy_signal: dict | None = None,
        llm_research: dict | None = None,
        risk_gate: dict | None = None,
        action: dict | None = None,
        execution: dict | None = None,
        inputs_digest: str = "",
    ) -> AuditRecord:
        """Build an ``AuditRecord`` from components, log it, and return it."""
        record = AuditRecord(
            timestamp=_utc_now(),
            symbol=symbol,
            decision=decision,
            strategy_signal=strategy_signal,
            llm_research=llm_research,
            risk_gate=risk_gate,
            action=action,
            execution=execution,
            inputs_digest=inputs_digest,
        )
        self.log(record)
        return record

    # ── reading ──────────────────────────────────────────────────
    def _iter_files(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Path]:
        files: list[Path] = []
        for p in sorted(self.log_dir.glob("*.jsonl")):
            try:
                file_date = datetime.strptime(p.stem, "%Y%m%d").date()
            except ValueError:
                continue
            if start_date is not None and file_date < start_date:
                continue
            if end_date is not None and file_date > end_date:
                continue
            files.append(p)
        return files

    @staticmethod
    def _load_file(path: Path) -> list[AuditRecord]:
        records: list[AuditRecord] = []
        with path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {path}:{lineno}: {exc}"
                    ) from exc
                records.append(AuditRecord.model_validate(obj))
        return records

    def _load_all(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AuditRecord]:
        out: list[AuditRecord] = []
        for path in self._iter_files(start_date, end_date):
            out.extend(self._load_file(path))
        return out

    # ── queries ──────────────────────────────────────────────────
    def query_by_symbol(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AuditRecord]:
        """Return records matching ``symbol`` within the optional date window."""
        return [
            r for r in self._load_all(start_date, end_date) if r.symbol == symbol
        ]

    def query_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> list[AuditRecord]:
        """Return all records with timestamps in ``[start_date, end_date]`` (UTC)."""
        records: list[AuditRecord] = []
        for path in self._iter_files(start_date, end_date):
            for rec in self._load_file(path):
                rec_date = rec.timestamp.astimezone(timezone.utc).date()
                if start_date <= rec_date <= end_date:
                    records.append(rec)
        return records

    def query_by_client_order_id(
        self,
        client_order_id: str,
    ) -> list[AuditRecord]:
        """Search all audit files for records whose action/execution dict
        contains ``client_order_id`` (checked in ``action`` and ``execution``).
        """
        matches: list[AuditRecord] = []
        for rec in self._load_all():
            containers = [c for c in (rec.action, rec.execution) if c is not None]
            for c in containers:
                if c.get("client_order_id") == client_order_id:
                    matches.append(rec)
                    break
        return matches
