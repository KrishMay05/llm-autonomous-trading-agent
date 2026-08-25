"""Tests for technical indicators."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from src.brokers.models import Bar
from src.features.technicals import (
    bars_to_dataframe,
    compute_atr,
    compute_ema,
    compute_macd,
    compute_returns,
    compute_rsi,
    compute_sma,
    compute_volume_ratio,
)


def _bar(ts_close: datetime, o: float, h: float, l: float, c: float, v: float = 1.0) -> Bar:
    return Bar(
        symbol="TEST",
        timeframe="1d",
        ts_open=ts_close - timedelta(days=1),
        ts_close=ts_close,
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(l)),
        close=Decimal(str(c)),
        volume=Decimal(str(v)),
    )


# ── returns ───────────────────────────────────────────────────────
def test_compute_returns():
    prices = pd.Series([100.0, 110.0, 121.0])
    r = compute_returns(prices)
    assert math.isnan(r.iloc[0])
    assert r.iloc[1] == pytest.approx(0.10, abs=1e-9)
    assert r.iloc[2] == pytest.approx(0.10, abs=1e-9)


def test_compute_returns_decimal():
    prices = pd.Series([Decimal("100"), Decimal("110"), Decimal("121")])
    r = compute_returns(prices)
    assert math.isnan(r.iloc[0])
    assert r.iloc[1] == pytest.approx(0.10, abs=1e-9)
    assert r.iloc[2] == pytest.approx(0.10, abs=1e-9)


# ── SMA ───────────────────────────────────────────────────────────
def test_compute_sma():
    prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    sma = compute_sma(prices, 3)
    assert math.isnan(sma.iloc[0])
    assert math.isnan(sma.iloc[1])
    assert sma.iloc[2] == pytest.approx(2.0)
    assert sma.iloc[3] == pytest.approx(3.0)
    assert sma.iloc[4] == pytest.approx(4.0)


# ── EMA ──────────────────────────────────────────────────────────
def test_compute_ema():
    prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    ema = compute_ema(prices, 3)
    # First two values warm up; from index 2 onward we have a valid EMA.
    assert not math.isnan(ema.iloc[-1])
    # EMA should lag the price but be close to it in a rising series.
    assert ema.iloc[-1] < prices.iloc[-1]
    assert ema.iloc[-1] > prices.iloc[0]


# ── RSI ───────────────────────────────────────────────────────────
def test_compute_rsi_range():
    np.random.seed(42)
    prices = pd.Series(np.cumsum(np.random.randn(100)) + 100.0)
    rsi = compute_rsi(prices, 14)
    valid = rsi.dropna()
    assert (valid >= 0).all()
    assert (valid <= 100).all()


def test_compute_rsi_all_up():
    # Monotonically increasing -> RSI should be high (>=70).
    prices = pd.Series([float(100 + i) for i in range(30)])
    rsi = compute_rsi(prices, 14)
    assert rsi.iloc[-1] >= 70.0


def test_compute_rsi_all_down():
    prices = pd.Series([float(100 - i) for i in range(30)])
    rsi = compute_rsi(prices, 14)
    assert rsi.iloc[-1] <= 30.0


# ── MACD ──────────────────────────────────────────────────────────
def test_compute_macd_columns():
    prices = pd.Series([float(100 + i * 0.5) for i in range(50)])
    df = compute_macd(prices)
    assert set(df.columns) == {"macd_line", "signal_line", "histogram"}
    assert len(df) == len(prices)


# ── ATR ──────────────────────────────────────────────────────────
def test_compute_atr():
    high = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0])
    low = pd.Series([8.0, 10.0, 12.0, 14.0, 16.0])
    close = pd.Series([9.0, 11.0, 13.0, 15.0, 17.0])
    atr = compute_atr(high, low, close, window=3)
    # Warm-up: first two values NaN, third value should be finite.
    assert not math.isnan(atr.iloc[-1])
    assert atr.iloc[-1] >= 0.0


# ── bars_to_dataframe ─────────────────────────────────────────────
def test_bars_to_dataframe():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = [
        _bar(base + timedelta(days=i), 100.0 + i, 105.0 + i, 95.0 + i, 100.0 + i, 1000 + i)
        for i in range(3)
    ]
    df = bars_to_dataframe(bars)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 3
    assert df["close"].iloc[0] == 100.0


def test_bars_to_dataframe_empty():
    df = bars_to_dataframe([])
    assert df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


# ── volume ratio ──────────────────────────────────────────────────
def test_compute_volume_ratio():
    # 21 bars of volume 100, then a 22nd bar of 200. The rolling(20)
    # window at the last position covers indices 2..21 (19×100 + 200),
    # so the rolling mean is 105 and the ratio is 200/105 ≈ 1.9048.
    vols = pd.Series([100.0] * 21 + [200.0])
    vr = compute_volume_ratio(vols, 20)
    assert not math.isnan(vr.iloc[-1])
    assert vr.iloc[-1] == pytest.approx(200.0 / 105.0, abs=1e-9)
    # Volume ratio > 1 confirms higher-than-average volume detected.
    assert vr.iloc[-1] > 1.0


# ── warmup NaN ────────────────────────────────────────────────────
def test_warmup_nan():
    prices = pd.Series([1.0, 2.0])
    assert math.isnan(compute_sma(prices, 3).iloc[-1])
    assert math.isnan(compute_rsi(prices, 14).iloc[-1])
    assert math.isnan(compute_atr(pd.Series([1.0, 2.0]), pd.Series([0.0, 1.0]), prices, 14).iloc[-1])
    assert math.isnan(compute_volume_ratio(pd.Series([1.0, 2.0]), 20).iloc[-1])
