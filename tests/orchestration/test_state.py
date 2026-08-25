"""Tests for src.portfolio.state."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.brokers.models import Account, Fill, Position, SessionState
from src.portfolio.state import PortfolioState


@pytest.fixture
def utc_now():
    return datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc)


class TestUpdateFromFillBuy:
    def test_buy_fill_decreases_cash(self, utc_now):
        state = PortfolioState(cash=Decimal("10000"))
        fill = Fill(
            order_client_id="order-1",
            qty=Decimal("10"),
            price=Decimal("100"),
            ts=utc_now,
            fee=Decimal("1"),
        )
        state.update_from_fill(fill, "buy")
        assert state.cash == Decimal("10000") - Decimal("10") * Decimal("100") - Decimal("1")

    def test_buy_fill_correct_notional(self, utc_now):
        state = PortfolioState(cash=Decimal("50000"))
        fill = Fill(
            order_client_id="order-2",
            qty=Decimal("5"),
            price=Decimal("200"),
            ts=utc_now,
            fee=Decimal("0"),
        )
        state.update_from_fill(fill, "buy")
        # 50000 - 5*200 = 49000
        assert state.cash == Decimal("49000")


class TestUpdateFromFillSell:
    def test_sell_fill_increases_cash(self, utc_now):
        state = PortfolioState(cash=Decimal("10000"))
        fill = Fill(
            order_client_id="order-3",
            qty=Decimal("10"),
            price=Decimal("100"),
            ts=utc_now,
            fee=Decimal("1"),
        )
        state.update_from_fill(fill, "sell")
        # sell: cash += notional - fee
        assert state.cash == Decimal("10000") + Decimal("10") * Decimal("100") - Decimal("1")

    def test_sell_fill_with_zero_fee(self, utc_now):
        state = PortfolioState(cash=Decimal("0"))
        fill = Fill(
            order_client_id="order-4",
            qty=Decimal("3"),
            price=Decimal("50"),
            ts=utc_now,
            fee=Decimal("0"),
        )
        state.update_from_fill(fill, "sell")
        assert state.cash == Decimal("150")


class TestToSessionState:
    def test_converts_correctly(self, utc_now):
        state = PortfolioState(
            cash=Decimal("50000"),
            session_start_equity=Decimal("100000"),
            realized_pnl=Decimal("500"),
        )
        ss = state.to_session_state()
        assert isinstance(ss, SessionState)
        assert ss.session_start_equity == Decimal("100000")
        assert ss.realized_pnl == Decimal("500")
        assert ss.date.tzinfo is not None  # timezone-aware

    def test_session_state_defaults(self):
        state = PortfolioState()
        ss = state.to_session_state()
        assert ss.realized_pnl == Decimal("0")
        assert ss.session_start_equity == Decimal("0")
        assert ss.orders_today == 0


class TestGetPosition:
    def test_returns_position_if_exists(self):
        pos = Position(symbol="AAPL", qty=Decimal("10"), avg_price=Decimal("150"))
        state = PortfolioState(positions={"AAPL": pos})
        result = state.get_position("AAPL")
        assert result is not None
        assert result.qty == Decimal("10")

    def test_returns_none_if_missing(self):
        state = PortfolioState()
        assert state.get_position("NOPE") is None


class TestUpdateFromReconcile:
    def test_overwrites_positions_and_cash(self):
        old_pos = Position(symbol="SPY", qty=Decimal("10"), avg_price=Decimal("100"))
        state = PortfolioState(
            positions={"SPY": old_pos},
            cash=Decimal("1000"),
            session_start_equity=Decimal("1000"),
        )
        new_positions = [
            Position(symbol="AAPL", qty=Decimal("5"), avg_price=Decimal("200")),
        ]
        account = Account(
            equity=Decimal("5000"),
            cash=Decimal("3000"),
            buying_power=Decimal("6000"),
        )
        state.update_from_reconcile(new_positions, account)
        assert state.get_position("AAPL") is not None
        assert state.get_position("SPY") is None  # overwritten
        assert state.cash == Decimal("3000")
