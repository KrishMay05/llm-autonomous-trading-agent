"""Broker protocol — the interface every broker adapter must satisfy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.brokers.models import Account, Order, Position, TradeIntent


@runtime_checkable
class Broker(Protocol):
    """The contract between the trading engine and any broker backend.

    Implementations must provide a ``name`` and the six core methods below.
    All money values use ``Decimal``; all datetimes are timezone-aware UTC.
    """

    name: str

    def get_account(self) -> Account:
        """Return the current account snapshot (cash, equity, buying power)."""
        ...

    def list_positions(self) -> list[Position]:
        """Return all open positions (qty ≠ 0)."""
        ...

    def get_order(self, client_order_id: str) -> Order | None:
        """Return a single order by its client-side id, or ``None``."""
        ...

    def list_open_orders(self) -> list[Order]:
        """Return all orders not in a terminal status."""
        ...

    def submit_order(self, intent: TradeIntent) -> Order:
        """Submit a post-risk trade intent and return the resulting Order.

        Must be idempotent on ``client_order_id`` — a duplicate submission
        returns the existing Order without creating a new fill.
        """
        ...

    def cancel_order(self, client_order_id: str) -> Order:
        """Cancel an open order; return the updated (CANCELED) Order."""
        ...
