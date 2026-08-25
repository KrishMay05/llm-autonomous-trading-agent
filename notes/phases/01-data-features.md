# Phase 1 — Data & features

Status: **NOT STARTED**

## Goal

Provider interfaces + yfinance (or equivalent) implementation, caching, technical/sentiment/calendar pipelines, reproducible feature vectors.

## Dependencies

Phase 0 exit criteria met.

## Deliverables

| Item | Path |
|------|------|
| Providers | `src/data/providers/`, `market_data.py`, `news_feed.py` |
| Cache | `src/data/cache.py` |
| Features | `technicals.py`, `sentiment.py`, `calendar.py`, `feature_store.py` |
| Seed script | `scripts/seed_data.py` |
| Tests | calendar/session, technicals fixtures, no-future-data assertions |
| Stub | Production vendor stub behind factory |

## Implementation plan

1. Define `MarketDataProvider` / `NewsProvider` protocols.
2. Implement YFinance provider + fixture-based CI path (no network required for unit tests).
3. Cache historical bars to disk for offline runs.
4. Build technicals + calendar; wire `build_features`.
5. Minimal news→sentiment path (VADER OK).
6. Document corporate-action limitations in feature spec.

## Tests required

- UTC normalization
- Feature `as_of` look-ahead guard
- Cache hit behavior (mocked)
- Factory selects provider from settings

## Exit criteria

- [ ] Reproducible feature matrix for allowlisted tickers from seed/cache
- [ ] Timezone/session tests green
- [ ] Strategy-ready `FeatureVector` without LLM
- [ ] Provider swappable via config (stub acceptable)

## Non-goals

Walk-forward backtest UI; live broker adapters beyond paper.

## Next

[Phase 2 — Strategy + LLM](02-strategy-llm.md)
