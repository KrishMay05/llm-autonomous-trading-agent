"""Sentiment scoring for news headlines.

A lightweight, dependency-free VADER-like lexicon scorer. It tokenises
headlines, maps tokens to positive/negative polarities, and returns an
average sentiment in ``[-1, 1]``. The :class:`SentimentAnalyzer` caches
per-``NewsItem.id`` scores so that repeated lookups are free.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.brokers.models import NewsItem


# A small but reasonably broad VADER-inspired lexicon.
# Each word maps to a polarity in [-1, 1]. Negations flip the sign.
_POSITIVE_WORDS: dict[str, float] = {
    "good": 0.5,
    "great": 0.8,
    "excellent": 0.9,
    "amazing": 0.9,
    "awesome": 0.8,
    "fantastic": 0.8,
    "wonderful": 0.8,
    "best": 0.8,
    "better": 0.6,
    "strong": 0.6,
    "bullish": 0.8,
    "gain": 0.5,
    "gains": 0.5,
    "gained": 0.5,
    "growth": 0.5,
    "grow": 0.4,
    "grows": 0.4,
    "grew": 0.4,
    "growing": 0.5,
    "up": 0.3,
    "rise": 0.5,
    "rises": 0.5,
    "rising": 0.5,
    "rose": 0.5,
    "rally": 0.6,
    "rallies": 0.6,
    "rallied": 0.6,
    "soar": 0.8,
    "soars": 0.8,
    "soared": 0.8,
    "surge": 0.7,
    "surges": 0.7,
    "surged": 0.7,
    "jump": 0.5,
    "jumps": 0.5,
    "jumped": 0.5,
    "beat": 0.6,
    "beats": 0.6,
    "beaten": -0.3,
    "profit": 0.6,
    "profits": 0.6,
    "profitable": 0.7,
    "win": 0.6,
    "wins": 0.6,
    "won": 0.6,
    "success": 0.7,
    "successful": 0.8,
    "boost": 0.5,
    "boosts": 0.5,
    "boosted": 0.5,
    "upgrade": 0.5,
    "upgraded": 0.5,
    "upgrades": 0.5,
    "outperform": 0.6,
    "outperforms": 0.6,
    "positive": 0.6,
    "optimistic": 0.6,
    "confident": 0.5,
    "recovery": 0.5,
    "recover": 0.4,
    "recovers": 0.4,
    "recovered": 0.4,
    "rebound": 0.5,
    "rebounds": 0.5,
    "breakthrough": 0.7,
    "innovation": 0.4,
    "innovative": 0.5,
    "record": 0.6,
    "high": 0.3,
    "higher": 0.4,
    "opportunity": 0.5,
    "opportunities": 0.5,
    "favorable": 0.5,
    "favourable": 0.5,
    "encouraging": 0.6,
    "encouraged": 0.5,
}

_NEGATIVE_WORDS: dict[str, float] = {
    "bad": -0.5,
    "terrible": -0.8,
    "awful": -0.8,
    "horrible": -0.9,
    "worst": -0.9,
    "worse": -0.6,
    "weak": -0.5,
    "bearish": -0.8,
    "loss": -0.6,
    "losses": -0.6,
    "lost": -0.5,
    "lose": -0.5,
    "losing": -0.5,
    "down": -0.3,
    "fall": -0.5,
    "falls": -0.5,
    "fell": -0.5,
    "falling": -0.5,
    "drop": -0.5,
    "drops": -0.5,
    "dropped": -0.5,
    "plunge": -0.8,
    "plunges": -0.8,
    "plunged": -0.8,
    "crash": -0.9,
    "crashes": -0.9,
    "crashed": -0.9,
    "tank": -0.7,
    "tanks": -0.7,
    "tanked": -0.7,
    "dive": -0.6,
    "dives": -0.6,
    "dived": -0.6,
    "sell": -0.5,
    "sells": -0.5,
    "sold": -0.5,
    "selling": -0.5,
    "miss": -0.6,
    "misses": -0.6,
    "missed": -0.6,
    "cut": -0.4,
    "cuts": -0.4,
    "cutting": -0.4,
    "downgrade": -0.6,
    "downgrades": -0.6,
    "downgraded": -0.6,
    "underperform": -0.6,
    "underperforms": -0.6,
    "negative": -0.6,
    "pessimistic": -0.6,
    "fear": -0.6,
    "fears": -0.6,
    "fearful": -0.6,
    "concern": -0.4,
    "concerns": -0.4,
    "concerned": -0.5,
    "worried": -0.5,
    "worry": -0.4,
    "worries": -0.4,
    "risk": -0.3,
    "risky": -0.4,
    "risks": -0.3,
    "lawsuit": -0.6,
    "lawsuits": -0.6,
    "sue": -0.5,
    "sues": -0.5,
    "sued": -0.5,
    "fraud": -0.8,
    "investigation": -0.6,
    "investigate": -0.5,
    "investigated": -0.5,
    "scandal": -0.8,
    "bankrupt": -0.9,
    "bankruptcy": -0.9,
    "debt": -0.3,
    "default": -0.7,
    "defaults": -0.7,
    "defaulted": -0.7,
    "low": -0.2,
    "lower": -0.3,
    "decline": -0.5,
    "declines": -0.5,
    "declined": -0.5,
    "recession": -0.7,
    "inflation": -0.3,
    "layoff": -0.5,
    "layoffs": -0.5,
    "unemployment": -0.5,
    "strike": -0.4,
    "warning": -0.4,
    "warned": -0.5,
    "warns": -0.5,
    "caution": -0.3,
    "cautioned": -0.3,
}

_NEGATION_WORDS: set[str] = {
    "not",
    "no",
    "never",
    "without",
    "don't",
    "doesn't",
    "didn't",
    "isn't",
    "wasn't",
    "won't",
    "can't",
    "cannot",
    "hardly",
    "barely",
}

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class SentimentAnalyzer:
    """Lexicon-based sentiment scorer with a per-id cache.

    The cache is a plain ``dict[str, float]`` keyed by ``NewsItem.id``;
    callers can inspect ``analyzer.cache`` to verify hit behaviour.
    """

    def __init__(self) -> None:
        self.cache: dict[str, float] = {}

    # -- single-headline scoring -------------------------------------------
    def _score_text(self, text: str) -> float:
        """Score a single string in ``[-1, 1]``."""
        tokens = _tokenize(text)
        if not tokens:
            return 0.0

        total = 0.0
        count = 0
        negate = False
        for tok in tokens:
            if tok in _NEGATION_WORDS:
                negate = True
                continue
            score = _POSITIVE_WORDS.get(tok, _NEGATIVE_WORDS.get(tok))
            if score is None:
                # Reset negation only after we've passed a non-lexicon token.
                # Keep negation sticky for the immediately following word.
                if negate:
                    # token was not a lexicon word — leave negate on until we
                    # consume one sentiment-bearing word.
                    continue
                continue
            if negate:
                score = -score
                negate = False
            total += score
            count += 1

        if count == 0:
            return 0.0
        avg = total / count
        # squash into [-1, 1] robustly (mean of bounded vals is already
        # in range, but guard against fp drift)
        return max(-1.0, min(1.0, avg))

    # -- public API --------------------------------------------------------
    def analyze(self, headlines: list[str]) -> float:
        """Average sentiment across *headlines* in ``[-1, 1]``.

        Returns ``0.0`` for an empty list.
        """
        if not headlines:
            return 0.0
        scores = [self._score_text(h) for h in headlines]
        return sum(scores) / len(scores)

    def score_news_items(
        self,
        items: list[NewsItem],
        as_of: datetime,
        lookback_hours: int = 24,
    ) -> float:
        """Aggregate sentiment for news items up to ``as_of``.

        - Only items with ``published_at <= as_of`` are considered.
        - Only items within ``lookback_hours`` of ``as_of`` are considered.
        - Per-item scores are cached by ``NewsItem.id``.
        - Returns ``0.0`` if no items qualify.
        """
        cutoff = as_of - timedelta(hours=lookback_hours)
        relevant: list[float] = []
        for item in items:
            if item.published_at > as_of:
                continue
            if item.published_at < cutoff:
                continue
            score = self.cache.get(item.id)
            if score is None:
                score = self._score_text(item.headline)
                self.cache[item.id] = score
            relevant.append(score)

        if not relevant:
            return 0.0
        return sum(relevant) / len(relevant)
