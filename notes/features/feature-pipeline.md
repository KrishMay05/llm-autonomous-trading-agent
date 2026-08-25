# Feature: Feature pipeline

Phase ownership: **1**.

## Purpose

Turn raw bars/news into deterministic `FeatureVector`s for strategies and for audit digests.

## Scope

**In:** technical indicators, sentiment scores, market calendar / session flags, feature store assembly.  
**Out:** LLM-generated features as required inputs (LLM may add narrative separately).

## Contracts

### Technicals (`src/features/technicals.py`)

Minimum v1 set (extend carefully with versioned names):

- Returns / SMA / EMA (e.g. 20/50/200 on daily)
- RSI
- MACD (line, signal, hist)
- ATR / volatility estimate
- Volume vs average volume

All functions: `DataFrame → DataFrame` or series; document warm-up bars required.

### Sentiment (`src/features/sentiment.py`)

- Local VADER and/or FinBERT on headlines → score in `[-1, 1]`
- Aggregate last N hours per symbol
- Cache by `NewsItem.id`

### Calendar (`src/features/calendar.py`)

- US equity session open/close (handle early closes roughly or via calendar lib)
- Holidays
- Optional: earnings blackout window flag if earnings dates available

### Feature store (`src/features/feature_store.py`)

```python
def build_features(symbol: str, as_of: datetime, bars: list[Bar], news: list[NewsItem]) -> FeatureVector: ...
```

**Invariant:** `as_of` features use only bars with `ts_close <= as_of` and news `published_at <= as_of`.

## Implementation plan

1. Calendar helpers + tests around DST edges (America/New_York → store UTC).
2. Technicals with known golden values on fixture series.
3. Sentiment scoring + empty-news behavior (`0` or `nan` — pick one, document).
4. `build_features` assembly + schema list exported for strategies.

## Tests

- Look-ahead: shifting `as_of` backward never increases available future bars.
- NaN policy for warm-up period (strategy should HOLD if required features NaN).
- Session flag false outside RTH if configured for RTH-only.

## Exit criteria

- Feature matrix reproducible from seed data.
- Timezone/session tests green.

## Open risks

- Indicator library differences — pin versions; golden fixtures.
