# ADR 0005: Equities first

## Status

Accepted

## Context

Options need accurate chains/Greeks, complex order types, and (for Robinhood) post-beta product support. Premature options work delays proving any edge.

## Decision

- v1 strategies trade **liquid US equities and ETFs** only.
- Options strategist modules and multi-leg orders are **deferred** until: equities promotion gates pass, production options data exists, and broker support is confirmed.
- Symbol allowlists should favor high liquidity names for early live size.

## Consequences

- Faster path to honest backtest and paper metrics.
- Some README “options chain” ideas remain future work — do not implement in Phases 0–6.
