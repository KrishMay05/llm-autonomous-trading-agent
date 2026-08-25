"""Technical indicator functions for the feature pipeline.

All functions handle warm-up gracefully (NaN for insufficient data).
Unless otherwise noted, inputs are pandas Series of floats; outputs preserve
the input index so callers can align by timestamp.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.brokers.models import Bar


def _to_float_series(prices: pd.Series | Decimal) -> pd.Series:
    """Coerce a Series of Decimal/float/int into float Series."""
    if isinstance(prices, pd.Series):
        # vectorised conversion to float (handles Decimal via numpy)
        try:
            return prices.astype(float)
        except (TypeError, ValueError):
            return prices.apply(lambda x: float(x) if x is not None else np.nan)
    return pd.Series([float(prices)])


def compute_returns(prices: pd.Series) -> pd.Series:
    """Daily simple returns: pct change of *prices*.

    First element is NaN (no prior price).
    """
    s = _to_float_series(prices)
    return s.pct_change()


def compute_sma(prices: pd.Series, window: int) -> pd.Series:
    """Simple moving average over *window* periods."""
    s = _to_float_series(prices)
    return s.rolling(window=window, min_periods=window).mean()


def compute_ema(prices: pd.Series, window: int) -> pd.Series:
    """Exponential moving average over *window* periods.

    Uses pandas ``ewm`` with ``adjust=False`` (standard recursive EMA,
    matching the most common definition where the first `window-1` values
    propagate the initial seed).
    """
    s = _to_float_series(prices)
    return s.ewm(span=window, adjust=False, min_periods=window).mean()


def compute_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing), range [0, 100].

    Uses the classic Wilder rolling-average approach rather than the
    simple rolling mean of differences, which matches the de-facto
    talib/pandas-ta default.
    """
    s = _to_float_series(prices)
    delta = s.diff()

    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Wilder's smoothing: EWM with alpha = 1/window
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 and avg_gain > 0 => RSI = 100
    rsi = rsi.where(~((avg_loss == 0.0) & (avg_gain > 0.0)), 100.0)
    rsi = rsi.where(~((avg_loss == 0.0) & (avg_gain == 0.0)), 50.0)
    return rsi.astype(float)


def compute_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Returns a DataFrame with columns: ``macd_line``, ``signal_line``,
    ``histogram``.
    """
    s = _to_float_series(prices)
    ema_fast = s.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = s.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
        },
        index=s.index,
    )


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Average True Range (Wilder's smoothing).

    TR_t = max(high_t - low_t, |high_t - close_{t-1}|, |low_t - close_{t-1}|)
    ATR = EMA(TR, alpha=1/window).
    """
    h = _to_float_series(high)
    l = _to_float_series(low)
    c = _to_float_series(close)

    prev_close = c.shift(1)
    tr1 = h - l
    tr2 = (h - prev_close).abs()
    tr3 = (l - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder smoothing
    atr = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    return atr


def compute_volume_ratio(volumes: pd.Series, window: int = 20) -> pd.Series:
    """Current volume divided by its rolling mean over *window* periods.

    Returns NaN until `window` observations are available.
    """
    v = _to_float_series(volumes)
    rolling_mean = v.rolling(window=window, min_periods=window).mean()
    return (v / rolling_mean).astype(float)


def bars_to_dataframe(bars: list[Bar]) -> pd.DataFrame:
    """Convert a list of :class:`Bar` into a DataFrame indexed by ``ts_close``.

    Columns: ``open``, ``high``, ``low``, ``close``, ``volume`` as floats.
    Bars are sorted by ``ts_close`` ascending.
    """
    if not bars:
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
        )

    records = []
    for b in bars:
        records.append(
            {
                "ts_close": b.ts_close,
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": float(b.volume),
            }
        )

    df = pd.DataFrame.from_records(records)
    df = df.sort_values("ts_close").reset_index(drop=True)
    df = df.set_index("ts_close")
    return df
