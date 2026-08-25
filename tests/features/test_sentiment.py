"""Tests for sentiment scoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.brokers.models import NewsItem
from src.features.sentiment import SentimentAnalyzer


def _news(item_id: str, headline: str, when: datetime, symbol: str = "TEST") -> NewsItem:
    return NewsItem(
        id=item_id,
        symbol=symbol,
        headline=headline,
        published_at=when,
        source="test",
    )


def test_analyze_positive():
    a = SentimentAnalyzer()
    score = a.analyze(["Great earnings beat, stock surges on record profits"])
    assert score > 0.0
    assert score <= 1.0


def test_analyze_negative():
    a = SentimentAnalyzer()
    score = a.analyze(["Company plunges amid fraud investigation and bankruptcy fears"])
    assert score < 0.0
    assert score >= -1.0


def test_analyze_empty():
    a = SentimentAnalyzer()
    assert a.analyze([]) == 0.0


def test_score_news_items_filters_by_as_of():
    a = SentimentAnalyzer()
    as_of = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    items = [
        _news("a", "Great earnings beat", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)),
        _news("b", "Plunges on bankruptcy fears", datetime(2026, 1, 3, 12, 0, tzinfo=timezone.utc)),
    ]
    score = a.score_news_items(items, as_of)
    # Only item "a" qualifies; positive sentiment.
    assert score > 0.0
    # "b" was not scored.
    assert "b" not in a.cache
    assert "a" in a.cache


def test_score_news_items_lookback_window():
    a = SentimentAnalyzer()
    as_of = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    items = [
        # Within 24h
        _news("x", "Great gains", as_of - timedelta(hours=12)),
        # Too old (> 24h)
        _news("y", "Great gains", as_of - timedelta(hours=48)),
    ]
    score = a.score_news_items(items, as_of, lookback_hours=24)
    assert "x" in a.cache
    assert "y" not in a.cache
    assert score > 0.0


def test_cache_hit():
    a = SentimentAnalyzer()
    as_of = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    item = _news("z", "Great earnings beat surges", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
    score1 = a.score_news_items([item], as_of)
    cache_after_first = dict(a.cache)
    # Re-score with the same item; cache should be hit (no new entries).
    score2 = a.score_news_items([item], as_of)
    assert score1 == score2
    assert a.cache == cache_after_first
    assert "z" in a.cache
