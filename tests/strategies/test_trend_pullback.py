"""Tests for TrendPullbackV1 strategy."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from src.brokers.models import FeatureVector, SignalSide
from src.strategies.base import StrategyContext
from src.strategies.momentum import TrendPullbackV1


# ── helpers ────────────────────────────────────────────────────────
NOW = datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc)


def _fv(symbol: str = "AAPL", **values: float) -> FeatureVector:
    return FeatureVector(symbol=symbol, as_of=NOW, values=dict(values))


def _ctx() -> StrategyContext:
    return StrategyContext()


@pytest.fixture
def strategy() -> TrendPullbackV1:
    return TrendPullbackV1()


# ── tests ──────────────────────────────────────────────────────────
class TestTrendPullbackV1:
    def test_buy_signal_when_oversold_pullback(self, strategy: TrendPullbackV1) -> None:
        """Price > sma_200, RSI < 35, near sma_50, vol > 1 → BUY."""
        fv = _fv(
            close=105.0,
            sma_200=100.0,
            sma_50=104.5,  # within 2% tolerance → pullback
            rsi_14=28.0,
            volume_ratio_20=1.5,
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.BUY
        assert signal.strength > 0.3
        assert signal.strategy_id == "trend_pullback_v1"

    def test_hold_when_below_long_sma(self, strategy: TrendPullbackV1) -> None:
        """Price < sma_200 → HOLD (no long regime)."""
        fv = _fv(
            close=95.0,
            sma_200=100.0,
            sma_50=96.0,
            rsi_14=30.0,
            volume_ratio_20=1.2,
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.HOLD
        assert signal.strength == 0.0

    def test_sell_on_overbought(self, strategy: TrendPullbackV1) -> None:
        """RSI > 70 → SELL."""
        fv = _fv(
            close=110.0,
            sma_200=100.0,
            sma_50=105.0,
            rsi_14=75.0,
            volume_ratio_20=1.0,
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.SELL
        assert "overbought" in signal.rationale.lower()

    def test_sell_on_break_of_intermediate(self, strategy: TrendPullbackV1) -> None:
        """Price < sma_50 (but > sma_200, RSI not overbought) → SELL."""
        fv = _fv(
            close=104.0,
            sma_200=100.0,
            sma_50=106.0,  # close < sma_50
            rsi_14=55.0,  # not overbought
            volume_ratio_20=1.0,
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.SELL

    def test_hold_when_no_clear_signal(self, strategy: TrendPullbackV1) -> None:
        """Price > sma_200 but RSI mid-range and no pullback → HOLD."""
        fv = _fv(
            close=110.0,
            sma_200=100.0,
            sma_50=100.0,  # not near → no pullback
            rsi_14=55.0,  # mid-range
            volume_ratio_20=0.9,
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.HOLD

    def test_strength_increases_with_conditions(self, strategy: TrendPullbackV1) -> None:
        """More conditions fired → higher strength."""
        # Only long regime (no RSI, no pullback, no vol)
        base = _fv(
            close=110.0,
            sma_200=100.0,
            sma_50=100.0,
            rsi_14=55.0,
            volume_ratio_20=0.8,
        )
        sig_base = strategy.evaluate(base, _ctx())
        assert sig_base.strength == pytest.approx(0.3)

        # Long regime + RSI oversold + pullback + vol → higher
        full = _fv(
            close=101.0,
            sma_200=100.0,
            sma_50=100.5,  # within 2%
            rsi_14=25.0,
            volume_ratio_20=1.5,
        )
        sig_full = strategy.evaluate(full, _ctx())
        assert sig_full.side == SignalSide.BUY
        assert sig_full.strength > sig_base.strength
        assert sig_full.strength == pytest.approx(1.0)  # 0.3+0.3+0.2+0.2=1.0

    def test_nan_features_hold(self, strategy: TrendPullbackV1) -> None:
        """NaN features → HOLD with strength 0."""
        fv = _fv(
            close=float("nan"),
            sma_200=100.0,
            sma_50=100.0,
            rsi_14=50.0,
            volume_ratio_20=1.0,
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.HOLD
        assert signal.strength == 0.0
        assert "nan" in signal.rationale.lower()

    def test_strategy_id_stable(self, strategy: TrendPullbackV1) -> None:
        """Signal strategy_id is always the stable string."""
        fv = _fv(
            close=105.0,
            sma_200=100.0,
            sma_50=104.5,
            rsi_14=28.0,
            volume_ratio_20=1.5,
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.strategy_id == "trend_pullback_v1"

        # Even for HOLD
        fv_hold = _fv(
            close=90.0,
            sma_200=100.0,
            sma_50=95.0,
            rsi_14=50.0,
            volume_ratio_20=1.0,
        )
        signal_hold = strategy.evaluate(fv_hold, _ctx())
        assert signal_hold.strategy_id == "trend_pullback_v1"

    def test_features_used_listed(self, strategy: TrendPullbackV1) -> None:
        """features_used contains the expected keys."""
        fv = _fv(
            close=105.0,
            sma_200=100.0,
            sma_50=104.5,
            rsi_14=28.0,
            volume_ratio_20=1.5,
        )
        signal = strategy.evaluate(fv, _ctx())
        for key in ("close", "sma_200", "sma_50", "rsi_14", "volume_ratio_20"):
            assert key in signal.features_used, f"{key} not in features_used: {signal.features_used}"

    def test_custom_parameters(self) -> None:
        """Constructor params override defaults."""
        strat = TrendPullbackV1(
            rsi_oversold=40.0,
            rsi_overbought=65.0,
            sma_long_key="sma_100",
            sma_int_key="sma_20",
            rsi_key="rsi_10",
            volume_ratio_key="vol_ratio",
            close_key="px",
        )
        fv = FeatureVector(
            symbol="AAPL",
            as_of=NOW,
            values={
                "px": 105.0,
                "sma_100": 100.0,
                "sma_20": 104.5,
                "rsi_10": 38.0,  # < 40 → oversold with custom threshold
                "vol_ratio": 1.5,
            },
        )
        signal = strat.evaluate(fv, _ctx())
        assert signal.side == SignalSide.BUY
        assert signal.strength == pytest.approx(1.0)

    def test_strength_clamped_to_one(self, strategy: TrendPullbackV1) -> None:
        """Strength never exceeds 1.0 even if all conditions fire strongly."""
        fv = _fv(
            close=100.5,
            sma_200=100.0,
            sma_50=100.4,  # within tolerance
            rsi_14=10.0,  # very oversold
            volume_ratio_20=5.0,  # very high
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.BUY
        assert signal.strength <= 1.0
        assert signal.strength == pytest.approx(1.0)

    def test_all_nan_hold(self, strategy: TrendPullbackV1) -> None:
        """All NaN → HOLD."""
        fv = _fv(
            close=float("nan"),
            sma_200=float("nan"),
            sma_50=float("nan"),
            rsi_14=float("nan"),
            volume_ratio_20=float("nan"),
        )
        signal = strategy.evaluate(fv, _ctx())
        assert signal.side == SignalSide.HOLD
        assert signal.strength == 0.0
        assert not math.isnan(signal.strength)
