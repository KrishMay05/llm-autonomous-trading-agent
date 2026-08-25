# LLM Autonomous Trading Agent

Quant signals + thin LLM research, **code-enforced risk**, paper trading, then live capital via **Robinhood Agentic Trading** (Alpaca for API parity).

**Not a demo project** — build order is: prove edge → broker-parity paper → tiny live size. Live trading stays **off by default**.

---

## Start here

| Role | Go to |
|------|--------|
| Browse the plan | [`notes/`](notes/) |
| Implement next | [`notes/phases/00-foundations.md`](notes/phases/00-foundations.md) |
| Agent rules | [`notes/AGENT_PLAYBOOK.md`](notes/AGENT_PLAYBOOK.md) |
| Product intent | [`notes/PRODUCT_PLAN.md`](notes/PRODUCT_PLAN.md) |

---

## Repository map

```
llm-autonomous-trading-agent/
├── README.md                 ← you are here (lean index)
├── LICENSE
├── CONTRIBUTING.md
├── notes/                    ← plans, specs, ADRs, runbooks
├── src/                      ← application code
│   ├── api/                  ← local operator UI (FastAPI)
│   └── orchestration/        ← control loop + session
├── frontend/                 ← black / grey / white operator UI
├── tests/
├── scripts/run_agent.py      ← CLI and --ui entry point
├── pyproject.toml
├── .env.example
└── .env.working_example      ← copy that actually loads under pydantic-settings
```

Plans and ADRs still live in [`notes/`](notes/).

---

## Principles (short)

1. **Quant decides, LLM explains** — reproducible signals; LLM is research/narrative only.
2. **Risk is code** — hard limits cannot be prompt-bypassed.
3. **Broker adapter from day one** — Paper → Alpaca → Robinhood Agentic.
4. **Equities first** — options/crypto later.
5. **Dedicated agentic account only** for Robinhood live blast radius.

---

## Quick start

```bash
python3 -m pip install -e ".[dev]"
cp .env.working_example .env   # LIVE_TRADING_ENABLED=false; paper broker
```

List settings (`SYMBOL_ALLOWLIST`, `STRATEGIES`) must be JSON arrays. A CSV value like `SPY,AAPL` will fail at startup. `.env.example` documents the knobs; `.env.working_example` is a loadable copy.

**CLI (one paper iteration, JSON to stdout):**

```bash
python3 scripts/run_agent.py --tickers SPY,AAPL --broker paper
```

**Operator UI (black / grey / white, localhost):**

```bash
python3 scripts/run_agent.py --ui
```

Opens [http://127.0.0.1:8765](http://127.0.0.1:8765). Shows equity, cash, day P&L, stub marks, paper holdings, and a decision log (signal → risk → broker). **Run iteration** steps the loop; **Disarm** sets the kill switch.

```bash
python3 scripts/run_agent.py --ui --no-browser --ui-port 8765
```

Phase 0 uses a paper broker and stub quotes. No live APIs are required. `LIVE_TRADING_ENABLED` stays false.

Details: [`notes/phases/`](notes/phases/).

---

## License & disclaimer

MIT — see [LICENSE](LICENSE).

Software can lose money. Not financial advice. Paper is default; live (including Robinhood Agentic) can lose the entire agentic-account balance.
