"""Tests for src.orchestration.loop."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.brokers.models import (
    Account,
    AuditRecord,
    Bar,
    FeatureVector,
    Order,
    OrderStatus,
    Position,
    Quote,
    RiskDecision,
    RiskStatus,
    SessionState,
    SignalSide,
    StrategySignal,
    TradeIntent,
    TradeProposal,
)
from src.config.settings import Settings
from src.orchestration.loop import TradingLoop
from src.portfolio.state import PortfolioState


@pytest.fixture
def utc_now():
    return datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def account():
    return Account(
        equity=Decimal("100000"),
        cash=Decimal("100000"),
        buying_power=Decimal("100000"),
    )


@pytest.fixture
def settings():
    return Settings(llm_enabled=False, symbol_allowlist=["AAPL"])


@pytest.fixture
def quote(utc_now):
    return Quote(
        symbol="AAPL",
        bid=Decimal("99.99"),
        ask=Decimal("100.01"),
        last=Decimal("100"),
        ts=utc_now,
        received_at=utc_now,
    )


@pytest.fixture
def bars(utc_now):
    return {
        "AAPL": [
            Bar(
                symbol="AAPL",
                timeframe="1d",
                ts_open=utc_now,
                ts_close=utc_now,
                open=Decimal("99"),
                high=Decimal("101"),
                low=Decimal("98"),
                close=Decimal("100"),
                volume=Decimal("1000000"),
            )
        ]
    }


def _make_mock_broker(account):
    broker = MagicMock()
    broker.get_account.return_value = account
    broker.list_positions.return_value = []
    order = Order(
        broker_order_id="test-1",
        client_order_id="test-cid",
        symbol="AAPL",
        side="buy",
        qty=Decimal("10"),
        filled_qty=Decimal("10"),
        avg_fill_price=Decimal("100"),
        status=OrderStatus.FILLED,
        submitted_at=datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
    )
    broker.submit_order.return_value = order
    return broker


def _make_approve_gate():
    gate = MagicMock()
    gate.evaluate.return_value = RiskDecision(
        status=RiskStatus.APPROVE,
        approved_qty=Decimal("10"),
        reasons=[],
        checks_passed=["test"],
        checks_failed=[],
    )
    return gate


def _make_reject_gate():
    gate = MagicMock()
    gate.evaluate.return_value = RiskDecision(
        status=RiskStatus.REJECT,
        approved_qty=Decimal("0"),
        reasons=["KILL_SWITCH"],
        checks_passed=[],
        checks_failed=["KILL_SWITCH"],
    )
    return gate


class _BuyStrategy:
    id = "buy_stub_v1"

    def evaluate(self, features: FeatureVector, context: Any) -> StrategySignal:
        return StrategySignal(
            strategy_id=self.id,
            symbol=features.symbol,
            side=SignalSide.BUY,
            strength=0.8,
            horizon="swing",
            rationale="test buy",
            as_of=features.as_of,
            features_used=["close"],
        )


class _HoldStrategy:
    id = "hold_stub_v1"

    def evaluate(self, features: FeatureVector, context: Any) -> StrategySignal:
        return StrategySignal(
            strategy_id=self.id,
            symbol=features.symbol,
            side=SignalSide.HOLD,
            strength=0.0,
            horizon="swing",
            rationale="hold",
            as_of=features.as_of,
            features_used=["close"],
        )


def _feature_builder(symbol, bars, quote, news) -> FeatureVector:
    return FeatureVector(
        symbol=symbol,
        as_of=datetime.now(timezone.utc),
        values={"close": 100.0},
        meta={},
    )


class TestLoopWithMockedBroker:
    def test_audit_records_produced(
        self, settings, account, quote, bars, utc_now
    ):
        broker = _make_mock_broker(account)
        gate = _make_approve_gate()
        audit_records: list[AuditRecord] = []

        loop = TradingLoop(
            settings=settings,
            broker=broker,
            risk_gate=gate,
            strategy_registry={"buy_stub_v1": _BuyStrategy()},
            feature_builder=_feature_builder,
            audit_logger=lambda r: audit_records.append(r),
            portfolio_state=PortfolioState(
                cash=account.cash,
                session_start_equity=account.equity,
            ),
        )
        records = loop.run_once(quotes={"AAPL": quote}, bars=bars, news=[])
        assert len(records) > 0
        # At least one BUY or SELL record (not just reject)
        decisions = [r.decision for r in records]
        assert "BUY" in decisions


class TestLoopRejectAudited:
    def test_reject_produces_reject_audit(
        self, settings, account, quote, bars
    ):
        broker = _make_mock_broker(account)
        gate = _make_reject_gate()
        audit_records: list[AuditRecord] = []

        loop = TradingLoop(
            settings=settings,
            broker=broker,
            risk_gate=gate,
            strategy_registry={"buy_stub_v1": _BuyStrategy()},
            feature_builder=_feature_builder,
            audit_logger=lambda r: audit_records.append(r),
            portfolio_state=PortfolioState(
                cash=account.cash,
                session_start_equity=account.equity,
            ),
        )
        records = loop.run_once(quotes={"AAPL": quote}, bars=bars, news=[])
        assert any(r.decision == "REJECT" for r in records)
        # Broker.submit should NOT be called on reject
        broker.submit_order.assert_not_called()


class TestLoopApproveSubmits:
    def test_broker_submit_called_on_approval(
        self, settings, account, quote, bars
    ):
        broker = _make_mock_broker(account)
        gate = _make_approve_gate()

        loop = TradingLoop(
            settings=settings,
            broker=broker,
            risk_gate=gate,
            strategy_registry={"buy_stub_v1": _BuyStrategy()},
            feature_builder=_feature_builder,
            audit_logger=lambda r: None,
            portfolio_state=PortfolioState(
                cash=account.cash,
                session_start_equity=account.equity,
            ),
        )
        loop.run_once(quotes={"AAPL": quote}, bars=bars, news=[])
        broker.submit_order.assert_called_once()
        submitted_intent = broker.submit_order.call_args[0][0]
        assert isinstance(submitted_intent, TradeIntent)
        assert submitted_intent.symbol == "AAPL"
        assert submitted_intent.side == "buy"


class TestLoopDisabledLLM:
    def test_loop_works_with_llm_disabled(
        self, settings, account, quote, bars
    ):
        broker = _make_mock_broker(account)
        gate = _make_approve_gate()

        loop = TradingLoop(
            settings=settings,
            broker=broker,
            risk_gate=gate,
            strategy_registry={"buy_stub_v1": _BuyStrategy()},
            feature_builder=_feature_builder,
            audit_logger=lambda r: None,
            portfolio_state=PortfolioState(
                cash=account.cash,
                session_start_equity=account.equity,
            ),
            llm_synthesizer=None,
        )
        records = loop.run_once(quotes={"AAPL": quote}, bars=bars, news=[])
        assert len(records) > 0
        # Should not crash; LLM not invoked

    def test_loop_with_hold_strategy_no_proposals(
        self, settings, account, quote, bars
    ):
        broker = _make_mock_broker(account)
        gate = _make_approve_gate()

        loop = TradingLoop(
            settings=settings,
            broker=broker,
            risk_gate=gate,
            strategy_registry={"hold_stub_v1": _HoldStrategy()},
            feature_builder=_feature_builder,
            audit_logger=lambda r: None,
            portfolio_state=PortfolioState(
                cash=account.cash,
                session_start_equity=account.equity,
            ),
        )
        records = loop.run_once(quotes={"AAPL": quote}, bars=bars, news=[])
        # HOLD signal → no proposals → no audit records for trades
        # (but loop still runs successfully)
        assert len(records) == 0
        broker.submit_order.assert_not_called()
