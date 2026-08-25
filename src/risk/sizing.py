"""Position sizing helpers — strength-scaled and max-cap resizers.

All inputs/outputs are ``Decimal`` to avoid float drift in money math.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN


def size_position(
    strength: float,
    equity: Decimal,
    max_pct: Decimal,
    price: Decimal,
) -> Decimal:
    """Size a position as ``equity * max_pct * strength`` divided by ``price``.

    Returns whole shares (integer-valued ``Decimal``, rounded down).

    >>> from decimal import Decimal
    >>> size_position(0.5, Decimal("100000"), Decimal("0.10"), Decimal("100"))
    Decimal('50')
    """
    if price <= 0:
        return Decimal("0")
    raw = (equity * max_pct * Decimal(str(strength))) / price
    return raw.quantize(Decimal("1"), rounding=ROUND_DOWN)


def resize_to_max(
    qty: Decimal,
    current_position_value: Decimal,
    max_allowed: Decimal,
    price: Decimal,
) -> Decimal:
    """Cap ``qty`` so the post-trade position notional stays within ``max_allowed``.

    Returns ``min(qty, (max_allowed - current_position_value) / price)``,
    floored to whole shares and clamped to non-negative.
    """
    if price <= 0:
        return Decimal("0")
    remaining = max_allowed - current_position_value
    if remaining <= 0:
        return Decimal("0")
    max_qty = remaining / price
    max_qty = max_qty.quantize(Decimal("1"), rounding=ROUND_DOWN)
    if max_qty < 0:
        max_qty = Decimal("0")
    return min(qty, max_qty)
