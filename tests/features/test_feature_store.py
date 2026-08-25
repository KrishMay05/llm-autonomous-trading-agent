"""Tests for the feature store."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.models import Bar, NewsItem
from src.features.feature_store import FEATURE_KEYS, build_features


def _bar(ts_close: datetime, c: float, v: float = 1000.0) -> Bar:
    return Bar(
        symbol="TEST",
        timeframe="1d",
        ts_open=ts_close - timedelta(days=1),
        ts_close=ts_close,
        open=Decimal(str(c - 1)),
        high=Decimal(str(c + 1)),
        low=Decimal(str(c - 2)),
        close=Decimal(str(c)),
        volume=Decimal(str(v)),
    )


def _news(item_id: str, headline: str, when: datetime) -> NewsItem:
    return NewsItem(
        id=item_id,
        symbol="TEST",
        headline=headline,
        published_at=when,
        source="test",
    )


def _make_bars(n: int, start: datetime) -> list[Bar]:
    return [_bar(start + timedelta(days=i), 100.0 + i) for i in range(n)]


def test_build_features_filters_bars():
    as_of = datetime(2026, 1, 3, 16, 0, tzinfo=timezone.utc)
    start = as_of - timedelta(days=10)
    # 5 eligible bars + 1 future bar.
    bars = _make_bars(5, start)
    future = _bar(as_of + timedelta(days=1), 999.0)
    bars.append(future)
    fv = build_features("TEST", as_of, bars, [])
    # Only 5 bars eligible; SMA-200 should be NaN.
    assert math.isnan(fv.values["sma_200"])
    # return_1d should be finite (last eligible bar).
    assert not math.isnan(fv.values["return_1d"])


def test_build_features_has_keys():
    as_of = datetime(2026, 1, 1, 16, 0, tzinfo=timezone.utc)
    start = as_of - timedelta(days=10)
    fv = build_features("TEST", as_of, _make_bars(10, start), [])
    for k in FEATURE_KEYS:
        assert k in fv.values


def test_build_features_meta():
    as_of = datetime(2026, 1, 1, 16, 0, tzinfo=timezone.utc)  # New Year's Day
    fv = build_features("TEST", as_of, [], [])
    assert "market_open" in fv.meta
    assert "trading_day" in fv.meta
    # New Year's Day is a holiday.
    assert fv.meta["trading_day"] == "False"


def test_build_features_empty_bars():
    as_of = datetime(2026, 1, 5, 21, 0, tzinfo=timezone.utc)
    fv = build_features("TEST", as_of, [], [])
    # All technical features NaN; sentiment is 0.0 by policy.
    for k in FEATURE_KEYS:
        if k == "sentiment_score":
            assert fv.values[k] == 0.0
        else:
            assert math.isnan(fv.values[k])
    assert fv.symbol == "TEST"


def test_build_features_filters_news():
    as_of = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    start = as_of - timedelta(days=10)
    news = [
        _news("past", "Great earnings beat", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)),
        _news("future", "Great earnings beat", datetime(2026, 1, 3, 12, 0, tzinfo=timezone.utc)),
    ]
    fv = build_features("TEST", as_of, _make_bars(10, start), news)
    # Should be positive (only the past positive item counted).
    assert fv.values["sentiment_score"] > 0.0


def test_build_features_symbol_and_as_of():
    as_of = datetime(2026, 1, 5, 21, 0, tzinfo=timezone.utc)
    fv = build_features("AAPL", as_of, [], [])
    assert fv.symbol == "AAPL"
    assert fv.as_of == as_of


def test_build_features_full_run():
    as_of = datetime(2026, 4, 1, 21, 0, tzinfo=timezone.utc)
    start = as_of - timedelta(days=250)
    bars = _make_bars(250, start)
    news = [
        _news("n1", "Stock surges on record profits", as_of - timedelta(hours=12)),
        _news("n2", "Weak guidance drags shares lower", as_of - timedelta(hours=6)),
    ]
    fv = build_features("TEST", as_of, bars, news)
    assert not math.isnan(fv.values["sma_200"])
    assert not math.isnan(fv.values["rsi_14"])
    assert not math.isnan(fv.values["macd_line"])
    assert -1.0 <= fv.values["sentiment_score"] <= 1.0
