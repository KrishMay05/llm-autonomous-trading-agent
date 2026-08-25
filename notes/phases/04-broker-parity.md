# Phase 4 — Broker parity paper

Status: **NOT STARTED**

## Goal

Run the loop against Alpaca **paper** (REST parity), with order state machine, reconciliation, and circuit breakers for stale data / API failures.

## Dependencies

Phase 3 completed (strategy evaluated). Prefer a promoted strategy, but paper parity can proceed with a rejected strategy for engineering validation — **do not arm live**.

## Deliverables

| Item | Path |
|------|------|
| Alpaca adapter | `src/brokers/alpaca.py` |
| Order state handling | normalized statuses in loop |
| Reconcile | `src/portfolio/reconcile.py` |
| Breakers | wired to loop |
| Integration tests | marked `alpaca` |
| Ops notes | how to set keys in `.env` |

## Implementation plan

1. Implement AlpacaBroker mapping TradeIntent ↔ API.
2. Contract tests with mocks; optional live-paper integration.
3. Reconcile each loop; halt on drift.
4. Handle partial fills and rejects without crashing loop.
5. Multi-day paper soak (manual or scheduled job).

## Tests required

- Mocked Alpaca submit/get/cancel
- Reconcile mismatch → halt
- Stale quote → no risk-increasing order

## Exit criteria

- [ ] Multi-day Alpaca paper run with **zero unexplained position drift**
- [ ] Order state machine covers filled/partial/rejected/canceled
- [ ] Circuit breakers verified

## Non-goals

Robinhood live; public dashboard.

## Next

[Phase 5 — Robinhood Agentic](05-robinhood-agentic.md)
