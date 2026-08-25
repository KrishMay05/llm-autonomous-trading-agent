"""Tests for the in-process agent session."""

from __future__ import annotations

from decimal import Decimal

from src.config.settings import Settings
from src.orchestration.session import AgentSession


def test_session_run_populates_audit_and_positions():
    settings = Settings(llm_enabled=False, symbol_allowlist=["AAPL"], broker="paper")
    session = AgentSession(settings, initial_capital=Decimal("100000"))
    records = session.run_once()
    assert records
    snap = session.snapshot()
    assert snap["status"]["runs"] == 1
    assert snap["status"]["last_run_at"]
    assert snap["portfolio"]["positions"]
    assert Decimal(snap["portfolio"]["cash"]) < Decimal("100000")


def test_kill_switch_skips_run():
    settings = Settings(llm_enabled=False, symbol_allowlist=["AAPL"], kill_switch=True)
    session = AgentSession(settings)
    assert session.run_once() == []
    assert session.runs == 0
    assert session.blocked_reason == "kill_switch"
