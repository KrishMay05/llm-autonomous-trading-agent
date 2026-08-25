# Product plan

> Canonical product intent for this repo. Root [`README.md`](../README.md) stays lean; implementation detail lives under [`notes/`](README.md).

A production-oriented trading system: quantitative signals + LLM research, hard risk guardrails, paper trading with broker-parity execution, and a clear path to live capital via **Robinhood Agentic Trading** (and Alpaca for API-first development).

---

## Overview

This project builds an **autonomous trading agent** that:

1. **Ingests** market data, news, and (later) options/macro feeds through a provider abstraction — free APIs for prototyping, paid/low-latency feeds for live capital
2. **Scores** opportunities with deterministic features and strategies first; uses LLMs for research synthesis, regime context, and explainability — not as the sole unchecked decision-maker
3. **Enforces** risk in code (position limits, drawdown kills, PDT awareness, kill switches) — LLMs may advise, but they cannot override hard gates
4. **Paper-trades** through a broker interface that mirrors live order semantics (rejects, partial fills, slippage models)
5. **Goes live** behind the same interface: Robinhood Agentic Trading (dedicated agentic account) and/or Alpaca for REST-first development
6. **Explains** every decision with a full audit trail suitable for post-trade review

### Product intent (not a demo)

The long-term goal is a system **you actually fund** — starting with small live capital after edge is evidenced, scaling only when risk and ops hold up. Portfolio career value (pipeline engineering, XAI, agentic systems) is a byproduct, not the primary success metric.

**Success metric:** positive expected value after costs, with controlled drawdowns, on out-of-sample / walk-forward evaluation — then on paper with broker-parity fills — then on small live size.

Honest constraint: most retail strategies fail after costs and overfitting. This repo is structured to **fail fast on bad ideas** and only promote strategies that survive the promotion gates below.

---

## Critical design principles

These correct common failure modes in “LLM trading bot” projects:

| Principle | Why it matters |
|-----------|----------------|
| **Quant decides, LLM explains (and sometimes researches)** | Pure LLM buy/sell loops are non-deterministic, expensive, latency-sensitive, and hard to backtest honestly. Signals and sizing must be reproducible. |
| **Risk is code, not a prompt** | An LLM “Risk Manager” can hallucinate approval. Hard limits (max position %, max daily loss, max orders/day, symbol allowlist) live in deterministic modules and short-circuit execution. |
| **Broker adapter from day one** | Do not bolt on live trading later. `Broker` interface → `PaperBroker`, `AlpacaBroker`, `RobinhoodAgenticBroker`. Same order/position models everywhere. |
| **Prove edge before infra theater** | Dashboard, Celery, and multi-agent LangChain graphs do not make money. Data quality, strategy research, and walk-forward backtests do. Infra scales after promotion gates pass. |
| **Live capital blast radius** | Robinhood Agentic Trading uses a **dedicated agentic account** with only deposited funds. Never give an agent access to your full net worth. |
| **Cost discipline** | Track LLM $/decision and $/day. If inference cost approaches expected edge, simplify agents or cache research. |
| **Equities first** | Options and multi-leg strategies need better data, Greeks accuracy, and (for Robinhood) post-beta product support. Earn trust on liquid US equities/ETFs first. |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         TRADING CONTROL LOOP                              │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ Market   │  │  News /  │  │ Options  │  │ Macro /  │                 │
│  │ Data     │  │ Sentiment│  │ (later)  │  │ Calendar │                 │
│  │ Providers│  │ Providers│  │          │  │          │                 │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                 │
│       └─────────────┴─────────────┴─────────────┘                        │
│                         │                                                 │
│                         ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              FEATURE + STRATEGY LAYER (deterministic)         │       │
│  │  Technicals │ Sentiment scores │ Regime tags │ Signal scores  │       │
│  └──────────────────────────┬───────────────────────────────────┘       │
│                             │                                             │
│              ┌──────────────┴──────────────┐                              │
│              ▼                             ▼                              │
│  ┌─────────────────────┐     ┌─────────────────────────┐                │
│  │ LLM RESEARCH LAYER  │     │ HARD RISK GATE (code)   │                │
│  │ Regime narrative,   │     │ Sizing caps, DD kill,   │                │
│  │ news synthesis,     │     │ allowlist, PDT, order   │                │
│  │ optional override   │     │ rate limits, kill switch│                │
│  │ proposals (gated)   │     └───────────┬─────────────┘                │
│  └──────────┬──────────┘                 │                              │
│             └──────────────┬─────────────┘                              │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              PORTFOLIO / ORDER INTENT                         │       │
│  │  Structured TradeIntent (Pydantic) + rationale text           │       │
│  └──────────────────────────┬───────────────────────────────────┘       │
│                             │                                             │
│                             ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              BROKER ADAPTER                                   │       │
│  │  Paper │ Alpaca (paper/live) │ Robinhood Agentic (MCP)        │       │
│  │  Orders, fills, positions, account buying power               │       │
│  └──────────────────────────┬───────────────────────────────────┘       │
│                             │                                             │
│                             ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │         AUDIT, RECONCILIATION, MONITORING, DASHBOARD          │       │
│  │  Trade + reasoning log │ broker vs local state │ alerts │ UI  │       │
│  └──────────────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
```

### Decision flow

```
Market/News → Features → StrategySignal(s)
                              │
                              ├→ LLM Research (optional enrichment / veto proposal)
                              │
                              ▼
                     HardRiskGate (code) ──REJECT→ AuditLogger
                              │ APPROVE (sized)
                              ▼
                     TradeIntent → Broker.submit()
                              │
                              ▼
                     Fill / Reject → Portfolio reconcile → AuditLogger
