"""Cost tracking for LLM calls — daily budget enforcement.

Tracks cumulative USD spend per calendar day. Resets automatically when
the calendar day rolls over (so a long-running process doesn't carry
yesterday's spend into today).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


class CostTracker:
    """Track daily LLM spend in USD.

    Thread-safety: not required — the orchestrator calls the LLM path
    single-threaded. If that changes, wrap the two fields in a lock.
    """

    def __init__(self) -> None:
        self._daily_cost: Decimal = Decimal("0")
        self._day: datetime = self._today()

    @staticmethod
    def _today() -> datetime:
        """Current UTC calendar date (time truncated to day for comparison)."""
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    def _maybe_rollover(self) -> None:
        """If the calendar day changed, reset the daily total."""
        today = self._today()
        if today.date() != self._day.date():
            self._daily_cost = Decimal("0")
            self._day = today

    def add_cost(self, amount: Decimal) -> None:
        """Add ``amount`` to the current day's cumulative spend."""
        if amount is None:
            return
        if amount < 0:
            raise ValueError("cost amount must be non-negative")
        self._maybe_rollover()
        self._daily_cost += Decimal(str(amount))

    def get_daily_cost(self) -> Decimal:
        """Return cumulative spend for the current calendar day."""
        self._maybe_rollover()
        return self._daily_cost

    def is_over_budget(self, max_daily: Decimal) -> bool:
        """True if current daily spend exceeds ``max_daily``."""
        return self.get_daily_cost() > Decimal(str(max_daily))

    def reset(self) -> None:
        """Reset the daily total to zero (e.g. for tests or manual override)."""
        self._daily_cost = Decimal("0")
        self._day = self._today()
