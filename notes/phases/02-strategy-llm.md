# Phase 2 — Strategy + LLM research (thin)

Status: **NOT STARTED**

## Goal

Deterministic strategy → risk → TradeIntent → paper broker, with optional LLM `ResearchNote`, and JSONL audit. Loop works with LLM disabled.

## Dependencies

Phase 1 exit criteria met.

## Deliverables

| Item | Path |
|------|------|
| Strategies | `src/strategies/base.py`, `trend_pullback_v1` (or equiv), `registry.py` |
| LLM | `src/llm/client.py`, `research_synthesizer.py`, `prompts/research_v1.*` |
| Orchestration | `src/orchestration/loop.py` |
| Audit | `src/audit/logger.py` |
| Portfolio | basic `state.py` |
| Tests | strategy unit tests, LLM soft-fail, audit round-trip |

## Implementation plan

1. Implement strategy protocol + first strategy with config params.
2. Allocator → TradeProposal → HardRiskGate → PaperBroker.
3. Add LLM synthesizer behind `LLM_ENABLED`; validate structured output.
4. Advisory veto optional via `LLM_VETO_ENABLED` (default false).
5. Audit JSONL for every decision.
6. CLI runs multi-ticker paper session.

## Tests required

- Strategy golden vectors
- LLM invalid JSON → continue
- `LLM_ENABLED=false` path identical for submits except missing research section
- Audit written on reject

## Exit criteria

- [ ] Paper session produces auditable trades/rejects
- [ ] Disabling LLM does not break the loop
- [ ] No LLM path bypasses risk (code review + test)

## Non-goals

Alpaca; walk-forward harness (Phase 3); dashboard.

## Next

[Phase 3 — Backtest](03-backtest.md)
