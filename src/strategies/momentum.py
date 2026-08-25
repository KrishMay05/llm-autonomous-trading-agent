"""Trend-Pullback v1 — first deterministic strategy.

Long-biased trend-following with a mean-reversion entry trigger:

* **Bias**: price above the long SMA (200d) → long-only regime.
* **Entry**: RSI recovered from oversold (< ``rsi_oversold``) **and** price
  pulling back toward the intermediate SMA (50d).  Volume ratio > 1 adds
  confirmation strength.
* **Exit / SELL**: RSI overbought (> ``rsi_overbought``) or price breaks below
  the intermediate SMA.
* **Else**: HOLD.

Strength is additive from how many conditions fired, clamped to ``[0, 1]``.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from src.brokers.models import FeatureVector, SignalSide, StrategySignal
from src.strategies.base import StrategyContext


class TrendPullbackV1:
    """Trend-pullback strategy — long-biased trend follow with RSI entry.

    All thresholds are constructor-configurable so the same class can be
    tuned from settings or backtest sweeps without code changes.
    """

    id: str = "trend_pullback_v1"

    def __init__(
        self,
        *,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 70.0,
        sma_long_key: str = "sma_200",
        sma_int_key: str = "sma_50",
        rsi_key: str = "rsi_14",
        volume_ratio_key: str = "volume_ratio_20",
        close_key: str = "close",
        pullback_tolerance: float = 0.02,
    ) -> None:
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.sma_long_key = sma_long_key
        self.sma_int_key = sma_int_key
        self.rsi_key = rsi_key
        self.volume_ratio_key = volume_ratio_key
        self.close_key = close_key
        self.pullback_tolerance = pullback_tolerance

    # ── helpers ────────────────────────────────────────────────────
    @staticmethod
    def _is_nan(x: float) -> bool:
        return x != x if isinstance(x, float) else math.isnan(x)

    def _get(self, features: FeatureVector, key: str) -> float:
        return float(features.values.get(key, float("nan")))

    # ── main ───────────────────────────────────────────────────────
    def evaluate(self, features: FeatureVector, context: StrategyContext) -> StrategySignal:
        close = self._get(features, self.close_key)
        sma_long = self._get(features, self.sma_long_key)
        sma_int = self._get(features, self.sma_int_key)
        rsi = self._get(features, self.rsi_key)
        vol_ratio = self._get(features, self.volume_ratio_key)

        features_used: list[str] = [
            self.close_key,
            self.sma_long_key,
            self.sma_int_key,
            self.rsi_key,
            self.volume_ratio_key,
        ]

        now = datetime.now(timezone.utc)

        # ── NaN guard: HOLD when inputs are missing ──────────────────
        if any(self._is_nan(v) for v in (close, sma_long, sma_int, rsi, vol_ratio)):
            return StrategySignal(
                strategy_id=self.id,
                symbol=features.symbol,
                side=SignalSide.HOLD,
                strength=0.0,
                horizon="swing",
                rationale="HOLD: one or more feature values are NaN/missing.",
                as_of=now,
                features_used=features_used,
            )

        rationale_parts: list[str] = []

        # ── Long-bias gate: must be above long SMA to be in regime ─────
        # SELL exits only make sense when we're in a long regime; if we're
        # below the long SMA there's nothing to exit → HOLD.
        if sma_long <= 0 or close <= sma_long:
            return StrategySignal(
                strategy_id=self.id,
                symbol=features.symbol,
                side=SignalSide.HOLD,
                strength=0.0,
                horizon="swing",
                rationale=(
                    f"HOLD: close {close:.2f} not above {self.sma_long_key} "
                    f"{sma_long:.2f} — no long regime."
                ),
                as_of=now,
                features_used=features_used,
            )

        # ── SELL: overbought mean-reversion exit ────────────────────
        if rsi > self.rsi_overbought:
            rationale_parts.append(
                f"RSI {rsi:.1f} > {self.rsi_overbought} (overbought exit)"
            )
            return StrategySignal(
                strategy_id=self.id,
                symbol=features.symbol,
                side=SignalSide.SELL,
                strength=min(1.0, 0.3 + (0.7 * min(1.0, (rsi - self.rsi_overbought) / 30.0))),
                horizon="swing",
                rationale="SELL: " + "; ".join(rationale_parts),
                as_of=now,
                features_used=features_used,
            )

        # ── SELL: broke below intermediate MA (while in long regime) ──
        if close < sma_int:
            rationale_parts.append(f"close {close:.2f} < {self.sma_int_key} {sma_int:.2f}")
            return StrategySignal(
                strategy_id=self.id,
                symbol=features.symbol,
                side=SignalSide.SELL,
                strength=0.5,
                horizon="swing",
                rationale="SELL: " + "; ".join(rationale_parts),
                as_of=now,
                features_used=features_used,
            )

        # ── BUY path: in long regime, check entry conditions ────────
        strength = 0.3  # base: in long regime
        rationale_parts.append(f"close {close:.2f} > {self.sma_long_key} {sma_long:.2f} (long regime)")

        rsi_condition = rsi < self.rsi_oversold
        pullback_condition = abs(close - sma_int) <= self.pullback_tolerance * sma_int if sma_int > 0 else False
        volume_condition = vol_ratio > 1.0

        if rsi_condition:
            strength += 0.3
            rationale_parts.append(f"RSI {rsi:.1f} < {self.rsi_oversold} (oversold entry)")
        if pullback_condition:
            strength += 0.2
            rationale_parts.append(
                f"close {close:.2f} near {self.sma_int_key} {sma_int:.2f} (pullback)"
            )
        if volume_condition:
            strength += 0.2
            rationale_parts.append(
                f"volume_ratio {vol_ratio:.2f} > 1.0 (confirmation)"
            )

        strength = min(1.0, strength)

        # If neither RSI nor pullback fired, no real entry trigger → HOLD
        if not (rsi_condition or pullback_condition):
            return StrategySignal(
                strategy_id=self.id,
                symbol=features.symbol,
                side=SignalSide.HOLD,
                strength=0.3,
                horizon="swing",
                rationale="HOLD: " + "; ".join(rationale_parts),
                as_of=now,
                features_used=features_used,
            )

        rationale_parts.append(f"strength={strength:.2f}")
        return StrategySignal(
            strategy_id=self.id,
            symbol=features.symbol,
            side=SignalSide.BUY,
            strength=strength,
            horizon="swing",
            rationale="BUY: " + "; ".join(rationale_parts),
            as_of=now,
            features_used=features_used,
        )
