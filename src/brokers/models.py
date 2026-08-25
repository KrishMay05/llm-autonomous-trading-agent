"""Shared domain models — Pydantic v2.

These are the canonical contracts shared across all modules.
See notes/DOMAIN_MODELS.md for the authoritative spec.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict


# ── Frozen base for immutable models ──────────────────────────────
class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


# ── Enums ────────────────────────────────────────────────────────
class SignalSide(str, Enum):
    HOLD = "HOLD"
    BUY = "BUY"
    SELL = "SELL"
    REDUCE = "REDUCE"


class OrderStatus(str, Enum):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskStatus(str, Enum):
    APPROVE = "APPROVE"
    RESIZE = "RESIZE"
    REJECT = "REJECT"


# ── Market data ──────────────────────────────────────────────────
class Bar(_Frozen):
    symbol: str
    timeframe: str
    ts_open: datetime
    ts_close: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source: str = ""


class Quote(_Frozen):
    symbol: str
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal | None = None
    ts: datetime
    received_at: datetime
    source: str = ""


class NewsItem(_Frozen):
    id: str
    symbol: str | None = None
    headline: str
    published_at: datetime
    url: str | None = None
    source: str = ""


# ── Features & strategy ─────────────────────────────────────────
class FeatureVector(_Frozen):
    symbol: str
    as_of: datetime
    values: dict[str, float]
    meta: dict[str, str] = {}


class StrategySignal(_Frozen):
    strategy_id: str
    symbol: str
    side: SignalSide
    strength: float
    horizon: str = "swing"
    rationale: str = ""
    as_of: datetime
    features_used: list[str] = []


# ── LLM research ─────────────────────────────────────────────────
class ResearchNote(_Frozen):
    as_of: datetime
    regime: Literal["risk_on", "risk_off", "mixed", "unknown"] = "unknown"
    notes: str = ""
    symbol_notes: dict[str, str] = {}
    proposed_veto_symbols: list[str] = []
    model: str = ""
    prompt_version: str = ""
    cost_usd: Decimal | None = None


# ── Risk & intents ───────────────────────────────────────────────
class TradeProposal(_Frozen):
    symbol: str
    side: Literal["buy", "sell"]
    qty: Decimal
    order_type: Literal["market", "limit"] = "market"
    limit_price: Decimal | None = None
    strategy_id: str = ""
    signal_strength: float = 0.0
    rationale: str = ""


class RiskDecision(_Frozen):
    status: RiskStatus
    approved_qty: Decimal = Decimal("0")
    reasons: list[str] = []
    checks_passed: list[str] = []
    checks_failed: list[str] = []


class TradeIntent(_Frozen):
    client_order_id: str
    symbol: str
    side: Literal["buy", "sell"]
    qty: Decimal
    order_type: str = "market"
    limit_price: Decimal | None = None
    time_in_force: str = "day"
    strategy_id: str = ""
    risk_decision: RiskDecision
    rationale: str = ""
    created_at: datetime


# ── Broker models ───────────────────────────────────────────────
class Order(_Frozen):
    broker_order_id: str | None = None
    client_order_id: str
    symbol: str
    side: str
    qty: Decimal
    filled_qty: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    status: OrderStatus = OrderStatus.SUBMITTED
    submitted_at: datetime
    updated_at: datetime
    raw: dict | None = None


class Fill(_Frozen):
    order_client_id: str
    qty: Decimal
    price: Decimal
    ts: datetime
    fee: Decimal = Decimal("0")


class Position(_Frozen):
    symbol: str
    qty: Decimal
    avg_price: Decimal = Decimal("0")
    market_value: Decimal | None = None


class Account(_Frozen):
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    currency: str = "USD"
    pattern_day_trader: bool | None = None


# ── Session state ────────────────────────────────────────────────
class SessionState(_Frozen):
    date: datetime
    orders_today: int = 0
    realized_pnl: Decimal = Decimal("0")
    session_start_equity: Decimal = Decimal("0")


# ── Audit ───────────────────────────────────────────────────────
class AuditRecord(_Frozen):
    timestamp: datetime
    symbol: str
    decision: Literal["BUY", "SELL", "HOLD", "REJECT"]
    strategy_signal: dict | None = None
    llm_research: dict | None = None
    risk_gate: dict | None = None
    action: dict | None = None
    execution: dict | None = None
    inputs_digest: str = ""
