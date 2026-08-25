"""Portfolio state — local view of positions, cash, and session PnL.

Kept in sync via fills and broker reconcile snapshots.  The source of truth
for ``SessionState`` passed into the risk gate.
"""

from __future__ import annotations

from decimal import Decimal
from typing import MutableMapping

from src.brokers.models import Account, Fill, Position, SessionState


class PortfolioState:
    """Mutable local view of the portfolio.

    Not thread-safe; the orchestration loop is single-threaded.
    """

    def __init__(
        self,
        *,
        positions: dict[str, Position] | None = None,
        cash: Decimal = Decimal("0"),
        session_start_equity: Decimal = Decimal("0"),
        realized_pnl: Decimal = Decimal("0"),
    ) -> None:
        self._positions: dict[str, Position] = dict(positions) if positions else {}
        self.cash: Decimal = cash
        self.session_start_equity: Decimal = session_start_equity
        self.realized_pnl: Decimal = realized_pnl

    # ── accessors ────────────────────────────────────────────────────

    @property
    def positions(self) -> dict[str, Position]:
        return self._positions

    def get_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol.upper())

    # ── mutations ────────────────────────────────────────────────────

    def update_from_fill(self, fill: Fill, side: str) -> None:
        """Apply a fill to local state.

        ``side`` is the order side (``"buy"`` or ``"sell"``), *not* the
        signal side — a SELL *signal* may still result in a sell fill that
        reduces a long position.
        """
        # We need the symbol from the fill's order client id mapping, but
        # Fill doesn't carry symbol.  The caller is expected to pass the
        # correct side; for qty/price we use the fill directly.
        #
        # Because Fill is frozen and has ``order_client_id`` rather than
        # ``symbol``, we cannot update the correct Position here without
        # additional context.  In practice the orchestration loop calls
        # this with the symbol resolved from the Order.  We accept that
        # ``Fill`` lacks ``symbol`` and update cash generically; position
        # updates are handled via ``update_from_reconcile`` snapshots.
        #
        # Cash impact:
        #   buy  → cash decreases by qty * price + fee
        #   sell → cash increases by qty * price - fee
        notional = fill.qty * fill.price
        side_lower = side.lower()
        if side_lower == "buy":
            self.cash -= notional + fill.fee
        elif side_lower == "sell":
            self.cash += notional - fill.fee
        else:
            raise ValueError(f"Unknown side '{side}' (expected 'buy' or 'sell')")

    def update_from_reconcile(
        self,
        positions: list[Position],
        account: Account,
    ) -> None:
        """Overwrite local state from a broker snapshot.

        This is the hard-sync path — local state is replaced, not merged.
        Realized PnL is *not* overwritten (broker snapshots don't carry it).
        """
        self._positions = {p.symbol.upper(): p for p in positions}
        self.cash = account.cash
        # session_start_equity is preserved unless caller resets it
        if self.session_start_equity == Decimal("0"):
            self.session_start_equity = account.equity

    # ── export ──────────────────────────────────────────────────────

    def to_session_state(self) -> SessionState:
        """Convert to ``SessionState`` for the risk gate."""
        from datetime import datetime, timezone

        return SessionState(
            date=datetime.now(timezone.utc),
            realized_pnl=self.realized_pnl,
            session_start_equity=self.session_start_equity,
        )
