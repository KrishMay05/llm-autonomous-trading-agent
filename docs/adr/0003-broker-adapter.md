# ADR 0003: Broker adapter interface

## Status

Accepted

## Context

Bolting live trading onto a paper-only simulator late causes semantic drift (order states, partial fills, buying power). Multiple destinations are required: local paper, Alpaca, Robinhood Agentic.

## Decision

- All execution goes through `src/brokers/base.py` protocol: submit, cancel, get order, list positions, get account, optionally list open orders.
- Shared models in `src/brokers/models.py`.
- Strategies and risk never import vendor SDKs directly.
- Contract tests run against `PaperBroker` in CI; live adapters tested behind marks/secrets.

## Consequences

- Slightly more upfront abstraction.
- Enables Phase 4–5 without rewriting the loop.
- Vendor quirks stay isolated in adapter modules.
