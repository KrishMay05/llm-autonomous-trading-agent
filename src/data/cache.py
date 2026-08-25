"""Disk cache for market data (bars + quotes).

Keys are deterministic hashes of ``provider + method + parameters``.
Values are pickled ``list[Bar]``, ``list[NewsItem]``, or ``Quote`` objects.
Each entry carries a TTL measured in seconds; expired entries are treated
as misses.
"""

from __future__ import annotations

import hashlib
import pickle
import time
from pathlib import Path
from typing import Any

from src.brokers.models import Bar, Quote


# Default TTLs (seconds)
TTL_BARS: int = 86_400      # 24 h — historical bars rarely change
TTL_QUOTE: int = 60        # 60 s — quotes are real-time-ish
TTL_NEWS: int = 3_600      # 1 h — news headline cache


class DataCache:
    """A lightweight pickled-object disk cache.

    Each key is hashed (sha256 → hex digest) to form the file name.  The
    stored payload is ``(value, expires_at)`` where ``expires_at`` is an
    epoch timestamp.
    """

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir: Path = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── key helpers ──────────────────────────────────────────────
    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{self._hash_key(key)}.pkl"

    # ── raw primitives ───────────────────────────────────────────
    def get(self, key: str) -> Any | None:
        """Return the cached value for *key* or ``None`` on miss/expiry."""
        path = self._path(key)
        if not path.exists():
            return None
        try:
            with path.open("rb") as fh:
                value, expires_at = pickle.load(fh)  # noqa: S301
        except Exception:  # noqa: BLE001
            return None
        if time.time() > expires_at:
            # expired — remove stale file
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store *value* under *key* with a TTL of *ttl* seconds."""
        path = self._path(key)
        expires_at = time.time() + ttl
        with path.open("wb") as fh:
            pickle.dump((value, expires_at), fh)  # noqa: S301

    def exists(self, key: str) -> bool:
        """Return ``True`` if *key* exists and has not expired."""
        return self.get(key) is not None

    def clear(self) -> None:
        """Remove every cache file."""
        for child in self.cache_dir.glob("*.pkl"):
            try:
                child.unlink()
            except OSError:
                pass

    # ── high-level helpers ────────────────────────────────────────
    @staticmethod
    def _bars_key(
        provider: str,
        symbol: str,
        timeframe: str,
        start: Any,
        end: Any,
    ) -> str:
        return f"{provider}_bars_{symbol}_{timeframe}_{start}_{end}"

    def get_bars(
        self,
        provider: str,
        symbol: str,
        timeframe: str,
        start: Any,
        end: Any,
    ) -> list[Bar] | None:
        key = self._bars_key(provider, symbol, timeframe, start, end)
        value = self.get(key)
        return value if isinstance(value, list) else None

    def put_bars(
        self,
        provider: str,
        symbol: str,
        timeframe: str,
        start: Any,
        end: Any,
        bars: list[Bar],
    ) -> None:
        key = self._bars_key(provider, symbol, timeframe, start, end)
        self.set(key, bars, TTL_BARS)

    @staticmethod
    def _quote_key(provider: str, symbol: str) -> str:
        return f"{provider}_quote_{symbol}"

    def get_quote(self, provider: str, symbol: str) -> Quote | None:
        key = self._quote_key(provider, symbol)
        value = self.get(key)
        return value if isinstance(value, Quote) else None

    def put_quote(self, provider: str, symbol: str, quote: Quote) -> None:
        key = self._quote_key(provider, symbol)
        self.set(key, quote, TTL_QUOTE)
