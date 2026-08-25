"""HoldStrategy — trivial always-HOLD strategy for wiring tests."""

from __future__ import annotations

from datetime import datetime, timezone

from src.brokers.models import FeatureVector, SignalSide, StrategySignal
from src.strategies.base import StrategyContext


class HoldStrategy:
    """Always returns a HOLD signal — useful for wiring / integration tests."""

    id: str = "hold"

    def evaluate(self, features: FeatureVector, context: StrategyContext) -> StrategySignal:
        return StrategySignal(
            strategy_id=self.id,
            symbol=features.symbol,
            side=SignalSide.HOLD,
            strength=0.0,
            horizon="swing",
            rationale="HOLD: hold strategy always holds.",
            as_of=datetime.now(timezone.utc),
            features_used=[],
        )
