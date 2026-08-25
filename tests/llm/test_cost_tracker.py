"""Tests for src/llm/cost_tracker.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.llm.cost_tracker import CostTracker


def test_add_cost_accumulates() -> None:
    """Adding cost accumulates into the daily total."""
    tracker = CostTracker()
    assert tracker.get_daily_cost() == Decimal("0")

    tracker.add_cost(Decimal("0.50"))
    assert tracker.get_daily_cost() == Decimal("0.50")

    tracker.add_cost(Decimal("1.25"))
    assert tracker.get_daily_cost() == Decimal("1.75")


def test_add_cost_ignores_none() -> None:
    """None amount is a no-op (defensive)."""
    tracker = CostTracker()
    tracker.add_cost(None)  # type: ignore[arg-type]
    assert tracker.get_daily_cost() == Decimal("0")


def test_add_cost_rejects_negative() -> None:
    """Negative cost is a programmer error."""
    tracker = CostTracker()
    with pytest.raises(ValueError):
        tracker.add_cost(Decimal("-1.00"))


def test_is_over_budget_true() -> None:
    """Over budget when daily cost exceeds max."""
    tracker = CostTracker()
    tracker.add_cost(Decimal("5.01"))
    assert tracker.is_over_budget(Decimal("5.00")) is True


def test_is_over_budget_false_when_under() -> None:
    """Under budget returns False."""
    tracker = CostTracker()
    tracker.add_cost(Decimal("4.99"))
    assert tracker.is_over_budget(Decimal("5.00")) is False


def test_is_over_budget_false_when_equal() -> None:
    """Exactly at the limit is NOT over budget (strict >)."""
    tracker = CostTracker()
    tracker.add_cost(Decimal("5.00"))
    assert tracker.is_over_budget(Decimal("5.00")) is False


def test_reset_clears_daily_cost() -> None:
    """Reset zeroes the daily total."""
    tracker = CostTracker()
    tracker.add_cost(Decimal("3.00"))
    assert tracker.get_daily_cost() == Decimal("3.00")
    tracker.reset()
    assert tracker.get_daily_cost() == Decimal("0")


def test_rollover_on_new_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cost resets when the calendar day changes."""

    class FakeClock:
        def __init__(self) -> None:
            self.now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        def advance_day(self) -> None:
            self.now = self.now + timedelta(days=1)

    clock = FakeClock()
    tracker = CostTracker()

    # Patch _today to use our fake clock.
    monkeypatch.setattr(tracker, "_today", lambda: clock.now)
    # Also patch the staticmethod on the class for the initial __init__ day.
    monkeypatch.setattr(CostTracker, "_today", lambda _: clock.now)

    tracker.add_cost(Decimal("2.00"))
    assert tracker.get_daily_cost() == Decimal("2.00")

    # Advance one day — rollover should reset.
    clock.advance_day()
    assert tracker.get_daily_cost() == Decimal("0")
