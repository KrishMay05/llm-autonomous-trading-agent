# Feature: Strategies

Phase ownership: **2** (first strategy), more in **8**.  
ADR: [0001](../adr/0001-quant-first-llm-second.md), [0005](../adr/0005-equities-first.md).

## Purpose

Deterministic, versioned signal generation that can run identically in backtest and live.

## Scope

**In:** `Strategy` protocol, registry, ≥1 real strategy (e.g. trend pullback), HOLD when uncertain.  
**Out:** LLM-only strategies; options strategies in v1.

## Contracts

```python
class Strategy(Protocol):
    id: str  # e.g. trend_pullback_v1

    def evaluate(self, features: FeatureVector, context: StrategyContext) -> StrategySignal: ...
```

`StrategyContext`: account snapshot optional, position for symbol, research note optional (read-only).

### Registry

- `src/strategies/registry.py` maps id → class
- Config `STRATEGIES=trend_pullback_v1` (comma list)

### First strategy suggestion: `trend_pullback_v1`

Illustrative rules (tune in research; lock params in config):

- **Universe:** allowlist liquid US equities/ETFs
- **Bias:** price above long SMA (e.g. 200d) → long-only regime
- **Entry:** RSI recovered from oversold band / pullback to intermediate MA + volume confirmation
- **Exit/SELL:** break of intermediate MA or RSI overbought mean-reversion exit — define clearly
- **Else:** HOLD

Emit `strength` in `0..1` from how many conditions fired; rationale string lists conditions.

## Implementation plan

1. Protocol + registry + HOLD-only stub strategy for wiring tests.
2. Implement `trend_pullback_v1` with parameters in settings.
3. Unit tests with synthetic feature vectors (no network).
4. Hook into orchestration.

## Tests

- Golden feature vectors → expected side
- NaN features → HOLD
- Strategy id stable in signals/audit

## Exit criteria (Phase 2)

- ≥1 deterministic strategy produces signals in paper loop.
- Disabling LLM does not change ability to signal (may change veto enrichment only).

## Open risks

- Overfitting when tuning on short windows — rely on Phase 3 walk-forward before live.
