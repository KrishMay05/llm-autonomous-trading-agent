"""High-level market-data service: provider + cache orchestration."""

from __future__ import annotations

from datetime import datetime

from src.brokers.models import Bar, Quote
from src.data.cache import DataCache
from src.data.providers.base import MarketDataProvider


class MarketDataService:
    """Wrap a ``MarketDataProvider`` with a ``DataCache`` for lookups."""

    def __init__(
        self,
        provider: MarketDataProvider,
        cache: DataCache | None = None,
    ) -> None:
        self.provider = provider
        self.cache = cache
        # Use the provider's ``source`` attribute when available
        self._provider_name: str = getattr(provider, "source", provider.__class__.__name__)

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Return bars — from cache if fresh, otherwise fetched."""
        if self.cache is not None:
            cached = self.cache.get_bars(self._provider_name, symbol, timeframe, start, end)
            if cached is not None:
                return cached

        bars = self.provider.get_bars(symbol, timeframe, start, end)

        if self.cache is not None and bars:
            self.cache.put_bars(self._provider_name, symbol, timeframe, start, end, bars)

        return bars

    def get_quote(self, symbol: str) -> Quote:
        """Return a quote — from cache if fresh, otherwise fetched."""
        if self.cache is not None:
            cached = self.cache.get_quote(self._provider_name, symbol)
            if cached is not None:
                return cached

        quote = self.provider.get_quote(symbol)

        if self.cache is not None:
            self.cache.put_quote(self._provider_name, symbol, quote)

        return quote
