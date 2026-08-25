# Feature: Hard risk gate

Phase ownership: **0** (core), refined in **2–6**.  
ADR: [0002](../adr/0002-risk-is-code.md).

## Purpose

Deterministic last-line defense between proposals and broker submits. LLMs and strategies cannot bypass it.

## Scope

**In:** allowlist, max position %, portfolio heat, max daily loss halt, max orders/day, stale quote check, optional PDT guard, kill switch, sizing helpers.  
**Out:** LLM judgment of “riskiness”; portfolio optimization beyond simple caps (can live in allocator).

## Contracts

### Settings (examples)

| Env / setting | Meaning |
|---------------|---------|
| `SYMBOL_ALLOWLIST` | Tradable symbols |
| `MAX_POSITION_PCT` | Max notional per symbol / equity |
| `MAX_PORTFOLIO_HEAT_PCT` | Sum of risk notions or gross exposure cap |
| `MAX_DAILY_LOSS_PCT` | From session start equity |
| `MAX_ORDERS_PER_DAY` | Includes rejects? **Count submits**; document choice |
| `MAX_QUOTE_AGE_SEC` | Stale data |
| `KILL_SWITCH` | If true, reject all new risk-increasing orders |
| `PDT_GUARD_ENABLED` | Block day trades when equity & broker flags require |

### API

```python
class HardRiskGate:
    def evaluate(
        self,
        proposal: TradeProposal,
        *,
        account: Account,
        positions: list[Position],
        quote: Quote,
        session: SessionState,
    ) -> RiskDecision: ...
```

`RiskDecision.status`: `APPROVE` | `RESIZE` | `REJECT`  
Reason codes (stable strings): `ALLOWLIST`, `MAX_POSITION`, `HEAT`, `DAILY_LOSS`, `MAX_ORDERS`, `STALE_DATA`, `KILL_SWITCH`, `PDT`, `INVALID_QTY`, `MISSING_QUOTE`.

### Sizing (`src/risk/sizing.py`)

- Input: strength, equity, volatility (optional), max pct.
- Output: raw qty before gate; gate may further resize.

### Circuit breakers (`src/risk/circuit_breakers.py`)

- Trip on daily loss, error rate, reconcile failure flag.
- Tripped state persisted for the session; clear only on configured condition (next session / manual).

## Implementation plan

1. Pure functions for each check + composite `HardRiskGate`.
2. Table-driven unit tests for every reason code.
3. Integrate into orchestration before `submit_order`.
4. Ensure audit always stores `RiskDecision` even on reject.

## Tests

- Each reason code independently triggers.
- `RESIZE` reduces qty to max allowed and passes.
- Sell/reduce orders: define policy — allow reducing even if kill switch is on for *increasing* risk only (document and test).
- PDT: mock account equity and day-trade count.

## Exit criteria

- Phase 0: at least allowlist, max position, kill switch, daily loss stub working with tests.
- Later phases: PDT + stale data + order rate fully wired to live quotes/session state.

## Open risks

- PDT rules are account-mode dependent; keep conservative.
- “Heat” definition must stay consistent between backtest and live.
