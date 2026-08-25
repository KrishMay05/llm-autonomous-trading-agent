# Phase 0 — Foundations

Status: **NOT STARTED**

## Goal

Stand up installable package, settings, logging, `Broker` + `PaperBroker`, minimal `HardRiskGate`, and a CLI that can simulate an order and prove risk can block it.

## Dependencies

None (first phase).

## Deliverables

| Item | Path / artifact |
|------|-----------------|
| Packaging | `pyproject.toml`, `src/` package |
| Settings | `src/config/settings.py`, `.env.example` |
| Models | `src/brokers/models.py`, risk/strategy stubs as needed |
| Paper broker | `src/brokers/paper.py`, `base.py`, `factory.py` |
| Risk | `src/risk/limits.py`, gate entrypoint |
| CLI | `scripts/run_agent.py --broker paper` |
| Tests | `tests/test_risk_gate.py`, `tests/test_brokers_paper.py` |
| License/ignore | `LICENSE` if missing, `.gitignore` |

## Implementation plan

1. Create `pyproject.toml` with pytest/ruff/mypy/pydantic/pandas deps (keep lean).
2. Implement settings: `LIVE_TRADING_ENABLED=false`, `BROKER=paper`, allowlist, risk caps.
3. Implement shared broker models + PaperBroker.
4. Implement HardRiskGate with allowlist, max position, kill switch (minimum).
5. CLI: load settings → fake quote → proposal → gate → submit or reject → print result.
6. Unit tests for gate + paper submit idempotency.

## Tests required

- Risk reject on allowlist miss
- Risk reject on kill switch
- Paper fill increases position
- Duplicate client_order_id safe

## Exit criteria

- [ ] `pip install -e ".[dev]"` works
- [ ] `python scripts/run_agent.py --tickers SPY --broker paper` runs
- [ ] Demonstrably blocked order when limits trip (test or CLI mode)
- [ ] Live trading cannot be enabled accidentally (default false; test assert)

## Non-goals

Dashboard, real market data, LLM, Alpaca/Robinhood.

## Next

[Phase 1 — Data & features](01-data-features.md)
