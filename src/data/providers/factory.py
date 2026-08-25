"""Provider factory — selects the configured data / news backend."""

from __future__ import annotations

from src.config.settings import Settings

from .base import MarketDataProvider, NewsProvider
from .stub_news import StubNewsProvider
from .yfinance_provider import YFinanceMarketDataProvider


def get_market_data_provider(settings: Settings) -> MarketDataProvider:
    """Return the market-data provider named by ``settings.market_data_provider``."""
    name = settings.market_data_provider
    if name == "yfinance":
        return YFinanceMarketDataProvider()
    if name == "polygon":
        raise NotImplementedError("Polygon provider coming in Phase 8")
    if name == "alpaca_data":
        raise NotImplementedError("Alpaca data provider coming in a later phase")
    raise NotImplementedError(f"Unknown market_data_provider: {name!r}")


def get_news_provider(settings: Settings) -> NewsProvider:
    """Return the news provider — StubNewsProvider for now."""
    return StubNewsProvider()
