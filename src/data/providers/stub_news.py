"""Stub news provider — returns empty results (no real news source yet)."""

from __future__ import annotations

from datetime import datetime

from src.brokers.models import NewsItem


class StubNewsProvider:
    """Placeholder ``NewsProvider`` that always returns an empty list."""

    source: str = "stub"

    def get_headlines(
        self,
        symbol: str | None,
        since: datetime,
    ) -> list[NewsItem]:
        """Return an empty list — no news backend wired yet."""
        return []
