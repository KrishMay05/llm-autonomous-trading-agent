"""Reconciliation — compare local portfolio state vs broker snapshot.

On mismatch, the orchestrator should set a circuit breaker and skip new
orders for the session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.brokers.models import Account, Position
from src.portfolio.state import PortfolioState

_QTY_EPSILON = Decimal("0.0001")


@dataclass
class ReconcileResult:
    """Outcome of a reconciliation pass."""

    matched: bool
    mismatches: list[str] = field(default_factory=list)
    position_drift: dict[str, dict[str, Decimal]] = field(default_factory=dict)


class Reconciler:
    """Compare local ``PortfolioState`` against broker truth."""

    def reconcile(
        self,
        local: PortfolioState,
        broker_positions: list[Position],
        account: Account,
    ) -> ReconcileResult:
        broker_map: dict[str, Position] = {
            p.symbol.upper(): p for p in broker_positions
        }
        local_map: dict[str, Position] = {
            sym.upper(): pos for sym, pos in local.positions.items()
        }

        mismatches: list[str] = []
        drift: dict[str, dict[str, Decimal]] = {}

        all_symbols = set(broker_map) | set(local_map)
        for symbol in sorted(all_symbols):
            local_pos = local_map.get(symbol)
            broker_pos = broker_map.get(symbol)

            local_qty = local_pos.qty if local_pos else Decimal("0")
            broker_qty = broker_pos.qty if broker_pos else Decimal("0")

            qty_diff = abs(local_qty - broker_qty)
            if qty_diff > _QTY_EPSILON:
                mismatches.append(
                    f"Position qty mismatch for {symbol}: "
                    f"local={local_qty} broker={broker_qty} diff={qty_diff}"
                )
                drift[symbol] = {
                    "local_qty": local_qty,
                    "broker_qty": broker_qty,
                    "diff": local_qty - broker_qty,
                }

        # Cash check (allow small float noise)
        cash_diff = abs(local.cash - account.cash)
        if cash_diff > _QTY_EPSILON:
            mismatches.append(
                f"Cash mismatch: local={local.cash} broker={account.cash} "
                f"diff={cash_diff}"
            )
            drift["_CASH"] = {
                "local": local.cash,
                "broker": account.cash,
                "diff": local.cash - account.cash,
            }

        return ReconcileResult(
            matched=len(mismatches) == 0,
            mismatches=mismatches,
            position_drift=drift,
        )
