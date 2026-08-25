#!/usr/bin/env python3
"""CLI entry point for the trading agent.

Phase 0: uses fake/mock quotes and bars since data providers aren't wired yet.
Run one iteration of the loop and print results to stdout.

Usage:
    python scripts/run_agent.py --tickers SPY,AAPL --broker paper
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

# Ensure src/ is importable when running as a script
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from src.brokers.models import (  # noqa: E402
    Account,
    AuditRecord,
    Bar,
    FeatureVector,
    OrderStatus,
    Position,
    Quote,
    RiskDecision,
    RiskStatus,
    SessionState,
    StrategySignal,
    TradeIntent,
)
from src.config.settings import Settings  # noqa: E402
from src.orchestration.allocator import Allocator  # noqa: E402
from src.orchestration.loop import TradingLoop  # noqa: E402
from src.portfolio.reconcile import Reconciler  # noqa: E402
from src.portfolio.state import PortfolioState  # noqa: E402


# ── Phase 0 stubs ──────────────────────────────────────────────────

class StubBroker:
    """In-memory paper broker for Phase 0."""

    def __init__(self, equity: Decimal = Decimal("100000")) -> None:
        self._account = Account(
            equity=equity,
            cash=equity,
            buying_power=equity,
        )
        self._positions: list[Position] = []
        self._orders: list[Any] = []

    def get_account(self) -> Account:
        return self._account

    def list_positions(self) -> list[Position]:
        return list(self._positions)

    def submit_order(self, intent: TradeIntent):
        from src.brokers.models import Order

        now = datetime.now(timezone.utc)
        order = Order(
            broker_order_id=f"stub-{intent.client_order_id[:8]}",
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            qty=intent.qty,
            filled_qty=intent.qty,
            avg_fill_price=Decimal("100"),
            status=OrderStatus.FILLED,
            submitted_at=now,
            updated_at=now,
        )
        self._orders.append(order)
        return order


class StubRiskGate:
    """Permissive risk gate for Phase 0 — approves everything."""

    def evaluate(
        self,
        proposal,
        *,
        account: Account,
        positions: list[Position],
        quote: Quote,
        session: SessionState,
    ) -> RiskDecision:
        return RiskDecision(
            status=RiskStatus.APPROVE,
            approved_qty=proposal.qty,
            reasons=[],
            checks_passed=["phase0_stub"],
            checks_failed=[],
        )


class StubStrategy:
    """Simple strategy: BUY if price > 0 (Phase 0 wiring test)."""

    id: str = "stub_v1"

    def evaluate(self, features: FeatureVector, context: Any) -> StrategySignal:
        close = features.values.get("close", 0.0)
        side_str = "BUY" if close > 0 else "HOLD"
        from src.brokers.models import SignalSide

        return StrategySignal(
            strategy_id=self.id,
            symbol=features.symbol,
            side=SignalSide(side_str),
            strength=0.6,
            horizon="swing",
            rationale="stub strategy",
            as_of=features.as_of,
            features_used=["close"],
        )


def _make_fake_quote(symbol: str, price: Decimal) -> Quote:
    now = datetime.now(timezone.utc)
    return Quote(
        symbol=symbol,
        bid=price - Decimal("0.01"),
        ask=price + Decimal("0.01"),
        last=price,
        ts=now,
        received_at=now,
        source="stub",
    )


def _make_fake_bars(symbol: str, price: Decimal) -> list[Bar]:
    now = datetime.now(timezone.utc)
    return [
        Bar(
            symbol=symbol,
            timeframe="1d",
            ts_open=now,
            ts_close=now,
            open=price,
            high=price + Decimal("1"),
            low=price - Decimal("1"),
            close=price,
            volume=Decimal("1000000"),
            source="stub",
        )
    ]


def _feature_builder(symbol, bars, quote, news) -> FeatureVector:
    close = float(quote.last) if quote.last else 0.0
    return FeatureVector(
        symbol=symbol,
        as_of=datetime.now(timezone.utc),
        values={"close": close, "returns_1d": 0.01},
        meta={"source": "stub"},
    )


def _audit_sink(record: AuditRecord) -> None:
    # In Phase 0, just print
    print(f"[AUDIT] {record.timestamp.isoformat()} {record.symbol} {record.decision}")


# ── Main ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the trading agent (Phase 0).")
    parser.add_argument(
        "--tickers",
        type=str,
        default="SPY,AAPL,MSFT,NVDA",
        help="Comma-separated ticker list (default: SPY,AAPL,MSFT,NVDA)",
    )
    parser.add_argument(
        "--broker",
        type=str,
        default="paper",
        choices=["paper", "alpaca", "robinhood"],
        help="Broker backend (default: paper)",
    )
    parser.add_argument(
        "--llm-disabled",
        action="store_true",
        help="Disable LLM research note",
    )
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    # Load settings and override
    settings = Settings()
    settings = settings.model_copy(
        updates={
            "symbol_allowlist": tickers,
            "broker": "paper" if args.broker == "paper" else settings.broker,
            "llm_enabled": not args.llm_disabled,
        }
    )

    print(f"=== Trading Agent (Phase 0) ===")
    print(f"Broker: {args.broker}")
    print(f"Tickers: {tickers}")
    print(f"LLM enabled: {settings.llm_enabled}")
    print()

    # Build stubs
    broker = StubBroker()
    risk_gate = StubRiskGate()
    strategy_registry = {"stub_v1": StubStrategy()}
    portfolio_state = PortfolioState(
        cash=broker.get_account().cash,
        session_start_equity=broker.get_account().equity,
    )

    # Fake market data
    quotes = {sym: _make_fake_quote(sym, Decimal("100")) for sym in tickers}
    bars = {sym: _make_fake_bars(sym, Decimal("100")) for sym in tickers}
    news: list = []

    loop = TradingLoop(
        settings=settings,
        broker=broker,
        risk_gate=risk_gate,
        strategy_registry=strategy_registry,
        feature_builder=_feature_builder,
        audit_logger=_audit_sink,
        portfolio_state=portfolio_state,
        llm_synthesizer=None,
    )

    records = loop.run_once(quotes=quotes, bars=bars, news=news)

    print(f"\n=== Results: {len(records)} audit records ===")
    for rec in records:
        try:
            d = rec.model_dump(mode="json")
            print(json.dumps(d, default=str, indent=2))
        except Exception:
            print(f"  {rec.timestamp} {rec.symbol} {rec.decision}")


if __name__ == "__main__":
    main()
