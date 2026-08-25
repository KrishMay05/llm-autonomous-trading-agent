"""Strategy registry — maps strategy ids to instantiated strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.brokers.models import FeatureVector, StrategySignal
from src.strategies.base import Strategy, StrategyContext

if TYPE_CHECKING:
    from src.config.settings import Settings


# Built-in strategy factories keyed by id.
_BUILTIN_FACTORIES: dict[str, type[Strategy]] = {}


def _register_builtins() -> None:
    from src.strategies.momentum import TrendPullbackV1
    from src.strategies.stub import HoldStrategy

    _BUILTIN_FACTORIES.clear()
    _BUILTIN_FACTORIES["trend_pullback_v1"] = TrendPullbackV1  # type: ignore[assignment]
    _BUILTIN_FACTORIES["hold"] = HoldStrategy  # type: ignore[assignment]


class StrategyRegistry:
    """Registry of strategy id → instantiated ``Strategy``.

    Built-ins ("trend_pullback_v1", "hold") are available by default; extra
    strategies can be registered at runtime.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}

    def register(self, strategy_id: str, strategy_class: type[Strategy]) -> None:
        """Register a strategy class under ``strategy_id`` and instantiate it."""
        self._strategies[strategy_id] = strategy_class()

    def get(self, strategy_id: str) -> Strategy:
        """Return the strategy registered under ``strategy_id``.

        Raises:
            KeyError: if ``strategy_id`` is not registered.
        """
        try:
            return self._strategies[strategy_id]
        except KeyError:
            raise KeyError(
                f"Strategy '{strategy_id}' not registered. "
                f"Available: {list(self._strategies)}"
            ) from None

    def get_all(self) -> dict[str, Strategy]:
        """Return a copy of all registered strategies keyed by id."""
        return dict(self._strategies)

    def evaluate_all(
        self, features: FeatureVector, context: StrategyContext
    ) -> list[StrategySignal]:
        """Evaluate every registered strategy and return all signals."""
        return [s.evaluate(features, context) for s in self._strategies.values()]

    # ── factory ───────────────────────────────────────────────────
    @classmethod
    def from_settings(cls, settings: "Settings") -> "StrategyRegistry":
        """Build a registry from ``settings.strategies`` (list of ids).

        Unknown ids raise ``KeyError``.  Built-ins are registered first.
        """
        _register_builtins()
        registry = cls()
        # Strategy ids are case-insensitive from settings (validator uppercases).
        lowered = {k.lower(): v for k, v in _BUILTIN_FACTORIES.items()}
        for sid in settings.strategies:
            key = sid.lower()
            if key not in lowered:
                raise KeyError(
                    f"Strategy '{sid}' in settings is not a known built-in. "
                    f"Known: {list(_BUILTIN_FACTORIES)}"
                )
            registry.register(key, lowered[key])
        return registry


# Eagerly populate built-ins on import so ``from_settings`` is ready.
_register_builtins()
