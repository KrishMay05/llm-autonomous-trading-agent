"""Tests for src.audit.logger.AuditLogger — JSONL writer + query helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.audit.logger import AuditLogger
from src.brokers.models import AuditRecord


# ── helpers ──────────────────────────────────────────────────────
def _make_record(
    *,
    symbol: str = "AAPL",
    decision: str = "BUY",
    strategy_signal: dict | None = None,
    llm_research: dict | None = None,
    risk_gate: dict | None = None,
    action: dict | None = None,
    execution: dict | None = None,
    inputs_digest: str = "",
    ts: datetime | None = None,
) -> AuditRecord:
    return AuditRecord(
        timestamp=ts or datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
        symbol=symbol,
        decision=decision,
        strategy_signal=strategy_signal,
        llm_research=llm_research,
        risk_gate=risk_gate,
        action=action,
        execution=execution,
        inputs_digest=inputs_digest,
    )


# ── fixtures ─────────────────────────────────────────────────────
@pytest.fixture
def logger(tmp_path: Path) -> AuditLogger:
    return AuditLogger(log_dir=tmp_path / "audit")


# ── tests ────────────────────────────────────────────────────────
def test_log_creates_file(logger: AuditLogger) -> None:
    rec = _make_record(symbol="AAPL", decision="BUY")
    logger.log(rec)

    files = list(logger.log_dir.glob("*.jsonl"))
    assert len(files) == 1
    assert files[0].name == "20260115.jsonl"

    lines = files[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["symbol"] == "AAPL"
    assert obj["decision"] == "BUY"
    # timestamp is ISO-8601 and carries UTC (Z or +00:00)
    ts = obj["timestamp"]
    assert ts.endswith("Z") or ts.endswith("+00:00"), ts


def test_log_roundtrip(logger: AuditLogger) -> None:
    rec = _make_record(
        symbol="MSFT",
        decision="SELL",
        strategy_signal={"side": "SELL", "strength": 0.8},
        risk_gate={"status": "APPROVE"},
        inputs_digest="abc123",
    )
    logger.log(rec)

    found = logger.query_by_symbol("MSFT")
    assert len(found) == 1
    r = found[0]
    assert r.symbol == "MSFT"
    assert r.decision == "SELL"
    assert r.strategy_signal == {"side": "SELL", "strength": 0.8}
    assert r.risk_gate == {"status": "APPROVE"}
    assert r.inputs_digest == "abc123"


def test_reject_path_writes_audit(logger: AuditLogger) -> None:
    rec = logger.log_decision(
        symbol="TSLA",
        decision="REJECT",
        risk_gate={"status": "REJECT", "reasons": ["drawdown_limit"]},
    )
    assert rec.decision == "REJECT"
    assert rec.risk_gate == {"status": "REJECT", "reasons": ["drawdown_limit"]}

    found = logger.query_by_symbol("TSLA")
    assert len(found) == 1
    assert found[0].decision == "REJECT"


def test_query_by_symbol(logger: AuditLogger) -> None:
    logger.log(_make_record(symbol="AAPL", decision="BUY"))
    logger.log(_make_record(symbol="MSFT", decision="SELL"))
    logger.log(_make_record(symbol="AAPL", decision="HOLD"))

    aapl = logger.query_by_symbol("AAPL")
    assert len(aapl) == 2
    assert all(r.symbol == "AAPL" for r in aapl)

    msft = logger.query_by_symbol("MSFT")
    assert len(msft) == 1
    assert msft[0].symbol == "MSFT"

    assert logger.query_by_symbol("NVDA") == []


def test_query_by_date_range(logger: AuditLogger) -> None:
    logger.log(
        _make_record(
            symbol="AAPL",
            ts=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        )
    )
    logger.log(
        _make_record(
            symbol="AAPL",
            ts=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
    )
    logger.log(
        _make_record(
            symbol="AAPL",
            ts=datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc),
        )
    )

    from datetime import date

    mid = logger.query_by_date_range(date(2026, 1, 12), date(2026, 1, 18))
    assert len(mid) == 1
    assert mid[0].timestamp.day == 15

    all_jan = logger.query_by_date_range(date(2026, 1, 1), date(2026, 1, 31))
    assert len(all_jan) == 3


def test_query_by_client_order_id(logger: AuditLogger) -> None:
    logger.log(
        _make_record(
            symbol="AAPL",
            action={"client_order_id": "ord-001", "side": "buy"},
            execution={"client_order_id": "ord-001", "status": "filled"},
        )
    )
    logger.log(
        _make_record(
            symbol="MSFT",
            action={"client_order_id": "ord-002", "side": "sell"},
        )
    )

    found = logger.query_by_client_order_id("ord-001")
    assert len(found) == 1
    assert found[0].symbol == "AAPL"

    found2 = logger.query_by_client_order_id("ord-002")
    assert len(found2) == 1
    assert found2[0].symbol == "MSFT"

    assert logger.query_by_client_order_id("missing") == []


def test_multiple_records_same_day(logger: AuditLogger) -> None:
    for i in range(5):
        logger.log(
            _make_record(
                symbol="AAPL",
                decision="BUY" if i % 2 == 0 else "HOLD",
                ts=datetime(2026, 1, 15, 9 + i, 0, tzinfo=timezone.utc),
            )
        )

    files = list(logger.log_dir.glob("*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5

    records = logger.query_by_symbol("AAPL")
    assert len(records) == 5
