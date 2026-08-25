# Feature: Data providers

Phase ownership: **1** (interfaces + yfinance + cache), production vendor in **8** (stub earlier).

## Purpose

Fetch bars, quotes, news, macro data behind interfaces so strategies do not depend on yfinance forever.

## Scope

**In:** provider protocols, yfinance market implementation, Finnhub/GDELT-style news (or one news source), FRED macro optional, caching, rate-limit handling, production stub.  
**Out:** Scraping sites in violation of ToS; treating free delayed data as live truth.

## Contracts

### `MarketDataProvider`

```python
class MarketDataProvider(Protocol):
    def get_bars(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Bar]: ...
    def get_quote(self, symbol: str) -> Quote: ...
```

### `NewsProvider`

```python
class NewsProvider(Protocol):
    def get_headlines(self, symbol: str | None, since: datetime) -> list[NewsItem]: ...
```

### `MacroProvider` (optional early)

```python
class MacroProvider(Protocol):
    def get_series(self, series_id: str, start: datetime, end: datetime) -> pandas.DataFrame: ...
```

### Cache (`src/data/cache.py`)

- Keyed by provider + method + params.
- TTL by data type (bars longer than quotes).
- Respect vendor rate limits; backoff on 429.

### Settings

- `MARKET_DATA_PROVIDER=yfinance|polygon|alpaca_data|...`
- API keys per vendor
- `MAX_QUOTE_AGE_SEC` consumed by risk, sourced from `Quote.received_at`

## Implementation plan

1. Protocols + `YFinanceMarketDataProvider`.
2. Disk or SQLite cache for historical bars (backtest seed).
3. News provider with aggressive caching (LLM cost!).
4. Stub `PolygonMarketDataProvider` raising `NotImplementedError` with clear message — or minimal implement if keys present.
5. `scripts/seed_data.py` to download history for backtests.

## Tests

- Mock HTTP / fixture bars → parse to `Bar`.
- Cache hit avoids second fetch.
- Timezone: all `Bar.ts_*` UTC.
- Provider factory resolves from settings.

## Exit criteria (Phase 1)

- Reproducible bar download for allowlisted tickers.
- Feature pipeline can run offline from cache/seed.
- Swap provider via config without strategy changes (stub OK).

## Open risks

- yfinance breakage — isolate and keep fixtures for CI.
- Corporate actions: document limitation until production vendor; backtest must note split risk.
