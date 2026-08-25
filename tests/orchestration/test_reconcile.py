"""Tests for src.portfolio.reconcile."""

from __future__ import annotations

from decimal import Decimal

from src.brokers.models import Account, Position
from src.portfolio.reconcile import Reconciler
from src.portfolio.state import PortfolioState


class TestReconcileMatch:
    def test_positions_match(self):
        state = PortfolioState(
            positions={"AAPL": Position(symbol="AAPL", qty=Decimal("10"))},
            cash=Decimal("5000"),
        )
        broker_positions = [Position(symbol="AAPL", qty=Decimal("10"))]
        account = Account(
            equity=Decimal("10000"),
            cash=Decimal("5000"),
            buying_power=Decimal("10000"),
        )
        r = Reconciler().reconcile(state, broker_positions, account)
        assert r.matched is True
        assert len(r.mismatches) == 0

    def test_empty_both_sides(self):
        state = PortfolioState(cash=Decimal("5000"))
        account = Account(
            equity=Decimal("10000"),
            cash=Decimal("5000"),
            buying_power=Decimal("10000"),
        )
        r = Reconciler().reconcile(state, [], account)
        assert r.matched is True


class TestReconcileMismatch:
    def test_position_qty_drift(self):
        state = PortfolioState(
            positions={"AAPL": Position(symbol="AAPL", qty=Decimal("10"))},
            cash=Decimal("5000"),
        )
        broker_positions = [Position(symbol="AAPL", qty=Decimal("20"))]
        account = Account(
            equity=Decimal("10000"),
            cash=Decimal("5000"),
            buying_power=Decimal("10000"),
        )
        r = Reconciler().reconcile(state, broker_positions, account)
        assert r.matched is False
        assert len(r.mismatches) > 0
        assert "AAPL" in r.position_drift

    def test_missing_broker_position(self):
        state = PortfolioState(
            positions={"AAPL": Position(symbol="AAPL", qty=Decimal("10"))},
            cash=Decimal("5000"),
        )
        broker_positions: list[Position] = []
        account = Account(
            equity=Decimal("10000"),
            cash=Decimal("5000"),
            buying_power=Decimal("10000"),
        )
        r = Reconciler().reconcile(state, broker_positions, account)
        assert r.matched is False
        assert "AAPL" in r.position_drift

    def test_cash_mismatch(self):
        state = PortfolioState(cash=Decimal("5000"))
        account = Account(
            equity=Decimal("10000"),
            cash=Decimal("6000"),
            buying_power=Decimal("10000"),
        )
        r = Reconciler().reconcile(state, [], account)
        assert r.matched is False
        assert "_CASH" in r.position_drift


class TestReconcileEpsilon:
    def test_tiny_diff_within_epsilon(self):
        state = PortfolioState(
            positions={"AAPL": Position(symbol="AAPL", qty=Decimal("10.00005"))},
            cash=Decimal("5000"),
        )
        broker_positions = [Position(symbol="AAPL", qty=Decimal("10.00006"))]
        account = Account(
            equity=Decimal("10000"),
            cash=Decimal("5000"),
            buying_power=Decimal("10000"),
        )
        r = Reconciler().reconcile(state, broker_positions, account)
        # diff = 0.00001 < 0.0001 → matched
        assert r.matched is True

    def test_diff_just_above_epsilon(self):
        state = PortfolioState(
            positions={"AAPL": Position(symbol="AAPL", qty=Decimal("10.00"))},
            cash=Decimal("5000"),
        )
        broker_positions = [Position(symbol="AAPL", qty=Decimal("10.001"))]
        account = Account(
            equity=Decimal("10000"),
            cash=Decimal("5000"),
            buying_power=Decimal("10000"),
        )
        r = Reconciler().reconcile(state, broker_positions, account)
        assert r.matched is False
