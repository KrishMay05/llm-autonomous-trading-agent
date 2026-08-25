"""Tests for the HardRiskGate — one per reason code + resize + sell bypass."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.models import (
    Account,
    Position,
    Quote,
    RiskStatus,
    SessionState,
    TradeProposal,
)
from src.config.settings import Settings
from src.risk.circuit_breakers import CircuitBreaker
from src.risk.limits import HardRiskGate

UTC = timezone.utc
NOW = datetime(2026, 1, 15, 14, 30, 0, tzinfo=UTC)


# ── fixtures ─────────────────────────────────────────────────────
def _settings(**overrides) -> Settings:
    kwargs: dict = dict(
        symbol_allowlist=["SPY", "AAPL", "MSFT", "NVDA"],
        max_position_pct=Decimal("0.10"),
        max_portfolio_heat_pct=Decimal("0.40"),
        max_daily_loss_pct=Decimal("0.02"),
        max_orders_per_day=20,
        max_quote_age_sec=120,
        kill_switch=False,
        pdt_guard_enabled=False,
    )
    kwargs.update(overrides)
    return Settings(**kwargs)


def _account(equity: str = "100000") -> Account:
    return Account(
        equity=Decimal(equity),
        cash=Decimal(equity),
        buying_power=Decimal(equity),
        pattern_day_trader=False,
    )


def _quote(symbol: str = "SPY", last: str | None = "100", age_sec: int = 0) -> Quote:
    real_now = datetime.now(UTC)
    return Quote(
        symbol=symbol,
        bid=Decimal("99.9"),
        ask=Decimal("100.1"),
        last=Decimal(last) if last is not None else None,
        ts=real_now - timedelta(seconds=age_sec),
        received_at=real_now - timedelta(seconds=age_sec),
        source="test",
    )


def _session(orders_today: int = 0, realized_pnl: str = "0") -> SessionState:
    return SessionState(
        date=datetime.now(UTC).date(),
        orders_today=orders_today,
        realized_pnl=Decimal(realized_pnl),
        session_start_equity=Decimal("100000"),
    )


def _proposal(
    symbol: str = "SPY",
    side: str = "buy",
    qty: str = "10",
    strength: float = 0.5,
) -> TradeProposal:
    return TradeProposal(
        symbol=symbol,
        side=side,
        qty=Decimal(qty),
        order_type="market",
        strategy_id="test",
        signal_strength=strength,
        rationale="test",
    )


# ── individual reason codes ─────────────────────────────────────
def test_allowlist_reject():
    gate = HardRiskGate(_settings())
    dec = gate.evaluate(
        _proposal(symbol="XYZ"),
        account=_account(),
        positions=[],
        quote=_quote("XYZ"),
        session=_session(),
    )
    assert dec.status == RiskStatus.REJECT
    assert "ALLOWLIST" in dec.reasons


def test_kill_switch_rejects_buy():
    gate = HardRiskGate(_settings(kill_switch=True))
    dec = gate.evaluate(
        _proposal(side="buy"),
        account=_account(),
        positions=[],
        quote=_quote(),
        session=_session(),
    )
    assert dec.status == RiskStatus.REJECT
    assert "KILL_SWITCH" in dec.reasons


def test_kill_switch_allows_sell():
    gate = HardRiskGate(_settings(kill_switch=True))
    dec = gate.evaluate(
        _proposal(side="sell"),
        account=_account(),
        positions=[],
        quote=_quote(),
        session=_session(),
    )
    assert dec.status == RiskStatus.APPROVE
    assert "KILL_SWITCH" not in dec.reasons


def test_stale_data_reject():
    gate = HardRiskGate(_settings(max_quote_age_sec=120))
    dec = gate.evaluate(
        _proposal(),
        account=_account(),
        positions=[],
        quote=_quote(age_sec=300),
        session=_session(),
    )
    assert dec.status == RiskStatus.REJECT
    assert "STALE_DATA" in dec.reasons


def test_missing_quote_reject():
    gate = HardRiskGate(_settings())
    dec = gate.evaluate(
        _proposal(),
        account=_account(),
        positions=[],
        quote=_quote(last=None),
        session=_session(),
    )
    assert dec.status == RiskStatus.REJECT
    assert "MISSING_QUOTE" in dec.reasons


def test_invalid_qty_reject():
    gate = HardRiskGate(_settings())
    dec = gate.evaluate(
        _proposal(qty="0"),
        account=_account(),
        positions=[],
        quote=_quote(),
        session=_session(),
    )
    assert dec.status == RiskStatus.REJECT
    assert "INVALID_QTY" in dec.reasons


def test_max_position_resize():
    """Buying 200 shares @100 = 20k notional, max_position = 10% * 100k = 10k.
    Exceeds MAX_POSITION but stays under HEAT cap (40% * 100k = 40k) → RESIZE.
    """
    gate = HardRiskGate(_settings(max_position_pct=Decimal("0.10")))
    dec = gate.evaluate(
        _proposal(qty="200"),
        account=_account(equity="100000"),
        positions=[],
        quote=_quote(last="100"),
        session=_session(),
    )
    assert dec.status == RiskStatus.RESIZE
    assert "MAX_POSITION" in dec.reasons
    # 10% of 100k = 10000 / 100 = 100 shares
    assert dec.approved_qty == Decimal("100")


def test_daily_loss_reject():
    """realized_pnl = -3000 on 100k start = -3% > 2% limit → reject."""
    gate = HardRiskGate(_settings(max_daily_loss_pct=Decimal("0.02")))
    dec = gate.evaluate(
        _proposal(),
        account=_account(),
        positions=[],
        quote=_quote(),
        session=_session(realized_pnl="-3000"),
    )
    assert dec.status == RiskStatus.REJECT
    assert "DAILY_LOSS" in dec.reasons


def test_max_orders_reject():
    gate = HardRiskGate(_settings(max_orders_per_day=20))
    dec = gate.evaluate(
        _proposal(),
        account=_account(),
        positions=[],
        quote=_quote(),
        session=_session(orders_today=20),
    )
    assert dec.status == RiskStatus.REJECT
    assert "MAX_ORDERS" in dec.reasons


def test_heat_reject():
    """Existing positions worth 50k; buying another 50k pushes past 40k heat cap."""
    gate = HardRiskGate(_settings(max_portfolio_heat_pct=Decimal("0.40")))
    positions = [
        Position(symbol="AAPL", qty=Decimal("500"), avg_price=Decimal("100"),
                 market_value=Decimal("50000")),
    ]
    dec = gate.evaluate(
        _proposal(qty="600"),
        account=_account(equity="100000"),
        positions=positions,
        quote=_quote(last="100"),
        session=_session(),
    )
    assert dec.status == RiskStatus.REJECT
    assert "HEAT" in dec.reasons


def test_all_checks_pass():
    gate = HardRiskGate(_settings())
    dec = gate.evaluate(
        _proposal(qty="10"),
        account=_account(),
        positions=[],
        quote=_quote(),
        session=_session(),
    )
    assert dec.status == RiskStatus.APPROVE
    assert dec.approved_qty == Decimal("10")
    assert dec.reasons == []


def test_sell_bypasses_daily_loss():
    """Sell should be approved even when daily loss is exceeded."""
    gate = HardRiskGate(_settings(max_daily_loss_pct=Decimal("0.02")))
    dec = gate.evaluate(
        _proposal(side="sell"),
        account=_account(),
        positions=[
            Position(symbol="SPY", qty=Decimal("10"), avg_price=Decimal("100")),
        ],
        quote=_quote(),
        session=_session(realized_pnl="-5000"),
    )
    assert dec.status == RiskStatus.APPROVE
    assert "DAILY_LOSS" not in dec.reasons


def test_pdt_reject():
    """PDT guard + PDT flag + equity < 25k → reject."""
    gate = HardRiskGate(_settings(pdt_guard_enabled=True))
    dec = gate.evaluate(
        _proposal(),
        account=_account(equity="15000"),
        # override pattern_day_trader via direct construction
        positions=[],
        quote=_quote(),
        session=_session(),
    )
    # need to inject pattern_day_trader=True
    account = Account(
        equity=Decimal("15000"),
        cash=Decimal("15000"),
        buying_power=Decimal("15000"),
        pattern_day_trader=True,
    )
    dec = gate.evaluate(
        _proposal(),
        account=account,
        positions=[],
        quote=_quote(),
        session=_session(),
    )
    assert dec.status == RiskStatus.REJECT
    assert "PDT" in dec.reasons
