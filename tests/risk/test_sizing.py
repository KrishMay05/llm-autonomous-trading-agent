"""Tests for position sizing helpers."""

from __future__ import annotations

from decimal import Decimal

from src.risk.sizing import resize_to_max, size_position


def test_size_position_basic():
    """equity=100k, max_pct=10%, strength=0.5, price=100 → 50 shares."""
    qty = size_position(0.5, Decimal("100000"), Decimal("0.10"), Decimal("100"))
    assert qty == Decimal("50")


def test_size_position_zero_strength():
    qty = size_position(0.0, Decimal("100000"), Decimal("0.10"), Decimal("100"))
    assert qty == Decimal("0")


def test_size_position_rounds_down():
    """Non-integer raw qty is floored to whole shares."""
    qty = size_position(0.333, Decimal("100000"), Decimal("0.10"), Decimal("100"))
    # 100000 * 0.10 * 0.333 / 100 = 33.3 → 33
    assert qty == Decimal("33")


def test_resize_to_max():
    """qty=200, current=0, max=10000, price=100 → 100 shares."""
    resized = resize_to_max(
        qty=Decimal("200"),
        current_position_value=Decimal("0"),
        max_allowed=Decimal("10000"),
        price=Decimal("100"),
    )
    assert resized == Decimal("100")


def test_resize_to_max_with_existing():
    """qty=200, current=6000, max=10000, price=100 → 40 shares."""
    resized = resize_to_max(
        qty=Decimal("200"),
        current_position_value=Decimal("6000"),
        max_allowed=Decimal("10000"),
        price=Decimal("100"),
    )
    assert resized == Decimal("40")


def test_resize_to_max_already_within():
    """qty=50, current=0, max=10000, price=100 → 50 (no resize needed)."""
    resized = resize_to_max(
        qty=Decimal("50"),
        current_position_value=Decimal("0"),
        max_allowed=Decimal("10000"),
        price=Decimal("100"),
    )
    assert resized == Decimal("50")


def test_resize_to_max_at_cap():
    """qty=200, current=10000, max=10000 → 0 (no room)."""
    resized = resize_to_max(
        qty=Decimal("200"),
        current_position_value=Decimal("10000"),
        max_allowed=Decimal("10000"),
        price=Decimal("100"),
    )
    assert resized == Decimal("0")
