# Engineering conventions

## Language & packaging

- Python **3.11+**
- Package layout: `src/` with install via `pip install -e ".[dev]"` (`pyproject.toml`)
- Type-check with **mypy** (gradual OK; new modules should be typed)
- Lint/format with **ruff**

## Code style

- Prefer explicit functions/classes over deep framework magic.
- **LangChain** only when it clearly reduces complexity; default to direct LLM client + Pydantic parsing.
- No bare `except:`; catch specific exceptions at I/O boundaries.
- Logging: stdlib `logging`; include `client_order_id` / `symbol` in execution logs.
- Do not use `print` in library code.

## Testing

| Layer | Tools | Focus |
|-------|-------|-------|
| Unit | pytest | Risk gate, sizing, feature pure functions, signal math |
| Contract | pytest | Every `Broker` implements the protocol |
| Integrity | pytest | No look-ahead in backtests |
| Optional integration | marked tests | Alpaca paper / network — skip in CI without secrets |

Commands (once project exists):

```bash
pytest
pytest tests/test_risk_gate.py -v
pytest tests/test_no_lookahead.py -v
ruff check src tests
mypy src
```

## Git & safety

- Never commit `.env`, API keys, account ids, or raw broker dumps with PII.
- Default branch workflows must not arm live trading.
- Feature branches: descriptive; keep live credentials out of CI logs.

## Config

- All runtime config via pydantic-settings / env.
- Dangerous flags require explicit true + ideally a second confirmation in Phase 6 scripts.
- Document new env vars in `.env.example` **and** [ARCHITECTURE.md](ARCHITECTURE.md) table if operator-facing.

## Documentation updates

When you change a public contract (models, broker methods, risk codes):

1. Update [DOMAIN_MODELS.md](DOMAIN_MODELS.md) or the feature spec.
2. Update phase exit criteria checkboxes if a deliverable moved.
3. Add/amend an ADR only for cross-cutting decisions.

## Dependency policy

- Prefer well-maintained libs; pin in lockfile when added.
- Avoid heavy ML stacks until a phase needs them.
- `pandas-ta` preferred over system TA-Lib unless required.
