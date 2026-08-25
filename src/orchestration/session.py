"""In-process agent session used by the CLI and the local UI.

Phase 0: paper broker, stub strategy, synthetic quotes. No live APIs.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.brokers.models import (
    AuditRecord,
    Bar,
    FeatureVector,
    Quote,
    SignalSide,
    StrategySignal,
)
from src.brokers.paper import PaperBroker
from src.config.settings import Settings
from src.orchestration.loop import TradingLoop
from src.portfolio.state import PortfolioState

# Demo marks so the UI is readable without a market-data vendor.
_DEMO_PRICES: dict[str, Decimal] = {
    "SPY": Decimal("512.40"),
    "AAPL": Decimal("189.22"),
    "MSFT": Decimal("428.15"),
    "NVDA": Decimal("875.50"),
}


class StubStrategy:
    """BUY when last close is positive — Phase 0 wiring, not an edge claim."""

    id: str = "stub_v1"

    def evaluate(self, features: FeatureVector, context: Any) -> StrategySignal:
        close = features.values.get("close", 0.0)
        side = SignalSide.BUY if close > 0 else SignalSide.HOLD
        return StrategySignal(
            strategy_id=self.id,
            symbol=features.symbol,
            side=side,
            strength=0.6,
            horizon="swing",
            rationale="stub strategy: buy when close > 0",
            as_of=features.as_of,
            features_used=["close"],
        )


def demo_price(symbol: str) -> Decimal:
    """Return a stable demo last price for *symbol*."""
    return _DEMO_PRICES.get(symbol.upper(), Decimal("100.00"))


def _now() -> datetime:
    return datetime.now(UTC)


def make_quote(symbol: str, price: Decimal | None = None) -> Quote:
    now = _now()
    px = price if price is not None else demo_price(symbol)
    return Quote(
        symbol=symbol,
        bid=px - Decimal("0.01"),
        ask=px + Decimal("0.01"),
        last=px,
        ts=now,
        received_at=now,
        source="stub",
    )


def make_bars(symbol: str, price: Decimal | None = None) -> list[Bar]:
    now = _now()
    px = price if price is not None else demo_price(symbol)
    return [
        Bar(
            symbol=symbol,
            timeframe="1d",
            ts_open=now,
            ts_close=now,
            open=px - Decimal("1"),
            high=px + Decimal("1"),
            low=px - Decimal("2"),
            close=px,
            volume=Decimal("1000000"),
            source="stub",
        )
    ]


def feature_builder(symbol: str, bars: list[Bar], quote: Quote, news: list) -> FeatureVector:
    close = float(quote.last) if quote.last is not None else 0.0
    return FeatureVector(
        symbol=symbol,
        as_of=_now(),
        values={"close": close, "returns_1d": 0.01},
        meta={"source": "stub"},
    )


class AgentSession:
    """Mutable paper-trading session: one loop, accumulated audit, live snapshot."""

    def __init__(
        self,
        settings: Settings,
        *,
        initial_capital: Decimal = Decimal("100000"),
        audit_hook: Callable[[AuditRecord], None] | None = None,
    ) -> None:
        self.settings = settings
        self.audit_hook = audit_hook
        self.audit: list[AuditRecord] = []
        self.runs = 0
        self.last_run_at: datetime | None = None
        self.last_error: str | None = None
        self.last_quotes: dict[str, Quote] = {}
        self.blocked_reason: str | None = None

        prices = {sym: demo_price(sym) for sym in settings.symbol_allowlist}
        self.broker = PaperBroker(
            initial_capital=initial_capital,
            prices=prices,
            slippage_bps=5,
            commission=Decimal("0"),
            name="paper",
        )
        self.portfolio_state = PortfolioState(
            cash=self.broker.get_account().cash,
            session_start_equity=self.broker.get_account().equity,
        )
        self.loop = TradingLoop(
            settings=settings,
            broker=self.broker,
            risk_gate=_ApproveAllRiskGate(),
            strategy_registry={"stub_v1": StubStrategy()},
            feature_builder=feature_builder,
            audit_logger=self._on_audit,
            portfolio_state=self.portfolio_state,
            llm_synthesizer=None,
        )

    def _on_audit(self, record: AuditRecord) -> None:
        self.audit.append(record)
        if self.audit_hook is not None:
            self.audit_hook(record)

    def run_once(self) -> list[AuditRecord]:
        """Run one control-loop iteration. Returns records produced this run."""
        if self.settings.kill_switch:
            self.blocked_reason = "kill_switch"
            return []

        self.blocked_reason = None
        self.last_error = None
        tickers = [s.upper() for s in self.settings.symbol_allowlist]
        quotes = {sym: make_quote(sym) for sym in tickers}
        bars = {sym: make_bars(sym) for sym in tickers}
        for sym, quote in quotes.items():
            if quote.last is not None:
                self.broker.set_price(sym, quote.last)
        self.last_quotes = quotes

        before = len(self.audit)
        try:
            self.loop.run_once(quotes=quotes, bars=bars, news=[])
        except Exception as exc:  # noqa: BLE001 — surface to UI, do not crash server
            self.last_error = f"{type(exc).__name__}: {exc}"
            return []

        self.runs += 1
        self.last_run_at = _now()
        return self.audit[before:]

    def set_kill_switch(self, enabled: bool) -> None:
        """Arm or disarm the session kill switch (in-memory only)."""
        self.settings = self.settings.model_copy(update={"kill_switch": enabled})
        self.loop.settings = self.settings

    def snapshot(self) -> dict[str, Any]:
        """JSON-ready dashboard payload."""
        account = self.broker.get_account()
        positions = self.broker.list_positions()
        start = self.portfolio_state.session_start_equity
        day_pnl = account.equity - start
        day_pnl_pct = (day_pnl / start) if start else Decimal("0")

        return {
            "status": {
                "broker": self.broker.name,
                "live_trading_enabled": self.settings.live_trading_enabled,
                "llm_enabled": self.settings.llm_enabled,
                "llm_model": self.settings.llm_model,
                "kill_switch": self.settings.kill_switch,
                "symbols": [s.upper() for s in self.settings.symbol_allowlist],
                "strategies": ["stub_v1"],
                "configured_strategies": list(self.settings.strategies),
                "runs": self.runs,
                "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
                "last_error": self.last_error,
                "blocked_reason": self.blocked_reason,
                "market_data": "stub",
            },
            "risk": {
                "max_position_pct": str(self.settings.max_position_pct),
                "max_portfolio_heat_pct": str(self.settings.max_portfolio_heat_pct),
                "max_daily_loss_pct": str(self.settings.max_daily_loss_pct),
                "max_orders_per_day": self.settings.max_orders_per_day,
                "pdt_guard_enabled": self.settings.pdt_guard_enabled,
            },
            "portfolio": {
                "equity": str(account.equity),
                "cash": str(account.cash),
                "buying_power": str(account.buying_power),
                "currency": account.currency,
                "session_start_equity": str(start),
                "day_pnl": str(day_pnl),
                "day_pnl_pct": str(day_pnl_pct),
                "positions": [p.model_dump(mode="json") for p in positions],
            },
            "quotes": [q.model_dump(mode="json") for q in self.last_quotes.values()],
            "audit": [r.model_dump(mode="json") for r in reversed(self.audit)],
        }


class _ApproveAllRiskGate:
    """Phase 0 UI/CLI gate — real HardRiskGate is used once wired into the loop."""

    def evaluate(self, proposal, *, account, positions, quote, session):
        from src.brokers.models import RiskDecision, RiskStatus

        return RiskDecision(
            status=RiskStatus.APPROVE,
            approved_qty=proposal.qty,
            reasons=[],
            checks_passed=["phase0_stub"],
            checks_failed=[],
        )
