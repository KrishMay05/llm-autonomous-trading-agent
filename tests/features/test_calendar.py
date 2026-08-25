"""Tests for the market calendar."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.features.calendar import (
    get_market_session,
    is_market_open,
    is_trading_day,
)


_ET = ZoneInfo("America/New_York")
_UTC = timezone.utc


def test_is_market_open_during_session():
    # 2026-01-05 is a Monday. 10:00 ET = 15:00 UTC (EST, UTC-5).
    dt = datetime(2026, 1, 5, 15, 0, tzinfo=_UTC)
    assert is_market_open(dt) is True


def test_is_market_open_after_close():
    # 17:00 ET on a Monday = 22:00 UTC (EST).
    dt = datetime(2026, 1, 5, 22, 0, tzinfo=_UTC)
    assert is_market_open(dt) is False


def test_is_market_open_weekend():
    # 2026-01-03 is a Saturday, 12:00 ET.
    dt = datetime(2026, 1, 3, 17, 0, tzinfo=_UTC)
    assert is_market_open(dt) is False


def test_is_market_open_holiday():
    # 2025-12-25 is a Thursday (Christmas). 12:00 ET.
    dt = datetime(2025, 12, 25, 17, 0, tzinfo=_UTC)
    assert is_market_open(dt) is False


def test_is_trading_day_weekend():
    dt = datetime(2026, 1, 3, 12, 0, tzinfo=_UTC)  # Saturday
    assert is_trading_day(dt) is False


def test_is_trading_day_weekday():
    dt = datetime(2026, 1, 5, 12, 0, tzinfo=_UTC)  # Monday
    assert is_trading_day(dt) is True


def test_is_trading_day_christmas():
    dt = datetime(2025, 12, 25, 12, 0, tzinfo=_UTC)
    assert is_trading_day(dt) is False


def test_is_trading_day_new_year():
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=_UTC)
    assert is_trading_day(dt) is False


def test_get_market_session_returns_utc():
    dt = datetime(2026, 1, 5, 15, 0, tzinfo=_UTC)  # Monday 10:00 ET
    session = get_market_session(dt)
    assert session is not None
    open_dt, close_dt = session
    assert open_dt.tzinfo is not None
    assert close_dt.tzinfo is not None
    # Open should be 14:30 UTC (9:30 EST, UTC-5).
    assert open_dt.hour == 14 and open_dt.minute == 30
    # Close should be 21:00 UTC (16:00 EST, UTC-5).
    assert close_dt.hour == 21 and close_dt.minute == 0
    assert close_dt > open_dt


def test_get_market_session_non_trading_day():
    dt = datetime(2025, 12, 25, 12, 0, tzinfo=_UTC)
    assert get_market_session(dt) is None


def test_get_market_session_dst():
    # In July, ET is EDT (UTC-4). 2025-07-07 is a Monday.
    dt = datetime(2025, 7, 7, 14, 0, tzinfo=_UTC)  # 10:00 EDT
    session = get_market_session(dt)
    assert session is not None
    open_dt, close_dt = session
    # 9:30 EDT = 13:30 UTC
    assert open_dt.hour == 13 and open_dt.minute == 30
    # 16:00 EDT = 20:00 UTC
    assert close_dt.hour == 20 and close_dt.minute == 0
