"""Provider protocol definitions.

These Protocols define the contracts every market-data or news backend
must satisfy.  Concrete implementations live alongside this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from src.brokers.models import Bar, NewsItem, Quote


@runtime_checkable
class MarketDataProvider(Protocol):
    """Minimal contract for historical bars + real-time quotes."""

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Return OHLCV bars for *symbol* between *start* and *end*."""
        ...

    def get_quote(self, symbol: str) -> Quote:
        """Return the most recent Quote for *symbol*."""
        ...


@runtime_checkable
class NewsProvider(Protocol):
    """Contract for fetching news headlines."""

    def get_headlines(
        self,
        symbol: str | None,
        since: datetime,
    ) -> list[NewsItem]:
        """Return NewsItems published since *since*.

        If *symbol* is ``None``, return general market headlines.
        """
        ...