```

---

## Multi-agent / module design

Prefer **few LLM calls on a schedule** (e.g. session open, hourly research) over five LLM agents on every bar. Deterministic modules do the high-frequency work.

| Module | Type | Role | Notes |
|--------|------|------|-------|
| **Market Analyst** | Code (+ optional LLM narrative) | Trends, RSI/MACD, S/R, volatility | Indicators computed in pandas/ta; LLM summarizes only if needed |
| **Sentiment Analyst** | Code + LLM | News scoring; LLM for ambiguous headlines | Cache embeddings; don’t re-score unchanged headlines |
| **Options Strategist** | Deferred | IV, Greeks, unusual activity | Gate behind equities edge + better options data + broker support |
| **Risk Gate** | **Code only** | Position sizing, exposure, drawdown, PDT, kill switch | Non-negotiable; unit-tested; no LLM bypass |
| **Portfolio Allocator** | Code | Turns approved signals into TradeIntents | Can use simple rules first (equal risk, vol targeting) |
| **Research Synthesizer** | LLM | Cross-asset narrative, regime, “what changed” | Outputs structured notes, not raw orders |
| **Audit Logger** | Code | Persists inputs, signals, risk decisions, fills | Immutable append-only style records |

LLM agents that *propose* trades must emit structured `TradeProposal` objects that still pass `HardRiskGate`.

---

## Broker strategy (Robinhood path)

### Target: Robinhood Agentic Trading

As of May 2026, Robinhood offers **Agentic Trading**: connect a third-party AI agent to a **dedicated agentic brokerage account** via Robinhood’s Trading MCP. Equities launched in beta first; options/crypto/futures support is expected to expand. Safety model: agent only spends funds deposited in that account; user can disconnect anytime.

**Implications for this repo:**

- Treat Robinhood as a first-class **execution destination**, not a weekend add-on
- Implement `RobinhoodAgenticBroker` against the official Trading MCP / agentic docs — **no unofficial session scrapers** for live money (ToS and account risk)
- Use the dedicated agentic account as the blast-radius boundary
- Expect product constraints during beta (equities-only initially; preview/approval flows; MCP session semantics) and design the control loop to tolerate them

### Parallel: Alpaca (and optional IBKR later)

| Broker | Use in this project |
|--------|---------------------|
| **PaperBroker** | Local sim with configurable latency/slippage/commission; unit tests |
| **Alpaca** | Best REST paper↔live parity for development, CI, and non-Robinhood live |
| **Robinhood Agentic (MCP)** | Primary personal live destination you care about |
| **Robinhood Crypto API** | Separate official API — only if/when crypto strategies are in scope |
| **IBKR** | Later, if multi-asset / futures / international are required |

**Never** hardcode order submission to a single vendor. All execution goes through `brokers.base.Broker`.

### Live promotion gates (capital)

Do not enable live order routing until all are true:

1. Strategy passes walk-forward / out-of-sample criteria agreed in config (Sharpe, max DD, turnover, costs)
2. ≥ N paper sessions with **broker-parity** adapter (Alpaca paper or Robinhood paper/preview if available) with reconciliation clean
3. Kill switch, max daily loss, and max position % verified in integration tests
4. Secrets in env/secret store; keys scoped; agentic account funded with **only** risk capital
5. Manual “arm live” flag (explicit config), default off

---

## Data sources

### Prototyping (free / cheap)

| Source | Data | Caveat |
|--------|------|--------|
| **yfinance** | OHLCV, basic options | Delayed / brittle; fine for notebooks, not live truth |
| **Finnhub** | News, earnings | Respect free-tier limits; cache aggressively |
| **FRED** | Macro (rates, CPI, etc.) | Good for regime features; low frequency |
| **NewsAPI / GDELT** | Headlines | Noisy; needs filtering before LLM spend |
| **Alpha Vantage** | Indicators | Free tier is too small for a real loop — treat as optional |

### Production path (required before serious live size)

| Need | Direction |
|------|-----------|
| Equities bars / quotes | Polygon (or successor), Alpaca market data, or broker stream |
| Corporate actions | Explicit split/dividend handling in backtests |
| News | Vendor with stable ToS + caching; don’t scrape |
| Options (later) | Paid chain + Greeks; do not trust toy free chains for sizing |

`data/` modules must implement a **provider interface** so swapping yfinance → Polygon is a config change, not a rewrite.

---

## Tech stack

### Core
- **Python 3.11+**
- **Pydantic v2** — settings, TradeIntent, agent structured outputs
- **LLM providers** — OpenAI / Anthropic / local (Ollama) behind a thin client; LangChain only where it earns its complexity (prefer explicit orchestration early)

### Data & research
- **pandas / numpy**
- **pandas-ta** (prefer over brittle TA-Lib installs unless needed)
- **FinBERT / VADER** — local sentiment where possible to cut API cost
- **scikit-learn** — lightweight regime/classifier helpers (optional)

### Execution & risk
- First-party **broker adapters** (Paper, Alpaca, Robinhood Agentic)
- Deterministic **risk** package (not an LLM agent)

### Infrastructure (stage by need)
- **Early:** SQLite or Postgres + APScheduler / cron — enough for research and paper
- **Later:** Redis cache, Celery/worker, FastAPI control plane, React dashboard
- **Docker Compose** when services multiply; don’t block Phase 0–2 on it

### DevOps
- GitHub Actions — lint, typecheck, unit tests, scheduled backtests
- pytest, ruff, mypy, pre-commit

---

## Project structure

```
llm-autonomous-trading-agent/
├── README.md                       # lean repo map
├── LICENSE
├── CONTRIBUTING.md
├── notes/                          # plans, specs, ADRs (this folder)
├── pyproject.toml
├── docker-compose.yml              # when infra is needed
├── .env.example
├── .github/workflows/
│   ├── ci.yml
│   └── nightly-backtest.yml
│
├── src/
│   ├── config/
│   │   └── settings.py             # env-driven; live arm flags default false
│   │
│   ├── data/
│   │   ├── providers/              # yfinance, polygon, finnhub, ...
│   │   ├── market_data.py
│   │   ├── news_feed.py
│   │   ├── macro_feed.py
│   │   └── cache.py
│   │
│   ├── features/
│   │   ├── technicals.py
│   │   ├── sentiment.py
│   │   ├── calendar.py             # market hours, holidays, earnings blackouts
│   │   └── feature_store.py
│   │
│   ├── strategies/
│   │   ├── base.py                 # Strategy → Signal
│   │   ├── momentum.py             # example deterministic strategies
│   │   └── registry.py
│   │
│   ├── llm/
│   │   ├── client.py
│   │   ├── research_synthesizer.py
│   │   └── prompts/
│   │
│   ├── risk/
│   │   ├── limits.py               # hard caps from config
│   │   ├── sizing.py
│   │   ├── circuit_breakers.py     # daily loss, error rate, stale data
│   │   └── pdt.py                  # pattern day trader awareness
│   │
│   ├── brokers/
│   │   ├── base.py                 # Broker protocol
│   │   ├── paper.py
│   │   ├── alpaca.py
│   │   ├── robinhood_agentic.py    # official MCP / agentic integration
│   │   └── models.py               # Order, Fill, Position, Account
│   │
│   ├── portfolio/
│   │   ├── state.py
│   │   └── reconcile.py            # local vs broker positions
│   │
│   ├── orchestration/
│   │   ├── loop.py                 # scheduled control loop
│   │   └── promotion.py            # checks before live routing
│   │
│   ├── audit/
│   │   └── logger.py
│   │
│   ├── api/                        # Phase: control plane
│   │   └── main.py
│   │
│   └── db/
│       ├── models.py
│       └── migrations/
│
├── frontend/                       # after paper loop is trustworthy
├── tests/
│   ├── test_risk_gate.py           # must be strict
│   ├── test_brokers_paper.py
│   ├── test_strategies.py
│   ├── test_no_lookahead.py        # backtest integrity
│   └── conftest.py
│
├── scripts/
│   ├── run_agent.py
│   ├── backtest.py
│   ├── promote_check.py            # print pass/fail for live gates
│   └── seed_data.py
│
└── notebooks/
    ├── 01_market_data_exploration.ipynb
    ├── 02_sentiment_analysis.ipynb
    ├── 03_strategy_research.ipynb
    └── 04_backtesting_results.ipynb
