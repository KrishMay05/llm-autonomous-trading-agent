"""Tests for data providers + factory (no network calls)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config.settings import Settings
from src.data.providers.factory import get_market_data_provider, get_news_provider
from src.data.providers.stub_news import StubNewsProvider
from src.data.providers.yfinance_provider import YFinanceMarketDataProvider


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def utc_now() -> datetime:
    return datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)


@pytest.fixture
def provider() -> YFinanceMarketDataProvider:
    return YFinanceMarketDataProvider()


def _mock_bars_df() -> pd.DataFrame:
    """A small OHLCV DataFrame that mimics yfinance.download output."""
    index = pd.DatetimeIndex(
        [
            "2026-01-12 09:30:00",
            "2026-01-13 09:30:00",
            "2026-01-14 09:30:00",
        ],
        tz="America/New_York",
    )
    data = {
        "Open": [100.50, 102.00, 101.25],
        "High": [101.00, 103.00, 102.50],
        "Low": [99.50, 101.00, 100.50],
        "Close": [100.75, 102.50, 102.00],
        "Volume": [10_000, 12_000, 8_500],
    }
    return pd.DataFrame(data, index=index)


# ── YFinanceMarketDataProvider.get_bars ────────────────────────────

def test_yfinance_get_bars_mock(provider: YFinanceMarketDataProvider, utc_now: datetime) -> None:
    """Mocked yfinance.download returns valid Bar objects with Decimal fields."""
    df = _mock_bars_df()

    with patch("yfinance.download", return_value=df) as mock_download:
        bars = provider.get_bars(
            "AAPL", "1d",
            datetime(2026, 1, 12, tzinfo=timezone.utc),
            datetime(2026, 1, 14, tzinfo=timezone.utc),
        )

    mock_download.assert_called_once()

    assert len(bars) == 3
    first = bars[0]
    assert first.symbol == "AAPL"
    assert first.timeframe == "1d"
    assert first.source == "yfinance"
    assert isinstance(first.open, Decimal)
    assert isinstance(first.high, Decimal)
    assert isinstance(first.low, Decimal)
    assert isinstance(first.close, Decimal)
    assert isinstance(first.volume, Decimal)
    # UTC conversion: tz-aware datetimes must end up in UTC
    assert first.ts_open.tzinfo == timezone.utc


def test_yfinance_empty_data(provider: YFinanceMarketDataProvider, utc_now: datetime) -> None:
    """Empty / None downloads return an empty list — no exceptions."""
    with patch("yfinance.download", return_value=pd.DataFrame()):
        bars = provider.get_bars(
            "AAPL", "1d",
            datetime(2026, 1, 12, tzinfo=timezone.utc),
            datetime(2026, 1, 14, tzinfo=timezone.utc),
        )
    assert bars == []

    # Also verify None return is handled
    with patch("yfinance.download", return_value=None):
        bars = provider.get_bars(
            "AAPL", "1d",
            datetime(2026, 1, 12, tzinfo=timezone.utc),
            datetime(2026, 1, 14, tzinfo=timezone.utc),
        )
    assert bars == []


# ── YFinanceMarketDataProvider.get_quote ────────────────────────────

def test_yfinance_get_quote(provider: YFinanceMarketDataProvider) -> None:
    """Mock yfinance.Ticker().info and verify Quote conversion."""
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "bid": 100.25,
        "ask": 100.50,
        "currentPrice": 100.40,
    }

    with patch("yfinance.Ticker", return_value=mock_ticker):
        quote = provider.get_quote("AAPL")

    assert quote.symbol == "AAPL"
    assert quote.source == "yfinance"
    assert isinstance(quote.bid, Decimal)
    assert isinstance(quote.ask, Decimal)
    assert isinstance(quote.last, Decimal)
    assert quote.bid == Decimal("100.25")
    assert quote.ask == Decimal("100.50")
    assert quote.last == Decimal("100.40")
    assert quote.ts.tzinfo == timezone.utc
    assert quote.received_at.tzinfo == timezone.utc


# ── Factory ──────────────────────────────────────────────────────────

def test_factory_yfinance() -> None:
    """Factory returns YFinanceMarketDataProvider when configured."""
    s = Settings(market_data_provider="yfinance")
    p = get_market_data_provider(s)
    assert isinstance(p, YFinanceMarketDataProvider)


def test_factory_polygon_not_implemented() -> None:
    """Factory raises NotImplementedError for the polygon provider."""
    s = Settings(market_data_provider="polygon")
    with pytest.raises(NotImplementedError):
        get_market_data_provider(s)


def test_factory_news_stub() -> None:
    """Factory returns StubNewsProvider for the news backend."""
    s = Settings()
    news = get_news_provider(s)
    assert isinstance(news, StubNewsProvider)
    assert news.get_headlines("AAPL", datetime.now(tz=timezone.utc)) == []


# ── isprotocol / Protocol runtime check (smoke) ─────────────────────

def test_yfinance_implements_protocol(provider: YFinanceMarketDataProvider) -> None:
    """YFinanceMarketDataProvider satisfies the MarketDataProvider Protocol."""
    from src.data.providers.base import MarketDataProvider
    assert isinstance(provider, MarketDataProvider)
