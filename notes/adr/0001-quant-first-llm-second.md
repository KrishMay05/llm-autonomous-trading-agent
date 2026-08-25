# ADR 0001: Quant-first, LLM-second

## Status

Accepted

## Context

LLM-only trading loops are non-deterministic, expensive, hard to backtest fairly, and prone to prompt injection via news text. The product goal is deployable capital, not a chat demo.

## Decision

- **Primary decisions** (side, eligibility, baseline sizing inputs) come from deterministic strategies and code.
- **LLMs** produce `ResearchNote`: regime narrative, optional advisory veto list, explanations.
- Disabling LLM (`LLM_ENABLED=false`) must leave the control loop functional.
- LLM output never becomes a `TradeIntent` without passing `HardRiskGate`.

## Consequences

- Backtests can replay strategies without paying for tokens.
- Need disciplined prompt/versioning for research notes when used.
- Multi-agent LangChain graphs are out of scope until a measured need appears.
