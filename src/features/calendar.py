"""US equity market calendar helpers.

All datetimes passed in are assumed to be timezone-aware (UTC or otherwise).
Comparisons are performed in UTC. The market session is defined in
``America/New_York`` local time (ET), which handles DST automatically
because we convert to that zone via ``zoneinfo`` before comparing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # stdlib on 3.9+

_ET = ZoneInfo("America/New_York")
_UTC = timezone.utc

# Market hours (ET)
_MARKET_OPEN_HM = (9, 30)
_MARKET_CLOSE_HM = (16, 0)


def _to_et(dt: datetime) -> datetime:
    """Convert a datetime to America/New_York (handles DST)."""
    if dt.tzinfo is None:
        # Naive datetime — assume UTC for safety.
        dt = dt.replace(tzinfo=_UTC)
    return dt.astimezone(_ET)


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_UTC)
    return dt.astimezone(_UTC)


def _us_holidays(year: int) -> set[datetime]:
    """Return the set of major US equity market holiday dates for *year*.

    Each entry is a midnight-UTC datetime for that date.
    """
    holidays: set[datetime] = set()

    def _d(month: int, day: int) -> datetime:
        return datetime(year, month, day, tzinfo=_UTC)

    # New Year's Day (if not Saturday/Sunday, else observed)
    nyd = _d(1, 1)
    if nyd.weekday() == 5:  # Saturday -> Friday
        nyd = _d(1, 2) if datetime(year, 1, 2).weekday() != 5 else _d(1, 3)
    elif nyd.weekday() == 6:  # Sunday -> Monday
        nyd = _d(1, 2)
    holidays.add(nyd)

    # MLK Day — 3rd Monday of January
    holidays.add(_nth_weekday(year, 1, 0, 3))

    # Presidents Day — 3rd Monday of February
    holidays.add(_nth_weekday(year, 2, 0, 3))

    # Good Friday — Friday before Easter
    holidays.add(_good_friday(year))

    # Memorial Day — last Monday of May
    holidays.add(_last_weekday(year, 5, 0))

    # Juneteenth — June 19 (observed)
    juneteenth = _d(6, 19)
    if juneteenth.weekday() == 5:
        juneteenth = _d(6, 18)
    elif juneteenth.weekday() == 6:
        juneteenth = _d(6, 20)
    holidays.add(juneteenth)

    # Independence Day — July 4 (observed)
    ind = _d(7, 4)
    if ind.weekday() == 5:
        ind = _d(7, 3)
    elif ind.weekday() == 6:
        ind = _d(7, 5)
    holidays.add(ind)

    # Thanksgiving — 4th Thursday of November
    holidays.add(_nth_weekday(year, 11, 3, 4))

    # Christmas — Dec 25 (observed)
    christmas = _d(12, 25)
    if christmas.weekday() == 5:
        christmas = _d(12, 24)
    elif christmas.weekday() == 6:
        christmas = _d(12, 26)
    holidays.add(christmas)

    return holidays


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime:
    """Return the datetime of the *n*-th *weekday* of *month*."""
    first = datetime(year, month, 1, tzinfo=_UTC)
    offset = (weekday - first.weekday()) % 7
    day = 1 + offset + (n - 1) * 7
    return datetime(year, month, day, tzinfo=_UTC)


def _last_weekday(year: int, month: int, weekday: int) -> datetime:
    """Return the last *weekday* of *month*."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=_UTC)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=_UTC)
    last = next_month - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def _good_friday(year: int) -> datetime:
    """Good Friday = Easter Sunday - 2 days. Use the Anonymous Gregorian
    algorithm (valid for Gregorian calendar)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = datetime(year, month, day, tzinfo=_UTC)
    return easter - timedelta(days=2)


def is_trading_day(dt: datetime) -> bool:
    """Return True if *dt*'s date is a US equity trading day.

    Weekends and major US holidays return False.
    """
    d = _to_utc(dt)
    if d.weekday() >= 5:  # Sat=5, Sun=6
        return False
    holiday_dates = {h.date() for h in _us_holidays(d.year)}
    return d.date() not in holiday_dates


def is_market_open(dt: datetime) -> bool:
    """Return True if the US equity market is in session at *dt*.

    Session: 9:30–16:00 ET, Mon–Fri, excluding holidays.
    """
    et = _to_et(dt)
    if et.weekday() >= 5:
        return False
    if not is_trading_day(dt):
        return False
    open_h, open_m = _MARKET_OPEN_HM
    close_h, close_m = _MARKET_CLOSE_HM
    minutes_since_midnight = et.hour * 60 + et.minute
    open_minutes = open_h * 60 + open_m
    close_minutes = close_h * 60 + close_m
    return open_minutes <= minutes_since_midnight < close_minutes


def get_market_session(dt: datetime) -> tuple[datetime, datetime] | None:
    """Return ``(open, close)`` in UTC for the trading day containing *dt*.

    If *dt*'s date is not a trading day, return ``None``.
    """
    if not is_trading_day(dt):
        return None
    et = _to_et(dt)
    et_date = et.date()
    open_et = datetime(
        et_date.year,
        et_date.month,
        et_date.day,
        _MARKET_OPEN_HM[0],
        _MARKET_OPEN_HM[1],
        tzinfo=_ET,
    )
    close_et = datetime(
        et_date.year,
        et_date.month,
        et_date.day,
        _MARKET_CLOSE_HM[0],
        _MARKET_CLOSE_HM[1],
        tzinfo=_ET,
    )
    return (open_et.astimezone(_UTC), close_et.astimezone(_UTC))


def is_earnings_blackout(symbol: str, dt: datetime) -> bool:
    """Stub: always returns False (no earnings calendar available)."""
    return False