```

---

## Quick start

### Prerequisites

- Python 3.11+
- (Optional) Docker for Postgres/Redis later
- LLM API key and/or Ollama
- (Later) Alpaca keys; Robinhood Agentic account + MCP credentials

### Setup

```bash
git clone https://github.com/yourusername/llm-autonomous-trading-agent.git
cd llm-autonomous-trading-agent
cp .env.example .env   # fill keys; LIVE_TRADING_ENABLED=false
pip install -e ".[dev]"
```

### Paper run

```bash
python scripts/run_agent.py --tickers AAPL,MSFT,SPY --broker paper
```

### Dashboard (when implemented)

```bash
uvicorn src.api.main:app --reload
cd frontend && npm install && npm run dev
```

---

## Backtesting (honesty requirements)

```bash
python scripts/backtest.py \
  --start 2020-01-01 \
  --end 2025-12-31 \
  --tickers AAPL,MSFT,NVDA,SPY \
  --initial-capital 100000 \
  --costs realistic \
  --report output/backtest_report.html
```

### Metrics that matter

- Total return vs benchmark (e.g. SPY) **after** fees/slippage
- Sharpe / Sortino
- Max drawdown and time under water
- Win rate, profit factor, expectancy
- Turnover and estimated capacity
- Exposure / concentration

### Integrity checks (non-optional)

- **No look-ahead:** features at `t` use only data ≤ `t`
- **Walk-forward** or purged CV — not a single in-sample fit
- **Corporate actions** handled
- **Cost model** stress test (2× slippage) still acceptable
- Drop vanity metrics like “LLM graded its own reasoning quality” as a performance proxy — coherence ≠ edge

---

## Example audit record

```json
{
  "timestamp": "2026-08-25T14:30:00Z",
  "ticker": "AAPL",
  "decision": "BUY",
  "strategy_signal": {
    "name": "trend_pullback_v1",
    "score": 0.74,
    "rationale": "Price above 200DMA; RSI 48 after pullback; volume dry-up into support."
  },
  "llm_research": {
    "regime": "risk_on",
    "notes": "Product-cycle headlines net positive; no earnings within 5 sessions.",
    "proposed_veto": false
  },
  "risk_gate": {
    "status": "APPROVE",
    "max_shares": 75,
    "approved_shares": 50,
    "checks": ["allowlist", "max_position_pct", "daily_loss", "pdt", "stale_data"]
  },
  "action": {
    "type": "MARKET_BUY",
    "quantity": 50,
    "ticker": "AAPL",
    "estimated_price": 178.50
  },
  "execution": {
    "broker": "paper",
    "fill_price": 178.52,
    "slippage": 0.02,
    "commission": 0.0,
    "fill_time": "2026-08-25T14:30:01Z"
  }
}
```

---

## Testing

```bash
pytest
pytest --cov=src --cov-report=html
pytest tests/test_risk_gate.py -v
pytest tests/test_no_lookahead.py -v
```

Priority tests: risk gate, order idempotency, reconciliation, backtest look-ahead, broker adapter contract tests.

---

## Roadmap (exit-criteria driven)

No calendar-week promises — each phase ends when **exit criteria** pass.

### Phase 0 — Foundations
- [ ] Repo skeleton (`pyproject.toml`, settings, logging)
- [ ] `Broker` protocol + `PaperBroker`
- [ ] `HardRiskGate` with unit tests
- [ ] Config flags: `LIVE_TRADING_ENABLED=false`, broker selection
- [ ] `.env.example` and secrets discipline

**Exit:** one CLI paper loop can place a simulated order that is blocked when risk limits trip.

### Phase 1 — Data & features
- [ ] Market data provider interface + yfinance implementation
- [ ] Caching and rate-limit handling
- [ ] Technical feature pipeline + market calendar
- [ ] Swap-ready stub for a production data vendor

**Exit:** reproducible feature matrix for a ticker set; tests for timezone/session correctness.

### Phase 2 — Strategy + LLM research (thin)
- [ ] ≥1 deterministic strategy with clear rules
- [ ] Signal → risk → TradeIntent path
- [ ] LLM research synthesizer (structured output) that cannot bypass risk
- [ ] Audit log to disk/DB

**Exit:** paper session produces auditable trades; disabling LLM does not break the loop.

### Phase 3 — Backtest harness
- [ ] Event-driven or bar-based backtest aligned with live intents
- [ ] Walk-forward runner + cost model
- [ ] Look-ahead tests; report HTML/JSON
- [ ] `promote_check.py` encodes numeric gates

**Exit:** at least one strategy either promoted or explicitly rejected with evidence (both outcomes are success).

### Phase 4 — Broker parity paper
- [ ] Alpaca paper adapter (REST parity)
- [ ] Position reconciliation job
- [ ] Order state machine (submitted / partial / filled / rejected / canceled)
- [ ] Stale-data and API-failure circuit breakers

**Exit:** multi-day paper run with zero unexplained position drift.

### Phase 5 — Robinhood Agentic integration
- [ ] `RobinhoodAgenticBroker` via official Trading MCP / agentic docs
- [ ] Dedicated agentic account only; documented setup
- [ ] Map MCP constraints (beta asset classes, preview/approval) into the loop
- [ ] Dry-run / preview mode before autonomous submits
- [ ] Kill switch + disconnect runbook

**Exit:** successful preview or small paper-equivalent path; live still disarmed by default.

### Phase 6 — Small live capital
- [ ] Arming checklist (`promote_check` + manual confirm)
- [ ] Tiny max notional / daily loss
- [ ] Alerting (email/push) on fills, rejects, breaker trips
- [ ] Post-trade review workflow from audit logs

**Exit:** defined live window completed; decide scale-up, hold, or kill based on real fills vs expectation.

### Phase 7 — Control plane & dashboard
- [ ] FastAPI: portfolio, trades, audit, agent status, arm/disarm
- [ ] React dashboard: PnL, positions, reasoning explorer
- [ ] WebSocket updates optional

**Exit:** operator can supervise and disarm without SSH.

### Phase 8 — Harden & expand (only after live stability)
- [ ] Production market data vendor
- [ ] Options strategies when data + Robinhood support exist
- [ ] Additional strategies / portfolios (risk profiles)
- [ ] CI nightly backtests; deployment story (VPS/cloud) with secret injection
- [ ] Optional IBKR adapter for multi-asset

### Explicitly deferred / out of scope for now
- Reinforcement learning fine-tuning as a path to edge (research distraction until baselines work)
- Unofficial Robinhood mobile-session automation
- Mobile app
- “Beat the market” marketing claims without promotion-gate evidence

---

## Risk, compliance, and ops checklist

- [ ] Allowlist of tradable symbols
- [ ] Max position % and max portfolio heat
- [ ] Max daily loss → flatten or halt
- [ ] Max orders per day / cooldown after N rejects
- [ ] PDT / account-equity awareness for US margin accounts under $25k
- [ ] No trading on stale quotes or failed feature builds
- [ ] Idempotent client order IDs
- [ ] Reconcile local vs broker on every loop
- [ ] Human arm/disarm; default safe
- [ ] Audit retention for post-mortems
- [ ] LLM cost budgets and truncation of context

---

## Disclaimer

This software can lose money. It is **not** financial advice. Past backtests and paper results do **not** guarantee live performance.

Paper trading is the default. Live trading — including via **Robinhood Agentic Trading** — involves significant risk, including loss of the entire amount deposited in an agentic account. AI components can err, misread news, or act on incomplete data. You are responsible for monitoring, for complying with broker terms and applicable law, and for any capital you allocate.

---

## License

MIT — See [LICENSE](LICENSE)

---

## Contributing

Pull requests welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## Links

- **Notes index:** [README.md](README.md)
- **Agent playbook:** [AGENT_PLAYBOOK.md](AGENT_PLAYBOOK.md)
- **Phased plans:** [phases/](phases/)
- **Robinhood Agentic Trading:** [Robinhood newsroom announcement](https://robinhood.com/us/en/newsroom/robinhood-is-now-open-to-agents/)
