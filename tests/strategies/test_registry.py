"""Tests for StrategyRegistry."""

from __future__ import annotations

import pytest

from src.config.settings import Settings
from src.strategies.base import StrategyContext
from src.strategies.registry import StrategyRegistry
from src.strategies.momentum import TrendPullbackV1
from src.strategies.stub import HoldStrategy


class TestStrategyRegistry:
    def test_register_and_get(self) -> None:
        """Register then get returns the strategy."""
        registry = StrategyRegistry()
        registry.register("trend_pullback_v1", TrendPullbackV1)
        strat = registry.get("trend_pullback_v1")
        assert isinstance(strat, TrendPullbackV1)
        assert strat.id == "trend_pullback_v1"

    def test_get_unknown_raises(self) -> None:
        """Unknown id raises KeyError."""
        registry = StrategyRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent_strategy")

    def test_from_settings(self) -> None:
        """Settings with strategies=['trend_pullback_v1'] → registry has it."""
        settings = Settings(strategies=["trend_pullback_v1"])
        registry = StrategyRegistry.from_settings(settings)
        strat = registry.get("trend_pullback_v1")
        assert isinstance(strat, TrendPullbackV1)
        assert "trend_pullback_v1" in registry.get_all()

    def test_get_all(self) -> None:
        """get_all returns all registered strategies."""
        registry = StrategyRegistry()
        registry.register("trend_pullback_v1", TrendPullbackV1)
        registry.register("hold", HoldStrategy)
        all_strats = registry.get_all()
        assert len(all_strats) == 2
        assert "trend_pullback_v1" in all_strats
        assert "hold" in all_strats
        assert isinstance(all_strats["trend_pullback_v1"], TrendPullbackV1)
        assert isinstance(all_strats["hold"], HoldStrategy)

    def test_get_all_returns_copy(self) -> None:
        """get_all returns a copy — mutating it doesn't affect registry."""
        registry = StrategyRegistry()
        registry.register("hold", HoldStrategy)
        all_strats = registry.get_all()
        all_strats.clear()
        assert "hold" in registry.get_all()  # original unchanged

    def test_from_settings_multiple(self) -> None:
        """Settings with multiple strategies → all registered."""
        settings = Settings(strategies=["trend_pullback_v1", "hold"])
        registry = StrategyRegistry.from_settings(settings)
        all_strats = registry.get_all()
        assert len(all_strats) == 2
        assert isinstance(all_strats["trend_pullback_v1"], TrendPullbackV1)
        assert isinstance(all_strats["hold"], HoldStrategy)

    def test_from_settings_unknown_raises(self) -> None:
        """Unknown strategy id in settings raises KeyError."""
        settings = Settings(strategies=["bogus_strategy"])
        with pytest.raises(KeyError):
            StrategyRegistry.from_settings(settings)
