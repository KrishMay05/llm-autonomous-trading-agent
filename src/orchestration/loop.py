"""Trading loop — single-iteration control flow.

Dependencies are injected for testability:
- ``broker``: any object with ``get_account``, ``list_positions``, ``submit_order``
- ``risk_gate``: any object with ``evaluate(proposal, *, account, positions, quote, session)``
- ``strategy_registry``: dict-like ``{strategy_id: Strategy}`` where Strategy has ``evaluate(features, context) -> StrategySignal``
- ``feature_builder``: callable ``(symbol, bars, quote, news) -> FeatureVector``
- ``audit_logger``: callable ``(AuditRecord) -> None``
- ``llm_synthesizer``: optional callable ``(signals, features, news) -> ResearchNote | None``
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Protocol, Sequence

from src.brokers.models import (
    Account,
    AuditRecord,
    Bar,
    FeatureVector,
    NewsItem,
    Order,
    Position,
    Quote,
    ResearchNote,
    RiskDecision,
    RiskStatus,
    SessionState,
    StrategySignal,
    TradeIntent,
    TradeProposal,
)
from src.config.settings import Settings
from src.orchestration.allocator import Allocator
from src.portfolio.reconcile import Reconciler
from src.portfolio.state import PortfolioState


# ── Protocols (structural typing for injected deps) ────────────────

class BrokerLike(Protocol):
    def get_account(self) -> Account: ...
    def list_positions(self) -> list[Position]: ...
    def submit_order(self, intent: TradeIntent) -> Order: ...


class RiskGateLike(Protocol):
    def evaluate(
        self,
        proposal: TradeProposal,
        *,
        account: Account,
        positions: list[Position],
        quote: Quote,
        session: SessionState,
    ) -> RiskDecision: ...


class StrategyLike(Protocol):
    id: str
    def evaluate(self, features: FeatureVector, context: Any) -> StrategySignal: ...


# Calendar stub — replace with src/calendar when available
class _CalendarStub:
    def is_trading_day(self, dt: datetime) -> bool:
        return True  # Phase 0: always tradable


# ── Helpers ───────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _audit_decision(
    decision: str,
    symbol: str,
    *,
    strategy_signal: dict | None = None,
    llm_research: dict | None = None,
    risk_gate: dict | None = None,
    action: dict | None = None,
    execution: dict | None = None,
) -> AuditRecord:
    return AuditRecord(
        timestamp=_now_utc(),
        symbol=symbol,
        decision=decision,  # type: ignore[arg-type]
        strategy_signal=strategy_signal,
        llm_research=llm_research,
        risk_gate=risk_gate,
        action=action,
        execution=execution,
        inputs_digest="",
    )


# ── TradingLoop ─────────────────────────────────────────────────────

class TradingLoop:
    """Single-iteration control loop for the trading agent."""

    def __init__(
        self,
        *,
        settings: Settings,
        broker: BrokerLike,
        risk_gate: RiskGateLike,
        strategy_registry: dict[str, StrategyLike],
        feature_builder: Callable[..., FeatureVector],
        audit_logger: Callable[[AuditRecord], None],
        portfolio_state: PortfolioState,
        llm_synthesizer: Callable[..., ResearchNote | None] | None = None,
        calendar: Any | None = None,
        allocator: Allocator | None = None,
        reconciler: Reconciler | None = None,
    ) -> None:
        self.settings = settings
        self.broker = broker
        self.risk_gate = risk_gate
        self.strategy_registry = strategy_registry
        self.feature_builder = feature_builder
        self.audit_logger = audit_logger
        self.portfolio_state = portfolio_state
        self.llm_synthesizer = llm_synthesizer
        self.calendar = calendar or _CalendarStub()
        self.allocator = allocator or Allocator()
        self.reconciler = reconciler or Reconciler()
        self._reconciled_ok = True

    def run_once(
        self,
        quotes: dict[str, Quote],
        bars: dict[str, list[Bar]],
        news: list[NewsItem],
    ) -> list[AuditRecord]:
        """Execute one iteration of the control loop.

        Returns the list of audit records produced.
        """
        records: list[AuditRecord] = []

        # ── Step a: check if session is tradable ───────────────────
        now = _now_utc()
        if not self.calendar.is_trading_day(now):
            rec = _audit_decision(
                "HOLD",
                "_SESSION",
                action={"reason": "not a trading day"},
            )
            records.append(rec)
            self.audit_logger(rec)
            return records

        # ── Step b: reconcile with broker ───────────────────────────
        account = self.broker.get_account()
        broker_positions = self.broker.list_positions()
        recon = self.reconciler.reconcile(
            self.portfolio_state, broker_positions, account,
        )
        if not recon.matched:
            self._reconciled_ok = False
            for msg in recon.mismatches:
                rec = _audit_decision(
                    "REJECT",
                    "_RECONCILE",
                    risk_gate={"reconcile_mismatch": msg},
                )
                records.append(rec)
                self.audit_logger(rec)
            # Fail closed: skip new orders this iteration
            return records
        # Sync local state
        self.portfolio_state.update_from_reconcile(broker_positions, account)

        # ── Step c: build features + evaluate strategies ───────────
        signals: list[StrategySignal] = []
        allowlist = [s.upper() for s in self.settings.symbol_allowlist]
        for symbol in allowlist:
            sym_bars = bars.get(symbol, [])
            sym_quote = quotes.get(symbol)
            if sym_quote is None:
                continue  # skip symbols without quotes
            features = self.feature_builder(
                symbol=symbol,
                bars=sym_bars,
                quote=sym_quote,
                news=news,
            )
            for strat_id, strategy in self.strategy_registry.items():
                ctx = {
                    "account": account,
                    "position": self.portfolio_state.get_position(symbol),
                    "research_note": None,
                }
                signal = strategy.evaluate(features, ctx)
                signals.append(signal)

        # ── Step d: optional LLM research note ─────────────────────
        research_note: ResearchNote | None = None
        if self.settings.llm_enabled and self.llm_synthesizer is not None:
            research_note = self.llm_synthesizer(
                signals=signals,
                features=None,
                news=news,
            )

        # ── Step e: allocate ────────────────────────────────────────
        proposals = self.allocator.allocate(
            signals=signals,
            account=account,
            positions=broker_positions,
            research_note=research_note,
            settings=self.settings,
        )

        # ── Step f: risk gate + submit ──────────────────────────────
        session = self.portfolio_state.to_session_state()
        llm_dict = research_note.model_dump() if research_note else None

        for proposal in proposals:
            sym_quote = quotes.get(proposal.symbol)
            if sym_quote is None:
                # Cannot risk-check without a quote
                rec = _audit_decision(
                    "REJECT",
                    proposal.symbol,
                    strategy_signal={
                        "strategy_id": proposal.strategy_id,
                        "side": proposal.side,
                        "strength": proposal.signal_strength,
                    },
                    llm_research=llm_dict,
                    risk_gate={"reason": "MISSING_QUOTE"},
                )
                records.append(rec)
                self.audit_logger(rec)
                continue

            decision = self.risk_gate.evaluate(
                proposal,
                account=account,
                positions=broker_positions,
                quote=sym_quote,
                session=session,
            )

            sig_dict = {
                "strategy_id": proposal.strategy_id,
                "side": proposal.side,
                "strength": proposal.signal_strength,
                "qty": str(proposal.qty),
            }

            if decision.status == RiskStatus.APPROVE and decision.approved_qty > 0:
                # Create intent and submit
                intent = TradeIntent(
                    client_order_id=str(uuid.uuid4()),
                    symbol=proposal.symbol,
                    side=proposal.side,  # type: ignore[arg-type]
                    qty=decision.approved_qty,
                    order_type=proposal.order_type,
                    limit_price=proposal.limit_price,
                    time_in_force="day",
                    strategy_id=proposal.strategy_id,
                    risk_decision=decision,
                    rationale=proposal.rationale,
                    created_at=_now_utc(),
                )
                order = self.broker.submit_order(intent)

                action_dict = {
                    "client_order_id": intent.client_order_id,
                    "side": intent.side,
                    "qty": str(intent.qty),
                    "order_type": intent.order_type,
                }
                exec_dict = {
                    "broker_order_id": order.broker_order_id,
                    "status": order.status.value,
                    "filled_qty": str(order.filled_qty),
                }

                rec = _audit_decision(
                    "BUY" if proposal.side == "buy" else "SELL",
                    proposal.symbol,
                    strategy_signal=sig_dict,
                    llm_research=llm_dict,
                    risk_gate=decision.model_dump(),
                    action=action_dict,
                    execution=exec_dict,
                )
            elif decision.status == RiskStatus.RESIZE and decision.approved_qty > 0:
                # Resized: submit the resized qty
                intent = TradeIntent(
                    client_order_id=str(uuid.uuid4()),
                    symbol=proposal.symbol,
                    side=proposal.side,  # type: ignore[arg-type]
                    qty=decision.approved_qty,
                    order_type=proposal.order_type,
                    limit_price=proposal.limit_price,
                    time_in_force="day",
                    strategy_id=proposal.strategy_id,
                    risk_decision=decision,
                    rationale=f"resized: {proposal.rationale}",
                    created_at=_now_utc(),
                )
                order = self.broker.submit_order(intent)

                rec = _audit_decision(
                    "BUY" if proposal.side == "buy" else "SELL",
                    proposal.symbol,
                    strategy_signal=sig_dict,
                    llm_research=llm_dict,
                    risk_gate=decision.model_dump(),
                    action={
                        "client_order_id": intent.client_order_id,
                        "side": intent.side,
                        "qty": str(intent.qty),
                        "resized": True,
                    },
                    execution={
                        "broker_order_id": order.broker_order_id,
                        "status": order.status.value,
                    },
                )
            else:
                # Rejected
                rec = _audit_decision(
                    "REJECT",
                    proposal.symbol,
                    strategy_signal=sig_dict,
                    llm_research=llm_dict,
                    risk_gate=decision.model_dump(),
                )

            records.append(rec)
            self.audit_logger(rec)

        return records
