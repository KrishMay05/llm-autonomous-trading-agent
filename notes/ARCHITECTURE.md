# Architecture

Status: **canonical design** (code may lag; implement toward this).

Related: [DOMAIN_MODELS.md](DOMAIN_MODELS.md), [features/portfolio-orchestration.md](features/portfolio-orchestration.md), ADRs 0001–0006.

## Goals

1. Reproducible trading decisions suitable for backtest ↔ paper ↔ live parity.
2. Hard safety boundary between “ideas” (strategy/LLM) and “orders” (risk + broker).
3. Swap data vendors and brokers without rewriting strategies.
4. Full auditability for every accept/reject/fill.

## Non-goals (near term)

- HFT / sub-second market making
- Unsupervised LLM placing unchecked live orders
- Multi-broker smart order routing across venues in v1

## Component map

```
src/config          → Settings (env), feature flags, risk limits config
src/data            → Provider interfaces + implementations + cache
src/features        → Deterministic feature vectors + calendar
src/strategies      → Strategy → StrategySignal
src/llm             → Optional research synthesizer (structured)
src/risk            → HardRiskGate, sizing, breakers, PDT
src/brokers         → Broker protocol + Paper/Alpaca/Robinhood
src/portfolio       → Local state + reconcile vs broker
src/orchestration   → Control loop + promotion checks
src/audit           → Append-only decision/execution records
src/api / frontend  → Operator control plane (later phases)
src/db              → Persistence (SQLite early → Postgres later)
```

## Control loop (single iteration)

1. **Clock / session check** — `features.calendar`: are we in a tradable window? earnings blackout?
2. **Pull data** — bars/quotes/news via providers; mark quote age.
3. **Build features** — technicals + sentiment scores; fail closed if required inputs missing/stale.
4. **Run strategies** — emit zero or more `StrategySignal` (side, strength, rationale).
5. **Optional LLM research** — `ResearchNote` (regime, veto *proposal* only); never a raw order.
6. **Allocate** — map signals → proposed quantities (`TradeProposal`).
7. **HardRiskGate** — approve/resize/reject; apply circuit breakers.
8. **Submit** — `TradeIntent` → `Broker.submit_order` with `client_order_id`.
9. **Reconcile** — broker positions/orders vs local portfolio; alert on drift.
10. **Audit** — persist full record (inputs hash, signals, risk, fills).

Schedule: start with **bar/session cadence** (e.g. end-of-bar or N-minute), not tick spam. LLM research on a **slower** cadence than strategy evaluation.

## Trust boundaries

```
┌─────────────────────────────────────────┐
│ Untrusted / advisory                     │
│  - LLM text and TradeProposal suggestions│
│  - News headlines, third-party scrapes   │
└──────────────────┬──────────────────────┘
                   │ structured only
                   ▼
┌─────────────────────────────────────────┐
│ Trusted computation                      │
│  - Features, strategies, risk, sizing    │
│  - Promotion checks                      │
└──────────────────┬──────────────────────┘
                   │ TradeIntent
                   ▼
┌─────────────────────────────────────────┐
│ Trusted I/O                              │
│  - Broker adapters (authenticated)       │
│  - Audit + portfolio stores              │
└─────────────────────────────────────────┘
```

## Failure modes (required behavior)

| Failure | Behavior |
|---------|----------|
| Stale quote / missing bar | Block new risk-increasing orders; audit `STALE_DATA` |
| Broker API 5xx / timeout | Retry with backoff for *reads*; do not double-submit without idempotency key |
| Partial fill | Update local state from broker; do not assume full qty |
| Reconcile mismatch | Halt new orders; raise alert; operator must resolve |
| LLM timeout / bad JSON | Continue without research enrichment; do not invent defaults that increase risk |
| Daily loss limit hit | `circuit_breakers` → halt or flatten per config; stay halted until next session or manual reset |

## Configuration surface (minimum)

See also `.env.example` (to be created in Phase 0).

| Key | Default | Meaning |
|-----|---------|---------|
| `LIVE_TRADING_ENABLED` | `false` | Master arm for any non-paper live routing |
| `BROKER` | `paper` | `paper` \| `alpaca` \| `robinhood_agentic` |
| `LLM_ENABLED` | `true` | If false, loop must still run |
| `SYMBOL_ALLOWLIST` | required | Comma-separated |
| `MAX_POSITION_PCT` | e.g. `0.10` | Per-symbol notional / equity |
| `MAX_DAILY_LOSS_PCT` | e.g. `0.02` | Circuit breaker |
| `MAX_QUOTE_AGE_SEC` | e.g. `120` | Stale data threshold (tune per venue) |

## Data flow parity (backtest ↔ live)

Backtest engine must construct the same `StrategySignal` → `HardRiskGate` → `TradeIntent` objects as live. Differences allowed only in:

- `Broker` implementation (simulated fills vs real)
- Data clock (historical bars vs wall clock)

Do **not** maintain a separate “backtest-only” strategy code path.

## Deployment topology (evolves)

| Stage | Topology |
|-------|----------|
| Phase 0–3 | Single process CLI + SQLite/files |
| Phase 4–6 | Long-running worker + Postgres; secrets via env |
| Phase 7+ | API + UI + worker; optional Redis |

## Security notes

- Scope API keys to least privilege; separate paper vs live credentials.
- Robinhood: funds only in **agentic** account; document disconnect runbook in Phase 5.
- Never log secrets or full account numbers; redact in audit if needed.
