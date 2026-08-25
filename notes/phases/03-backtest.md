# Phase 3 — Backtest harness

Status: **NOT STARTED**

## Goal

Honest historical evaluation with shared live path objects, walk-forward/OOS reporting, integrity tests, and `promote_check.py`.

## Dependencies

Phase 2 exit criteria met.

## Deliverables

| Item | Path |
|------|------|
| Backtest engine | `src/backtest/` + `scripts/backtest.py` |
| Metrics / report | JSON + HTML under `output/` |
| Walk-forward | runner module |
| Integrity | `tests/test_no_lookahead.py` |
| Promotion | `scripts/promote_check.py`, `src/orchestration/promotion.py` |

## Implementation plan

1. Replay bars through feature → strategy → risk → PaperBroker.
2. Implement cost model + stress multiplier.
3. Compute metrics vs SPY benchmark download/seed.
4. Walk-forward windows; write `PromotionReport`.
5. Lock example thresholds in config; document tuning process.

## Tests required

- Synthetic path PnL
- Look-ahead test
- promote_check fails without report / failed metrics

## Exit criteria

- [ ] Report artifact generated for ≥1 strategy
- [ ] Strategy **promoted or explicitly rejected** with evidence (both OK)
- [ ] Integrity tests green
- [ ] Cost stress documented in report

## Non-goals

Live brokers; spending time on dashboard.

## Next

[Phase 4 — Broker parity](04-broker-parity.md)
