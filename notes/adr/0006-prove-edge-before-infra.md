# ADR 0006: Prove edge before infra theater

## Status

Accepted

## Context

Dashboards, Celery, Redis, and elaborate multi-agent graphs consume time without proving expected value after costs.

## Decision

- Phases 0–3 prioritize: skeleton, data/features, strategy+risk+audit, backtest/promotion.
- FastAPI/React/heavy workers wait until Phase 7 (after broker-parity paper and preferably after small live learning in Phase 6 — UI may start in parallel only if Phase 4 exit is met).
- Early persistence may be SQLite/JSONL.

## Consequences

- Less impressive early demos; better capital outcomes.
- Agents must resist “just adding a dashboard” unless the active phase requires it.
