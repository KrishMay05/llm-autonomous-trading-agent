"""Hard risk gate — deterministic last-line defense before broker submit.

No LLM, no strategy logic: just yes/no/resize based on settings and state.
Every ``evaluate()`` call returns a fully-populated ``RiskDecision`` with
explicit ``checks_passed`` / ``checks_failed`` / ``reasons`` so the audit
trail is self-explanatory.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.brokers.models import (
    Account,
    Position,
    Quote,
    RiskDecision,
    RiskStatus,
    SessionState,
    TradeProposal,
)
from src.config.settings import Settings
from src.risk.sizing import resize_to_max

# Stable reason codes — exported for tests / audit consumers.
ALLOWLIST = "ALLOWLIST"
KILL_SWITCH = "KILL_SWITCH"
STALE_DATA = "STALE_DATA"
MISSING_QUOTE = "MISSING_QUOTE"
INVALID_QTY = "INVALID_QTY"
MAX_POSITION = "MAX_POSITION"
DAILY_LOSS = "DAILY_LOSS"
MAX_ORDERS = "MAX_ORDERS"
HEAT = "HEAT"
PDT = "PDT"


class HardRiskGate:
    """Run every hard check in order; APPROVE / RESIZE / REJECT the proposal."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # ── public API ──────────────────────────────────────────────
    def evaluate(
        self,
        proposal: TradeProposal,
        *,
        account: Account,
        positions: list[Position],
        quote: Quote,
        session: SessionState,
    ) -> RiskDecision:
        is_sell = proposal.side == "sell"
        checks_passed: list[str] = []
        checks_failed: list[str] = []
        reasons: list[str] = []

        # ── 1. ALLOWLIST ─────────────────────────────────────────
        if proposal.symbol.upper() not in [
            s.upper() for s in self.settings.symbol_allowlist
        ]:
            checks_failed.append(ALLOWLIST)
            reasons.append(ALLOWLIST)
        else:
            checks_passed.append(ALLOWLIST)

        # ── 2. KILL_SWITCH (bypassed for sells — reducing risk is ok) ──
        if self.settings.kill_switch and not is_sell:
            checks_failed.append(KILL_SWITCH)
            reasons.append(KILL_SWITCH)
        else:
            checks_passed.append(KILL_SWITCH)

        # ── 3. STALE_DATA ────────────────────────────────────────
        max_age = self.settings.max_quote_age_sec
        now = datetime.now(timezone.utc)
        quote_age = (now - quote.received_at).total_seconds()
        if quote_age > max_age:
            checks_failed.append(STALE_DATA)
            reasons.append(STALE_DATA)
        else:
            checks_passed.append(STALE_DATA)

        # ── 4. MISSING_QUOTE ─────────────────────────────────────
        if quote.last is None:
            checks_failed.append(MISSING_QUOTE)
            reasons.append(MISSING_QUOTE)
        else:
            checks_passed.append(MISSING_QUOTE)

        # ── 5. INVALID_QTY ───────────────────────────────────────
        if proposal.qty <= 0:
            checks_failed.append(INVALID_QTY)
            reasons.append(INVALID_QTY)
        else:
            checks_passed.append(INVALID_QTY)

        # ── 6. MAX_POSITION (resize path for buys) ────────────────
        max_position_notional = self.settings.max_position_pct * account.equity
        current_position_value = self._current_position_value(
            proposal.symbol, positions
        )
        proposed_value = proposal.qty * (quote.last or Decimal("0"))
        max_position_failed = False
        if not is_sell and proposed_value + current_position_value > max_position_notional:
            max_position_failed = True
            checks_failed.append(MAX_POSITION)
            reasons.append(MAX_POSITION)
        else:
            checks_passed.append(MAX_POSITION)

        # ── 7. DAILY_LOSS (bypassed for sells) ────────────────────
        if not is_sell and session.session_start_equity > 0:
            loss_ratio = session.realized_pnl / session.session_start_equity
            if loss_ratio <= -self.settings.max_daily_loss_pct:
                checks_failed.append(DAILY_LOSS)
                reasons.append(DAILY_LOSS)
            else:
                checks_passed.append(DAILY_LOSS)
        else:
            checks_passed.append(DAILY_LOSS)

        # ── 8. MAX_ORDERS ────────────────────────────────────────
        if session.orders_today >= self.settings.max_orders_per_day:
            checks_failed.append(MAX_ORDERS)
            reasons.append(MAX_ORDERS)
        else:
            checks_passed.append(MAX_ORDERS)

        # ── 9. HEAT ──────────────────────────────────────────────
        total_exposure = sum(
            (p.market_value or Decimal("0")) for p in positions
        )
        heat_cap = self.settings.max_portfolio_heat_pct * account.equity
        if not is_sell and total_exposure + proposed_value > heat_cap:
            checks_failed.append(HEAT)
            reasons.append(HEAT)
        else:
            checks_passed.append(HEAT)

        # ── 10. PDT ──────────────────────────────────────────────
        if (
            self.settings.pdt_guard_enabled
            and account.pattern_day_trader
            and account.equity < Decimal("25000")
        ):
            checks_failed.append(PDT)
            reasons.append(PDT)
        else:
            checks_passed.append(PDT)

        # ── decision ──────────────────────────────────────────────
        # No hard failures → maybe resize, else approve.
        if not checks_failed:
            return RiskDecision(
                status=RiskStatus.APPROVE,
                approved_qty=proposal.qty,
                reasons=[],
                checks_passed=checks_passed,
                checks_failed=[],
            )

        # Only MAX_POSITION failed (and it's a buy) → resize.
        hard_fails = [c for c in checks_failed if c != MAX_POSITION]
        if not hard_fails and max_position_failed and not is_sell:
            if quote.last is None or quote.last <= 0:
                return RiskDecision(
                    status=RiskStatus.REJECT,
                    approved_qty=Decimal("0"),
                    reasons=reasons,
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
            resized = resize_to_max(
                qty=proposal.qty,
                current_position_value=current_position_value,
                max_allowed=max_position_notional,
                price=quote.last,
            )
            if resized <= 0:
                return RiskDecision(
                    status=RiskStatus.REJECT,
                    approved_qty=Decimal("0"),
                    reasons=reasons,
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
            return RiskDecision(
                status=RiskStatus.RESIZE,
                approved_qty=resized,
                reasons=reasons,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )

        # Any other hard fail → reject.
        return RiskDecision(
            status=RiskStatus.REJECT,
            approved_qty=Decimal("0"),
            reasons=reasons,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    # ── helpers ─────────────────────────────────────────────────
    @staticmethod
    def _current_position_value(symbol: str, positions: list[Position]) -> Decimal:
        """Sum the market value of the existing position for ``symbol``."""
        for p in positions:
            if p.symbol.upper() == symbol.upper():
                if p.market_value is not None:
                    return p.market_value
                return p.qty * p.avg_price
        return Decimal("0")
