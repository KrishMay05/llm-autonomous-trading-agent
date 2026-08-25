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
├── notes/                    ← plans, specs, ADRs, runbooks (read these)
│   ├── README.md             ← notes index
│   ├── PRODUCT_PLAN.md       ← goals, principles, roadmap summary
│   ├── AGENT_PLAYBOOK.md
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_MODELS.md
│   ├── CONVENTIONS.md
│   ├── features/             ← subsystem contracts
│   ├── phases/               ← Phase 0–8 exit criteria
│   ├── adr/                  ← locked decisions
│   └── runbooks/
│
├── src/                      ← application code (Phase 0+)
├── tests/
├── scripts/
├── frontend/                 ← Phase 7+
├── notebooks/
├── pyproject.toml            ← forthcoming in Phase 0
├── .env.example
└── .github/workflows/
```

Code directories appear as phases land. Until then, **`notes/` is the working source of truth.**

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
# After Phase 0 scaffolding exists:
cp .env.example .env          # LIVE_TRADING_ENABLED=false
pip install -e ".[dev]"
python scripts/run_agent.py --tickers SPY --broker paper
```

Details: [`notes/phases/`](notes/phases/).

---

## License & disclaimer

MIT — see [LICENSE](LICENSE).

Software can lose money. Not financial advice. Paper is default; live (including Robinhood Agentic) can lose the entire agentic-account balance.
