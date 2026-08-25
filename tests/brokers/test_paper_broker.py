"""Focused unit tests for PaperBroker behaviour."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.brokers.models import (
    Order,
    OrderStatus,
    RiskDecision,
    RiskStatus,
    TradeIntent,
)
from src.brokers.paper import PaperBroker

# ── helpers ────────────────────────────────────────────────────────

def _make_intent(
    client_order_id: str,
    symbol: str = "AAPL",
    side: str = "buy",
    qty: Decimal | str = Decimal("10"),
    order_type: str = "market",
) -> TradeIntent:
    return TradeIntent(
        client_order_id=client_order_id,
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


@pytest.fixture
def broker() -> PaperBroker:
    return PaperBroker(
        initial_capital=Decimal("10000"),
        prices={"AAPL": Decimal("150"), "SPY": Decimal("400")},
        slippage_bps=5,
        commission=Decimal("0"),
    )


# ── tests ──────────────────────────────────────────────────────────

class TestSubmitMarketBuyFills:
    def test_submit_market_buy_fills(self, broker: PaperBroker) -> None:
        """A market buy fills immediately at price with slippage applied."""
        intent = _make_intent("order-1", symbol="AAPL", side="buy", qty="10")
        order = broker.submit_order(intent)

        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == Decimal("10")
        # 150 * (1 + 5/10000) = 150 * 1.0005 = 150.075
        expected_price = Decimal("150") * (Decimal("1") + Decimal("5") / Decimal("10000"))
        assert order.avg_fill_price == expected_price

    def test_cash_decreased_by_fill(self, broker: PaperBroker) -> None:
        intent = _make_intent("order-1", symbol="AAPL", side="buy", qty="10")
        broker.submit_order(intent)

        expected_price = Decimal("150") * (Decimal("1") + Decimal("5") / Decimal("10000"))
        expected_cost = expected_price * Decimal("10")
        assert broker.get_account().cash == Decimal("10000") - expected_cost


class TestDuplicateClientIdIdempotent:
    def test_duplicate_client_order_id_idempotent(self, broker: PaperBroker) -> None:
        """Same client_order_id returns the same Order — no double fill."""
        intent = _make_intent("order-1", symbol="AAPL", side="buy", qty="10")
        first = broker.submit_order(intent)

        # Submit the exact same intent again.
        second = broker.submit_order(intent)

        assert second is first
        assert first.status == OrderStatus.FILLED

        # Cash should only decrease once.
        expected_price = Decimal("150") * (Decimal("1") + Decimal("5") / Decimal("10000"))
        expected_cost = expected_price * Decimal("10")
        assert broker.get_account().cash == Decimal("10000") - expected_cost

        # Only one order in the store.
        assert len(broker._orders) == 1


class TestCancelOrder:
    def test_cancel_order(self, broker: PaperBroker) -> None:
        """Cancelling an open (non-terminal) order sets status CANCELED."""
        intent = _make_intent("order-1", symbol="AAPL", side="buy", qty="10")
        order = broker.submit_order(intent)

        # Market orders fill immediately in the paper broker, so we need
        # to manually plant an open order to test cancellation.
        broker._orders["order-1"] = order.model_copy(
            update={"status": OrderStatus.ACCEPTED}
        )

        canceled = broker.cancel_order("order-1")
        assert canceled.status == OrderStatus.CANCELED
        assert canceled.client_order_id == "order-1"


class TestInsufficientBuyingPower:
    def test_insufficient_buying_power_rejected(self, broker: PaperBroker) -> None:
        """A buy that costs more than available cash is REJECTED."""
        # 100 shares * ~150 = ~15007 > 10000 cash
        intent = _make_intent("order-1", symbol="AAPL", side="buy", qty="100")
        order = broker.submit_order(intent)

        assert order.status == OrderStatus.REJECTED
        assert order.filled_qty == Decimal("0")
        # Cash unchanged.
        assert broker.get_account().cash == Decimal("10000")


class TestGetAccountEquity:
    def test_get_account_equity(self, broker: PaperBroker) -> None:
        """Equity = cash + sum(position market_value) at current prices."""
        # Buy 20 AAPL @ ~150.
        intent = _make_intent("order-1", symbol="AAPL", side="buy", qty="20")
        broker.submit_order(intent)

        account = broker.get_account()
        fill_price = Decimal("150") * (Decimal("1") + Decimal("5") / Decimal("10000"))
        expected_cash = Decimal("10000") - fill_price * Decimal("20")
        # Market value uses the *current* price (150), not fill price.
        expected_mv = Decimal("150") * Decimal("20")
        expected_equity = expected_cash + expected_mv

        assert account.cash == expected_cash
        assert account.equity == expected_equity
        assert account.buying_power == expected_cash


class TestListOpenOrders:
    def test_list_open_orders(self, broker: PaperBroker) -> None:
        """Only non-terminal orders appear in list_open_orders."""
        # Fill one order.
        intent1 = _make_intent("order-1", symbol="AAPL", side="buy", qty="5")
        broker.submit_order(intent1)

        # Manually plant an ACCEPTED (open) order.
        intent2 = _make_intent("order-2", symbol="SPY", side="buy", qty="1")
        open_order = Order(
            broker_order_id="paper-999",
            client_order_id="order-2",
            symbol="SPY",
            side="buy",
            qty=Decimal("1"),
            status=OrderStatus.ACCEPTED,
            submitted_at=datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
        )
        broker._orders["order-2"] = open_order

        # Manually plant a REJECTED (terminal) order.
        intent3 = _make_intent("order-3", symbol="AAPL", side="buy", qty="99999")
        broker.submit_order(intent3)  # will be REJECTED (insufficient cash)

        open_orders = broker.list_open_orders()
        client_ids = {o.client_order_id for o in open_orders}

        # Only order-2 is open; order-1 (FILLED) and order-3 (REJECTED) excluded.
        assert "order-2" in client_ids
        assert "order-1" not in client_ids
        assert "order-3" not in client_ids


class TestSellDecreasesPosition:
    def test_sell_decreases_position(self, broker: PaperBroker) -> None:
        """Selling reduces position qty and increases cash."""
        # First, buy 20 AAPL.
        buy_intent = _make_intent("buy-1", symbol="AAPL", side="buy", qty="20")
        broker.submit_order(buy_intent)

        cash_after_buy = broker.get_account().cash
        positions_after_buy = broker.list_positions()
        aapl_pos = next(p for p in positions_after_buy if p.symbol == "AAPL")
        assert aapl_pos.qty == Decimal("20")

        # Now sell 5.
        sell_intent = _make_intent("sell-1", symbol="AAPL", side="sell", qty="5")
        sell_order = broker.submit_order(sell_intent)

        assert sell_order.status == OrderStatus.FILLED
        assert sell_order.side == "sell"

        # Position reduced by 5.
        positions_after_sell = broker.list_positions()
        aapl_pos_after = next(p for p in positions_after_sell if p.symbol == "AAPL")
        assert aapl_pos_after.qty == Decimal("15")

        # Cash increased.
        assert broker.get_account().cash > cash_after_buy
