# Notes index

Plans, specs, and ADRs for humans and coding agents.  
Root [`README.md`](../README.md) is a lean repo map — **this folder is where the detail lives.**

**Product intent:** [PRODUCT_PLAN.md](PRODUCT_PLAN.md)  
If PRODUCT_PLAN and a feature/phase doc disagree on *intent*, update the narrower doc to match PRODUCT_PLAN principles. If they disagree on *implementation detail*, prefer the feature/phase doc and amend PRODUCT_PLAN’s summary later.

---

## How to navigate (agents)

| If you need to… | Open |
|-----------------|------|
| Understand goals & roadmap summary | [PRODUCT_PLAN.md](PRODUCT_PLAN.md) |
| Know how to work in this repo safely | [AGENT_PLAYBOOK.md](AGENT_PLAYBOOK.md) |
| Understand system shape and control loop | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Implement Pydantic / domain contracts | [DOMAIN_MODELS.md](DOMAIN_MODELS.md) |
| Follow coding / testing conventions | [CONVENTIONS.md](CONVENTIONS.md) |
| Implement a subsystem | [features/](features/) (pick by area) |
| Know what to build next and exit criteria | [phases/](phases/) (start at `00`) |
| Understand *why* a decision was locked | [adr/](adr/) |
| Operate Robinhood Agentic safely | [runbooks/robinhood-agentic.md](runbooks/robinhood-agentic.md) |

**Default implementation order:** Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.  
Do not skip risk, broker protocol, or promotion gates to “ship faster.”

---

## Folder layout

```
notes/
├── README.md              ← this index
├── PRODUCT_PLAN.md        ← goals, principles, roadmap
├── AGENT_PLAYBOOK.md
├── ARCHITECTURE.md
├── DOMAIN_MODELS.md
├── CONVENTIONS.md
├── DOC_REVIEW.md
├── features/              ← subsystem contracts
├── phases/                ← Phase 0–8 plans
├── adr/                   ← architecture decisions
└── runbooks/              ← operator procedures
```

---

## Feature specs

| Doc | Covers |
|-----|--------|
| [features/brokers.md](features/brokers.md) | `Broker` protocol, Paper, Alpaca, Robinhood Agentic |
| [features/risk.md](features/risk.md) | Hard risk gate, sizing, circuit breakers, PDT |
| [features/data-providers.md](features/data-providers.md) | Market/news/macro providers, caching, production swap |
| [features/feature-pipeline.md](features/feature-pipeline.md) | Technicals, sentiment scores, calendar, feature store |
| [features/strategies.md](features/strategies.md) | Strategy interface, signals, registry, first strategy |
| [features/llm-research.md](features/llm-research.md) | Thin LLM layer, structured outputs, cost budgets |
| [features/portfolio-orchestration.md](features/portfolio-orchestration.md) | Control loop, intents, reconcile, promotion |
| [features/audit.md](features/audit.md) | Audit records, retention, post-trade review |
| [features/backtesting.md](features/backtesting.md) | Harness, walk-forward, integrity tests, promote_check |
| [features/control-plane.md](features/control-plane.md) | FastAPI + dashboard (Phase 7) |

---

## Phased implementation plans

| Phase | Doc | Exit criteria (summary) |
|-------|-----|-------------------------|
| 0 Foundations | [phases/00-foundations.md](phases/00-foundations.md) | Paper order works; risk can block it |
| 1 Data & features | [phases/01-data-features.md](phases/01-data-features.md) | Reproducible features; session tests |
| 2 Strategy + LLM | [phases/02-strategy-llm.md](phases/02-strategy-llm.md) | Auditable paper session; LLM optional |
| 3 Backtest | [phases/03-backtest.md](phases/03-backtest.md) | Strategy promoted *or* rejected with evidence |
| 4 Broker parity | [phases/04-broker-parity.md](phases/04-broker-parity.md) | Multi-day paper; zero unexplained drift |
| 5 Robinhood Agentic | [phases/05-robinhood-agentic.md](phases/05-robinhood-agentic.md) | Preview path works; live still disarmed |
| 6 Small live | [phases/06-small-live.md](phases/06-small-live.md) | Live window done; scale/hold/kill decision |
| 7 Control plane | [phases/07-control-plane.md](phases/07-control-plane.md) | Supervise/disarm without SSH |
| 8 Expand | [phases/08-harden-expand.md](phases/08-harden-expand.md) | Only after live stability |

---

## Architecture Decision Records

| ADR | Decision |
|-----|----------|
| [adr/0001-quant-first-llm-second.md](adr/0001-quant-first-llm-second.md) | Deterministic signals; LLM researches/explains |
| [adr/0002-risk-is-code.md](adr/0002-risk-is-code.md) | HardRiskGate cannot be LLM-bypassed |
| [adr/0003-broker-adapter.md](adr/0003-broker-adapter.md) | All execution behind `Broker` |
| [adr/0004-robinhood-agentic-target.md](adr/0004-robinhood-agentic-target.md) | Official Agentic MCP; dedicated account |
| [adr/0005-equities-first.md](adr/0005-equities-first.md) | Equities/ETFs before options/crypto complexity |
| [adr/0006-prove-edge-before-infra.md](adr/0006-prove-edge-before-infra.md) | Defer dashboard/workers until promotion gates |

---

## Runbooks

| Doc | Purpose |
|-----|---------|
| [runbooks/robinhood-agentic.md](runbooks/robinhood-agentic.md) | Dedicated account setup, preview, kill/disconnect (complete in Phase 5) |

---

## Meta

| Doc | Purpose |
|-----|---------|
| [DOC_REVIEW.md](DOC_REVIEW.md) | Checklist when editing notes |

---

## Doc conventions

- Each feature/phase doc has: **Purpose**, **Scope / non-goals**, **Contracts**, **Implementation plan**, **Tests**, **Exit criteria**, **Open risks**.
- Prefer absolute module paths like `src/risk/limits.py` matching the planned tree.
- Status badges in phase docs: `NOT STARTED` | `IN PROGRESS` | `DONE` — update when code lands.
- Do not invent unofficial Robinhood scraping as a “workaround” in notes or code.
