"""yfinance-backed market-data provider.

Uses the ``yfinance`` library to fetch historical OHLCV bars and real-time
quotes.  All numeric fields are converted to :class:`Decimal` and all
datetimes are normalized to UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd

from src.brokers.models import Bar, Quote

SOURCE = "yfinance"


def _to_utc(ts: Any) -> datetime:
    """Convert a pandas / numpy timestamp to a tz-aware UTC datetime."""
    if ts is None:
        # Should not happen for well-formed data, but stay robust.
        return datetime.now(tz=timezone.utc)
    # pandas Timestamp → py datetime
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    dt = ts if isinstance(ts, datetime) else datetime.fromtimestamp(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_decimal(value: Any) -> Decimal:
    """Safely coerce a numpy/pandas scalar to Decimal."""
    if value is None:
        return Decimal("0")
    # Convert numpy scalar → python scalar first
    if hasattr(value, "item"):
        value = value.item()
    return Decimal(str(value))


class YFinanceMarketDataProvider:
    """``MarketDataProvider`` implementation backed by yfinance."""

    source: str = SOURCE

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Download OHLCV bars via ``yfinance.download`` and map to ``Bar``."""
        import yfinance as yf

        # yfinance accepts plain dates or ISO strings for period bounds
        df = yf.download(
            symbol,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval=timeframe,
            progress=False,
            auto_adjust=False,
        )

        if df is None or df.empty:
            return []

        bars: list[Bar] = []
        for ts_open, row in df.iterrows():
            # ts_open is a pandas Timestamp (the row index)
            open_ts = _to_utc(ts_open)
            # infer bar close ts from the interval — fall back to open + 1 unit
            close_ts = open_ts  # yfinance does not return close ts; keep open for now
            # Prefer columns with capitalised names; handle MultiIndex too
            def _get(key: str) -> Any:
                col = key if key in row else key.capitalize()
                if col in row:
                    return row[col]
                # MultiIndex: (key, symbol)
                try:
                    return row[key]
                except KeyError:
                    return 0

            bars.append(
                Bar(
                    symbol=symbol,
                    timeframe=timeframe,
                    ts_open=open_ts,
                    ts_close=close_ts,
                    open=_to_decimal(_get("Open")),
                    high=_to_decimal(_get("High")),
                    low=_to_decimal(_get("Low")),
                    close=_to_decimal(_get("Close")),
                    volume=_to_decimal(_get("Volume")),
                    source=SOURCE,
                ),
            )

        return bars

    def get_quote(self, symbol: str) -> Quote:
        """Fetch the latest bid/ask/last via ``yfinance.Ticker``."""
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info: dict[str, Any] = {}
        try:
            info = ticker.info  # noqa: B009
        except Exception:  # noqa: BLE001
            info = {}

        now = datetime.now(tz=timezone.utc)

        def _dec(key: str) -> Decimal | None:
            val = info.get(key)
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except Exception:  # noqa: BLE001
                return None

        return Quote(
            symbol=symbol,
            bid=_dec("bid"),
            ask=_dec("ask"),
            last=_dec("currentPrice") or _dec("regularMarketPrice") or _dec("lastPrice"),
            ts=now,
            received_at=now,
            source=SOURCE,
        )
