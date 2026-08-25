# Feature: Portfolio & orchestration

Phase ownership: **0** (minimal loop), **2** (full path), **4** (reconcile), **6** (promotion arming).

## Purpose

Schedule the control loop, turn signals into proposals, apply risk, submit, reconcile, and gate live promotion.

## Scope

**In:** `orchestration/loop.py`, allocator, portfolio state, reconcile, `promotion.py`, CLI `scripts/run_agent.py`.  
**Out:** Distributed Celery (until needed), UI arming (Phase 7 can wrap same functions).

## Contracts

### Control loop

Pseudo:

```
for each tick/schedule:
  if not session_tradable: audit skip; return
  reconcile()  # fail closed on hard mismatch
  for symbol in allowlist:
    features = build_features(...)
    signal = strategy.evaluate(...)
    note = maybe_research(...)  # slower cadence
  proposals = allocate(signals, account, positions, note)
  for proposal in proposals:
    decision = risk_gate.evaluate(...)
    audit(decision)
    if decision.approved:
      order = broker.submit(intent)
      audit(execution)
  reconcile()
```

### Allocator

- Start simple: one symbol one order; size from `sizing.py` × signal strength.
- Ignore BUY if already at max position.
- Prefer flat list of `TradeProposal` sorted by strength.

### Portfolio state (`src/portfolio/state.py`)

- Local view of positions, cash, session PnL.
- Updated from fills + reconcile snapshots.

### Reconcile (`src/portfolio/reconcile.py`)

- Compare local vs `broker.list_positions()` within qty epsilon.
- On mismatch: set breaker, alert, skip new orders.

### Promotion (`src/orchestration/promotion.py`)

Checks (configurable thresholds):

1. Backtest gate file / last walk-forward report passed
2. Paper sessions count ≥ N with clean reconcile
3. Risk tests marked mandatory passed (CI artifact or local)
4. `LIVE_TRADING_ENABLED` requested but still need manual confirm in Phase 6 script
5. Broker is not paper when arming live

## Implementation plan

1. Phase 0: single-shot loop paper buy blocked by risk test path.
2. Phase 2: multi-symbol loop + audit JSONL.
3. Phase 4: reconcile hard fail.
4. Phase 6: `promote_check.py` + arm script.

## Tests

- Loop with mocked broker/strategy.
- Reconcile mismatch raises halt.
- Promotion fails when live flag true but gates incomplete.

## Exit criteria

- See phase docs 0/2/4/6.

## Open risks

- Scheduler drift / overlapping loop runs — use lockfile or single-worker assumption.
