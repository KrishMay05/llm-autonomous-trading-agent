# Agent playbook

Instructions for coding agents implementing this repository.

## Mission

Build a **fundable** trading control loop: deterministic strategies + thin LLM research, **code-enforced risk**, broker adapters (Paper → Alpaca → Robinhood Agentic), honest backtests, then small live capital in a **dedicated** Robinhood agentic account.

Career/demo polish is secondary. Edge evidence and safety are primary.

## Before writing code

1. Read [PRODUCT_PLAN.md](PRODUCT_PLAN.md) principles (quant-first, risk-as-code, broker-from-day-one).
2. Open the **current phase** doc under [phases/](phases/) — do not jump ahead past unmet exit criteria.
3. Open the matching [features/](features/) specs for modules you will touch.
4. Skim relevant [ADRs](adr/) so you do not re-litigate locked decisions.

## Hard invariants (never violate)

| Invariant | Enforcement |
|-----------|-------------|
| `LIVE_TRADING_ENABLED` defaults **false** | Settings + tests |
| LLM cannot submit orders or override risk | Architecture: intents only after `HardRiskGate` |
| All orders go through `brokers.base.Broker` | No direct HTTP to brokers outside adapters |
| No unofficial Robinhood session scrapers | Use official Agentic MCP / documented APIs only |
| Risk limits are code | `src/risk/*` unit tests must cover blocks |
| Backtests forbid look-ahead | `tests/test_no_lookahead.py` |
| Secrets never committed | `.env` gitignored; `.env.example` has placeholders |

## Preferred work style

- **Small vertical slices** that preserve the full path: data → signal → risk → broker → audit.
- **Fail closed:** on stale data, API errors, or parse failures → no new risk-increasing orders.
- **Idempotent orders:** every submit has a stable `client_order_id`.
- **Structured types:** Pydantic models from [DOMAIN_MODELS.md](DOMAIN_MODELS.md); avoid `dict` soup at boundaries.
- **Tests with behavior:** especially risk rejects, reconcile mismatches, and broker contract tests.

## What not to build yet

Unless the active phase explicitly requires it:

- React dashboard, Celery, Redis clustering
- Options strategies / multi-leg orders
- RL fine-tuning
- Multi-agent LangChain graphs calling an LLM five times per bar
- Mobile apps

See [adr/0006-prove-edge-before-infra.md](adr/0006-prove-edge-before-infra.md).

## Definition of done for a task

1. Code matches the feature contract.
2. Unit/integration tests listed in the phase/feature doc pass.
3. Phase exit criteria still hold (or are closer with remaining items listed).
4. Docs updated if you changed a contract or ADR outcome.
5. Live flags remain safe-by-default.

## When stuck

- Prefer **rejecting / halting** over clever recovery that increases position risk.
- Prefer **Alpaca paper** for broker-parity debugging before Robinhood MCP edge cases.
- Prefer **disabling LLM** to isolate strategy/risk bugs (`LLM_ENABLED=false`).
