"""Tests for src.orchestration.allocator."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.brokers.models import (
    Account,
    Position,
    ResearchNote,
    SignalSide,
    StrategySignal,
    TradeProposal,
)
from src.config.settings import Settings
from src.orchestration.allocator import Allocator


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
    return Settings()


def _buy_signal(symbol: str, strength: float, utc_now) -> StrategySignal:
    return StrategySignal(
        strategy_id="test_v1",
        symbol=symbol,
        side=SignalSide.BUY,
        strength=strength,
        horizon="swing",
        rationale="test",
        as_of=utc_now,
        features_used=["close"],
    )


def _sell_signal(symbol: str, strength: float, utc_now) -> StrategySignal:
    return StrategySignal(
        strategy_id="test_v1",
        symbol=symbol,
        side=SignalSide.SELL,
        strength=strength,
        horizon="swing",
        rationale="test exit",
        as_of=utc_now,
        features_used=["close"],
    )


class TestAllocateBuySignal:
    def test_buy_signal_creates_buy_proposal(self, account, settings, utc_now):
        signals = [_buy_signal("AAPL", 0.8, utc_now)]
        allocator = Allocator()
        proposals = allocator.allocate(signals, account, [], None, settings)
        assert len(proposals) == 1
        assert proposals[0].side == "buy"
        assert proposals[0].symbol == "AAPL"
        assert proposals[0].qty > 0

    def test_buy_signal_has_strategy_id(self, account, settings, utc_now):
        signals = [_buy_signal("MSFT", 0.5, utc_now)]
        proposals = Allocator().allocate(signals, account, [], None, settings)
        assert len(proposals) == 1
        assert proposals[0].strategy_id == "test_v1"


class TestAllocateSellSignal:
    def test_sell_signal_creates_sell_proposal(self, account, settings, utc_now):
        positions = [Position(symbol="AAPL", qty=Decimal("10"), avg_price=Decimal("150"))]
        signals = [_sell_signal("AAPL", 0.7, utc_now)]
        proposals = Allocator().allocate(signals, account, positions, None, settings)
        assert len(proposals) == 1
        assert proposals[0].side == "sell"
        assert proposals[0].qty == Decimal("10")  # full exit

    def test_sell_without_position_skipped(self, account, settings, utc_now):
        signals = [_sell_signal("NOPE", 0.7, utc_now)]
        proposals = Allocator().allocate(signals, account, [], None, settings)
        assert len(proposals) == 0


class TestAllocateSortedByStrength:
    def test_higher_strength_first(self, account, settings, utc_now):
        signals = [
            _buy_signal("AAPL", 0.3, utc_now),
            _buy_signal("MSFT", 0.9, utc_now),
            _buy_signal("NVDA", 0.6, utc_now),
        ]
        proposals = Allocator().allocate(signals, account, [], None, settings)
        assert len(proposals) == 3
        assert proposals[0].symbol == "MSFT"
        assert proposals[1].symbol == "NVDA"
        assert proposals[2].symbol == "AAPL"
        # descending
        strengths = [p.signal_strength for p in proposals]
        assert strengths == sorted(strengths, reverse=True)


class TestAllocateIgnoresAtMaxPosition:
    def test_buy_ignored_at_max(self, account, settings, utc_now):
        # max_position_pct = 0.10 → max notional = 10000
        # existing position: 100 shares @ 100 = 10000 → at max
        positions = [
            Position(
                symbol="AAPL",
                qty=Decimal("100"),
                avg_price=Decimal("100"),
                market_value=Decimal("10000"),
            )
        ]
        signals = [_buy_signal("AAPL", 0.8, utc_now)]
        proposals = Allocator().allocate(signals, account, positions, None, settings)
        assert len(proposals) == 0  # ignored

    def test_buy_allowed_below_max(self, account, settings, utc_now):
        positions = [
            Position(
                symbol="AAPL",
                qty=Decimal("10"),
                avg_price=Decimal("100"),
                market_value=Decimal("1000"),
            )
        ]
        signals = [_buy_signal("AAPL", 0.8, utc_now)]
        proposals = Allocator().allocate(signals, account, positions, None, settings)
        assert len(proposals) == 1


class TestAllocateVetoFilters:
    def test_veto_symbol_excluded_when_enabled(self, account, utc_now):
        settings = Settings(llm_veto_enabled=True)
        note = ResearchNote(
            as_of=utc_now,
            regime="risk_off",
            proposed_veto_symbols=["AAPL"],
        )
        signals = [
            _buy_signal("AAPL", 0.9, utc_now),
            _buy_signal("MSFT", 0.5, utc_now),
        ]
        proposals = Allocator().allocate(signals, account, [], note, settings)
        symbols = [p.symbol for p in proposals]
        assert "AAPL" not in symbols
        assert "MSFT" in symbols

    def test_veto_ignored_when_disabled(self, account, utc_now):
        settings = Settings(llm_veto_enabled=False)
        note = ResearchNote(
            as_of=utc_now,
            regime="risk_off",
            proposed_veto_symbols=["AAPL"],
        )
        signals = [
            _buy_signal("AAPL", 0.9, utc_now),
        ]
        proposals = Allocator().allocate(signals, account, [], note, settings)
        assert len(proposals) == 1
        assert proposals[0].symbol == "AAPL"
