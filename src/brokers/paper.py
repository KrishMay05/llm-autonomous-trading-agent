"""In-memory paper trading broker — simulates fills with slippage."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from src.brokers.models import (
    Account,
    Fill,
    Order,
    OrderStatus,
    Position,
    TradeIntent,
)

_TERMINAL_STATUSES: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    }
)

_BPS: Decimal = Decimal("10000")


class PaperBroker:
    """A fully in-memory broker for testing and dry-run trading.

    - Market orders fill immediately at ``price * (1 ± slippage_bps/10000)``.
    - Buys pay slippage *up* (worse), sells receive slippage *down* (worse).
    - ``submit_order`` is idempotent on ``client_order_id``.
    - Insufficient cash (buys) or position (sells) → ``REJECTED``.
    """

    def __init__(
        self,
        *,
        initial_capital: Decimal = Decimal("100000"),
        prices: dict[str, Decimal] | None = None,
        slippage_bps: int = 5,
        commission: Decimal = Decimal("0"),
        name: str = "paper",
        get_price: Callable[[str], Decimal] | None = None,
    ) -> None:
        self._name: str = name
        self._cash: Decimal = Decimal(initial_capital)
        self._prices: dict[str, Decimal] = dict(prices or {})
        self._slippage_bps: int = slippage_bps
        self._commission: Decimal = Decimal(commission)
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}
        self._counter: int = 0
        self._get_price_fn: Callable[[str], Decimal] | None = get_price

    # ── public properties ──────────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    # ── price oracle ───────────────────────────────────────────────
    def set_price(self, symbol: str, price: Decimal) -> None:
        """Update the last price for a symbol (used for fill + mark-to-market)."""
        self._prices[symbol] = Decimal(price)

    def _resolve_price(self, symbol: str) -> Decimal:
        """Return the last price for *symbol* — callable first, then dict."""
        if self._get_price_fn is not None:
            return self._get_price_fn(symbol)
        if symbol in self._prices:
            return self._prices[symbol]
        raise KeyError(f"Unknown symbol: {symbol}")

    def _next_broker_id(self) -> str:
        self._counter += 1
        return f"paper-{self._counter:06d}"

    # ── Broker protocol ────────────────────────────────────────────
    def get_account(self) -> Account:
        market_value = Decimal("0")
        for pos in self._positions.values():
            if pos.qty == 0:
                continue
            try:
                price = self._resolve_price(pos.symbol)
            except KeyError:
                continue
            market_value += price * pos.qty
        return Account(
            equity=self._cash + market_value,
            cash=self._cash,
            buying_power=self._cash,
            currency="USD",
            pattern_day_trader=False,
        )

    def list_positions(self) -> list[Position]:
        result: list[Position] = []
        for pos in self._positions.values():
            if pos.qty == 0:
                continue
            try:
                price = self._resolve_price(pos.symbol)
                mv = price * pos.qty
            except KeyError:
                mv = None
            result.append(pos.model_copy(update={"market_value": mv}))
        return result

    def get_order(self, client_order_id: str) -> Order | None:
        return self._orders.get(client_order_id)

    def list_open_orders(self) -> list[Order]:
        return [o for o in self._orders.values() if o.status not in _TERMINAL_STATUSES]

    def submit_order(self, intent: TradeIntent) -> Order:
        # Idempotent: duplicate client_order_id → return existing, no double fill.
        existing = self._orders.get(intent.client_order_id)
        if existing is not None:
            return existing

        now = datetime.now(timezone.utc)
        broker_id = self._next_broker_id()

        order = Order(
            broker_order_id=broker_id,
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            qty=intent.qty,
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            status=OrderStatus.ACCEPTED,
            submitted_at=intent.created_at,
            updated_at=now,
            raw={},
        )

        # Only market orders are supported in the paper broker.
        if intent.order_type != "market":
            rejected = order.model_copy(
                update={
                    "status": OrderStatus.REJECTED,
                    "updated_at": now,
                    "raw": {"reason": f"Unsupported order type: {intent.order_type}"},
                }
            )
            self._orders[intent.client_order_id] = rejected
            return rejected

        # Compute fill price with slippage.
        try:
            base_price = self._resolve_price(intent.symbol)
        except KeyError:
            rejected = order.model_copy(
                update={
                    "status": OrderStatus.REJECTED,
                    "updated_at": now,
                    "raw": {"reason": f"Unknown symbol: {intent.symbol}"},
                }
            )
            self._orders[intent.client_order_id] = rejected
            return rejected

        slip = Decimal(self._slippage_bps) / _BPS
        if intent.side == "buy":
            fill_price = base_price * (Decimal("1") + slip)
        else:  # sell
            fill_price = base_price * (Decimal("1") - slip)

        notional = fill_price * intent.qty
        commission = self._commission

        # ── Buying power check (buys) ──────────────────────────────
        if intent.side == "buy":
            total_cost = notional + commission
            if total_cost > self._cash:
                rejected = order.model_copy(
                    update={
                        "status": OrderStatus.REJECTED,
                        "updated_at": now,
                        "raw": {
                            "reason": "Insufficient buying power",
                            "required": str(total_cost),
                            "available": str(self._cash),
                        },
                    }
                )
                self._orders[intent.client_order_id] = rejected
                return rejected

        # ── Position check (sells) ─────────────────────────────────
        if intent.side == "sell":
            pos = self._positions.get(intent.symbol)
            current_qty = pos.qty if pos is not None else Decimal("0")
            if intent.qty > current_qty:
                rejected = order.model_copy(
                    update={
                        "status": OrderStatus.REJECTED,
                        "updated_at": now,
                        "raw": {
                            "reason": "Insufficient position",
                            "requested": str(intent.qty),
                            "available": str(current_qty),
                        },
                    }
                )
                self._orders[intent.client_order_id] = rejected
                return rejected

        # ── Fill the order ─────────────────────────────────────────
        fill = Fill(
            order_client_id=intent.client_order_id,
            qty=intent.qty,
            price=fill_price,
            ts=now,
            fee=commission,
        )

        if intent.side == "buy":
            self._apply_buy(intent.symbol, intent.qty, fill_price)
            self._cash -= (notional + commission)
        else:  # sell
            self._apply_sell(intent.symbol, intent.qty, fill_price)
            self._cash += (notional - commission)

        filled_order = order.model_copy(
            update={
                "filled_qty": intent.qty,
                "avg_fill_price": fill_price,
                "status": OrderStatus.FILLED,
                "updated_at": now,
                "raw": {
                    "fills": [
                        {
                            "qty": str(fill.qty),
                            "price": str(fill.price),
                            "ts": fill.ts.isoformat(),
                            "fee": str(fill.fee),
                        }
                    ],
                },
            }
        )
        self._orders[intent.client_order_id] = filled_order
        return filled_order

    def cancel_order(self, client_order_id: str) -> Order:
        order = self._orders.get(client_order_id)
        if order is None:
            raise ValueError(f"Unknown order: {client_order_id}")
        if order.status in _TERMINAL_STATUSES:
            return order  # Already terminal — idempotent no-op.
        now = datetime.now(timezone.utc)
        canceled = order.model_copy(
            update={
                "status": OrderStatus.CANCELED,
                "updated_at": now,
            }
        )
        self._orders[client_order_id] = canceled
        return canceled

    # ── internal position helpers ───────────────────────────────────
    def _apply_buy(self, symbol: str, qty: Decimal, price: Decimal) -> None:
        existing = self._positions.get(symbol)
        if existing is not None and existing.qty != 0:
            new_qty = existing.qty + qty
            total_cost_basis = existing.avg_price * existing.qty + price * qty
            new_avg = total_cost_basis / new_qty
        else:
            new_qty = qty
            new_avg = price
        self._positions[symbol] = Position(
            symbol=symbol,
            qty=new_qty,
            avg_price=new_avg,
        )

    def _apply_sell(self, symbol: str, qty: Decimal, price: Decimal) -> None:
        existing = self._positions.get(symbol)
        if existing is None:
            # Shouldn't happen — guarded by position check above.
            return
        new_qty = existing.qty - qty
        self._positions[symbol] = Position(
            symbol=symbol,
            qty=new_qty,
            avg_price=existing.avg_price,
        )
