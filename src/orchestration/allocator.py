"""Allocator — convert strategy signals into trade proposals.

Rules:
- BUY  → ``TradeProposal(side="buy",  qty=sizing(strength, equity, max_pct))``
- SELL → ``TradeProposal(side="sell", qty=full_position_exit)``  (liquidate)
- Ignore BUY if already at max position (``max_position_pct`` of equity).
- Sort by signal strength descending.
- If ``LLM_VETO_ENABLED`` and ``research_note`` has veto symbols, exclude them.
"""

from __future__ import annotations

from decimal import Decimal

from src.brokers.models import (
    Account,
    Position,
    ResearchNote,
    StrategySignal,
    SignalSide,
    TradeProposal,
)
from src.config.settings import Settings


def _max_position_value(equity: Decimal, max_pct: Decimal) -> Decimal:
    """Max notional allowed for a single symbol."""
    return equity * max_pct


def _estimate_price(position: Position) -> Decimal:
    """Use avg_price as a proxy for current notional (Phase 0 heuristic)."""
    return position.avg_price if position.avg_price else Decimal("0")


class Allocator:
    """Convert ``StrategySignal`` list → flat ``TradeProposal`` list."""

    def allocate(
        self,
        signals: list[StrategySignal],
        account: Account,
        positions: list[Position],
        research_note: ResearchNote | None,
        settings: Settings,
    ) -> list[TradeProposal]:
        position_map: dict[str, Position] = {
            p.symbol.upper(): p for p in positions
        }
        veto_symbols: set[str] = set()
        if (
            settings.llm_veto_enabled
            and research_note is not None
            and research_note.proposed_veto_symbols
        ):
            veto_symbols = {s.upper() for s in research_note.proposed_veto_symbols}

        equity = account.equity
        max_notional = _max_position_value(equity, settings.max_position_pct)

        proposals: list[TradeProposal] = []
        for sig in signals:
            symbol = sig.symbol.upper()

            # Veto filter
            if symbol in veto_symbols:
                continue

            if sig.side == SignalSide.BUY:
                pos = position_map.get(symbol)
                current_qty = pos.qty if pos else Decimal("0")
                current_price = _estimate_price(pos) if pos else None
                current_notional = (
                    (current_qty * current_price)
                    if pos and current_price
                    else Decimal("0")
                )

                # Skip if already at max position
                if current_notional >= max_notional and max_notional > 0:
                    continue

                # Sizing: equity * max_pct * strength, as share count
                # Phase 0: assume price ≈ avg_price or use notional/100 as stub
                target_notional = max_notional * Decimal(str(sig.strength))
                if target_notional <= 0:
                    continue
                # We don't have live price here; use a per-share stub.
                # The risk gate / broker will refine.  For Phase 0 we
                # compute qty as notional / a placeholder price of 1 so
                # the proposal is well-formed; the loop overrides this
                # with the actual quote price before submit.
                stub_price = current_price if current_price and current_price > 0 else Decimal("100")
                qty = (target_notional / stub_price).quantize(Decimal("0.0001"))
                if qty <= 0:
                    continue

                proposals.append(
                    TradeProposal(
                        symbol=symbol,
                        side="buy",
                        qty=qty,
                        order_type="market",
                        limit_price=None,
                        strategy_id=sig.strategy_id,
                        signal_strength=sig.strength,
                        rationale=sig.rationale,
                    )
                )

            elif sig.side == SignalSide.SELL:
                pos = position_map.get(symbol)
                if pos is None or pos.qty <= 0:
                    # Can't sell what we don't have
                    continue
                proposals.append(
                    TradeProposal(
                        symbol=symbol,
                        side="sell",
                        qty=pos.qty,
                        order_type="market",
                        limit_price=None,
                        strategy_id=sig.strategy_id,
                        signal_strength=sig.strength,
                        rationale=sig.rationale,
                    )
                )

            # HOLD / REDUCE → no proposal in Phase 0

        # Sort by strength descending
        proposals.sort(key=lambda p: p.signal_strength, reverse=True)
        return proposals
