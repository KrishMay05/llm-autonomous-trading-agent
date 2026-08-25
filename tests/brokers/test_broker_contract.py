"""Contract tests — any Broker implementation must satisfy these.

These tests program against the ``Broker`` Protocol, not ``PaperBroker``
concretely.  Adding a new broker is as simple as registering a fixture
that returns an instance implementing ``Broker`` and parametrizing
``broker`` over it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

import pytest

from src.brokers.base import Broker
from src.brokers.models import (
    OrderStatus,
    RiskDecision,
    RiskStatus,
    TradeIntent,
)
from src.brokers.paper import PaperBroker

# ── fixtures ───────────────────────────────────────────────────────

_PRICES: dict[str, Decimal] = {
    "AAPL": Decimal("150"),
    "SPY": Decimal("400"),
    "MSFT": Decimal("330"),
}


def _make_intent(
    coid: str,
    *,
    symbol: str = "AAPL",
    side: str = "buy",
    qty: Decimal | str = Decimal("10"),
    order_type: str = "market",
) -> TradeIntent:
    return TradeIntent(
        client_order_id=coid,
        symbol=symbol,
        side=side,
        qty=Decimal(qty),
        order_type=order_type,
        risk_decision=RiskDecision(
            status=RiskStatus.APPROVE,
            approved_qty=Decimal(qty),
        ),
        created_at=datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
    )


def _make_paper_broker() -> PaperBroker:
    """A PaperBroker with known prices for deterministic tests."""
    return PaperBroker(
        initial_capital=Decimal("50000"),
        prices=dict(_PRICES),
        slippage_bps=5,
        commission=Decimal("0"),
    )


# Registry of broker factories for parametrized contract tests.
# To add a new broker, implement the Broker protocol and append
# (id, factory_callable) here.
BROKER_FACTORIES: dict[str, Callable[[], Broker]] = {
    "paper": _make_paper_broker,
}


@pytest.fixture(
    params=list(BROKER_FACTORIES.keys()),
    ids=lambda r: f"broker={r}",
)
def broker(request: pytest.FixtureRequest) -> Broker:
    """Parametrized broker fixture — runs every contract test against
    every registered Broker implementation."""
    return BROKER_FACTORIES[request.param]()


class TestBrokerContract:
    """Protocol-level invariants every Broker must satisfy."""

    def test_has_name(self, broker: Broker) -> None:
        assert isinstance(broker.name, str)
        assert len(broker.name) > 0

    def test_get_account_returns_account(self, broker: Broker) -> None:
        account = broker.get_account()
        assert account is not None
        assert account.cash > 0
        assert account.equity >= 0
        assert account.buying_power == account.cash

    def test_submit_market_buy_fills(self, broker: Broker) -> None:
        intent = _make_intent("contract-buy-1", symbol="AAPL", side="buy", qty="10")
        order = broker.submit_order(intent)

        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == Decimal("10")
        assert order.avg_fill_price is not None
        assert order.avg_fill_price > Decimal("0")

    def test_duplicate_client_order_id_idempotent(self, broker: Broker) -> None:
        intent = _make_intent("contract-dup-1", symbol="AAPL", side="buy", qty="5")
        first = broker.submit_order(intent)
        second = broker.submit_order(intent)

        assert second.client_order_id == first.client_order_id
        assert second.status == first.status
        # No double fill: filled_qty stays at the original qty.
        assert second.filled_qty == Decimal("5")

    def test_cancel_open_order(self, broker: Broker) -> None:
        # Submit and then manually set status to ACCEPTED to simulate
        # an order that hasn't filled yet (paper broker fills instantly).
        intent = _make_intent("contract-cancel-1", symbol="AAPL", side="buy", qty="1")
        order = broker.submit_order(intent)
        # Plant an open copy.
        if isinstance(broker, PaperBroker):
            broker._orders["contract-cancel-1"] = order.model_copy(
                update={"status": OrderStatus.ACCEPTED}
            )
        canceled = broker.cancel_order("contract-cancel-1")
        assert canceled.status == OrderStatus.CANCELED

    def test_insufficient_buying_power_rejected(self, broker: Broker) -> None:
        # 1000 shares * ~150 ≈ 150k >> 50k cash
        intent = _make_intent("contract-reject-1", symbol="AAPL", side="buy", qty="1000")
        order = broker.submit_order(intent)

        assert order.status == OrderStatus.REJECTED
        assert order.filled_qty == Decimal("0")

    def test_list_open_orders_excludes_terminal(self, broker: Broker) -> None:
        # A filled order should NOT appear in open orders.
        intent = _make_intent("contract-open-1", symbol="SPY", side="buy", qty="10")
        broker.submit_order(intent)

        open_orders = broker.list_open_orders()
        for o in open_orders:
            assert o.status not in (
                OrderStatus.FILLED,
                OrderStatus.CANCELED,
                OrderStatus.REJECTED,
                OrderStatus.EXPIRED,
            )

    def test_get_order_returns_none_for_unknown(self, broker: Broker) -> None:
        assert broker.get_order("nonexistent-order-id") is None

    def test_get_order_returns_existing(self, broker: Broker) -> None:
        intent = _make_intent("contract-get-1", symbol="AAPL", side="buy", qty="2")
        submitted = broker.submit_order(intent)
        retrieved = broker.get_order("contract-get-1")
        assert retrieved is not None
        assert retrieved.client_order_id == submitted.client_order_id

    def test_list_positions_after_buy(self, broker: Broker) -> None:
        intent = _make_intent("contract-pos-1", symbol="MSFT", side="buy", qty="10")
        broker.submit_order(intent)

        positions = broker.list_positions()
        assert any(p.symbol == "MSFT" and p.qty == Decimal("10") for p in positions)

    def test_sell_reduces_position_and_increases_cash(self, broker: Broker) -> None:
        # Buy first to establish a position.
        buy = _make_intent("contract-sell-buy", symbol="AAPL", side="buy", qty="20")
        broker.submit_order(buy)

        cash_after_buy = broker.get_account().cash

        # Now sell 5.
        sell = _make_intent("contract-sell-1", symbol="AAPL", side="sell", qty="5")
        order = broker.submit_order(sell)

        assert order.status == OrderStatus.FILLED

        positions = broker.list_positions()
        aapl = next(p for p in positions if p.symbol == "AAPL")
        assert aapl.qty == Decimal("15")

        assert broker.get_account().cash > cash_after_buy

    def test_equity_equals_cash_plus_market_value(self, broker: Broker) -> None:
        # Buy some shares.
        broker.submit_order(
            _make_intent("contract-eq-1", symbol="AAPL", side="buy", qty="10")
        )

        account = broker.get_account()
        positions = broker.list_positions()

        mv_sum = Decimal("0")
        for p in positions:
            assert p.market_value is not None
            mv_sum += p.market_value

        assert account.equity == account.cash + mv_sum
