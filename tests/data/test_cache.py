"""Tests for the disk DataCache."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from src.brokers.models import Bar, Quote
from src.data.cache import DataCache


@pytest.fixture
def cache(tmp_path: Path) -> DataCache:
    """Fresh DataCache pointing at a temporary directory."""
    return DataCache(tmp_path / "dc")


# ── primitives ──────────────────────────────────────────────────────

def test_cache_set_get(cache: DataCache) -> None:
    """Set then get returns the same value."""
    cache.set("foo", {"a": 1}, ttl=3600)
    assert cache.get("foo") == {"a": 1}
    assert cache.exists("foo")


def test_cache_miss(cache: DataCache) -> None:
    """Get on a non-existent key returns None."""
    assert cache.get("missing") is None
    assert not cache.exists("missing")


def test_cache_expiry(cache: DataCache) -> None:
    """An expired key returns None and is removed."""
    cache.set("temp", "value", ttl=0)  # immediately expires
    # ttl=0 sets expires_at = now; simulate a tick by advancing time
    with patch("src.data.cache.time.time", return_value=10**12):
        assert cache.get("temp") is None
        assert not cache.exists("temp")


def test_cache_clear(cache: DataCache) -> None:
    cache.set("a", 1, ttl=3600)
    cache.set("b", 2, ttl=3600)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


# ── key generation ──────────────────────────────────────────────────

def test_cache_key_generation(cache: DataCache) -> None:
    """Same parameters produce the same hash key file."""
    cache2 = DataCache(cache.cache_dir)
    cache2.set("hello", "world", ttl=3600)
    # Same key + same cache_dir → hit
    assert cache.get("hello") == "world"
    # Different key → miss
    assert cache.get("world") is None


# ── high-level bars/quote helpers ───────────────────────────────────

def test_cache_get_put_bars(cache: DataCache) -> None:
    start = datetime(2026, 1, 12, tzinfo=timezone.utc)
    end = datetime(2026, 1, 14, tzinfo=timezone.utc)
    bars = [
        Bar(
            symbol="AAPL",
            timeframe="1d",
            ts_open=start,
            ts_close=end,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.50"),
            volume=Decimal("10000"),
            source="yfinance",
        ),
    ]
    cache.put_bars("yfinance", "AAPL", "1d", start, end, bars)

    got = cache.get_bars("yfinance", "AAPL", "1d", start, end)
    assert got is not None
    assert len(got) == 1
    assert got[0].symbol == "AAPL"
    assert got[0].open == Decimal("100")

    # miss on different params
    assert cache.get_bars("yfinance", "MSFT", "1d", start, end) is None


def test_cache_get_put_quote(cache: DataCache) -> None:
    now = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    q = Quote(
        symbol="AAPL",
        bid=Decimal("100.25"),
        ask=Decimal("100.50"),
        last=Decimal("100.40"),
        ts=now,
        received_at=now,
        source="yfinance",
    )
    cache.put_quote("yfinance", "AAPL", q)
    got = cache.get_quote("yfinance", "AAPL")
    assert got is not None
    assert got.symbol == "AAPL"
    assert got.bid == Decimal("100.25")
    assert cache.get_quote("yfinance", "MSFT") is None


def test_cache_bars_expiry(cache: DataCache) -> None:
    """Bars TTL = 0 should expire immediately."""
    start = datetime(2026, 1, 12, tzinfo=timezone.utc)
    end = datetime(2026, 1, 14, tzinfo=timezone.utc)
    bars: list[Bar] = []
    # Manually set with ttl=0
    key = cache._bars_key("yfinance", "AAPL", "1d", start, end)
    cache.set(key, bars, ttl=0)
    with patch("src.data.cache.time.time", return_value=10**12):
        assert cache.get_bars("yfinance", "AAPL", "1d", start, end) is None
