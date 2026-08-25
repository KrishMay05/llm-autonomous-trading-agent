"""Feature store: assemble a :class:`FeatureVector` from bars + news.

The single entry point is :func:`build_features`, which:

- Filters bars to those with ``ts_close <= as_of`` (no look-ahead).
- Filters news to items with ``published_at <= as_of``.
- Computes technical indicators (RSI-14, SMA-20/50/200, MACD,
  ATR-14, volume-ratio-20, 1-day return).
- Computes an aggregate sentiment score over the last 24h of news.
- Attaches calendar flags ("market_open", "trading_day") as meta.

Warm-up NaN policy: if insufficient bars exist for a given indicator,
the value is NaN. Strategies should treat any NaN feature as HOLD.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from src.features import technicals
from src.features.calendar import is_market_open, is_trading_day
from src.features.sentiment import SentimentAnalyzer

if TYPE_CHECKING:
    from src.brokers.models import Bar, FeatureVector, NewsItem


_FEATURE_KEYS = (
    "rsi_14",
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_20",
    "macd_line",
    "macd_signal",
    "macd_hist",
    "atr_14",
    "volume_ratio_20",
    "return_1d",
    "sentiment_score",
)


def _safe_last(series) -> float:
    """Return the last finite value of a Series, or NaN."""
    if series is None:
        return float("nan")
    try:
        s = series.dropna()
    except Exception:
        return float("nan")
    if s.empty:
        return float("nan")
    return float(s.iloc[-1])


def build_features(
    symbol: str,
    as_of: datetime,
    bars: list[Bar],
    news: list[NewsItem],
) -> FeatureVector:
    """Assemble a :class:`FeatureVector` from raw bars and news.

    Bars and news are filtered strictly by ``as_of`` (no look-ahead).
    Returns a :class:`FeatureVector` whose ``values`` dict contains the
    keys listed in ``_FEATURE_KEYS`` and whose ``meta`` dict contains
    ``"market_open"`` and ``"trading_day"`` as stringified booleans.
    """
    from src.brokers.models import FeatureVector as _FV

    # ── Filter bars ─────────────────────────────────────────────
    eligible_bars = [b for b in bars if b.ts_close <= as_of]
    # ── Filter news ─────────────────────────────────────────────
    eligible_news = [n for n in news if n.published_at <= as_of]

    values: dict[str, float] = {k: float("nan") for k in _FEATURE_KEYS}

    if eligible_bars:
        df = technicals.bars_to_dataframe(eligible_bars)
        close: pd.Series = df["close"]
        high: pd.Series = df["high"]
        low: pd.Series = df["low"]
        volume: pd.Series = df["volume"]

        if len(df) >= 2:
            rets = technicals.compute_returns(close)
            values["return_1d"] = _safe_last(rets)
        values["sma_20"] = _safe_last(technicals.compute_sma(close, 20))
        values["sma_50"] = _safe_last(technicals.compute_sma(close, 50))
        values["sma_200"] = _safe_last(technicals.compute_sma(close, 200))
        values["ema_20"] = _safe_last(technicals.compute_ema(close, 20))
        values["rsi_14"] = _safe_last(technicals.compute_rsi(close, 14))
        macd_df = technicals.compute_macd(close)
        if macd_df is not None and not macd_df.empty:
            values["macd_line"] = _safe_last(macd_df["macd_line"])
            values["macd_signal"] = _safe_last(macd_df["signal_line"])
            values["macd_hist"] = _safe_last(macd_df["histogram"])
        values["atr_14"] = _safe_last(
            technicals.compute_atr(high, low, close, 14)
        )
        values["volume_ratio_20"] = _safe_last(
            technicals.compute_volume_ratio(volume, 20)
        )

    # ── Sentiment ──────────────────────────────────────────────
    analyzer = SentimentAnalyzer()
    sentiment = analyzer.score_news_items(eligible_news, as_of, lookback_hours=24)
    # If no qualifying news, score is 0.0 (documented policy); we still
    # surface it so strategies see an explicit numeric rather than NaN.
    if not eligible_news:
        values["sentiment_score"] = 0.0
    else:
        values["sentiment_score"] = float(sentiment)

    # ── Meta (calendar) ────────────────────────────────────────
    meta = {
        "market_open": str(is_market_open(as_of)),
        "trading_day": str(is_trading_day(as_of)),
    }

    return _FV(
        symbol=symbol,
        as_of=as_of,
        values=values,
        meta=meta,
    )


# Re-exported for callers that want the schema.
FEATURE_KEYS: tuple[str, ...] = _FEATURE_KEYS
