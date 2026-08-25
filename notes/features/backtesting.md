# Feature: Backtesting & promotion metrics

Phase ownership: **3**.

## Purpose

Honest historical evaluation using the **same** signal → risk → intent path as live, plus promotion gates that block wishful live trading.

## Scope

**In:** bar-based (or event) harness, cost model, walk-forward, reports, look-ahead tests, `promote_check.py`.  
**Out:** LLM-as-judge of strategy quality as a gate metric.

## Contracts

### Harness (`scripts/backtest.py` / `src/backtest/`)

- Replay timeline; at each `as_of`, build features → strategies → risk → simulated broker.
- Initial capital, allowlist, strategy ids from CLI/config.
- Cost model: commission + slippage_bps; stress mode `2x`.

### Metrics

- Total return, benchmark-relative return (SPY)
- Sharpe, Sortino
- Max drawdown, time under water
- Win rate, profit factor, expectancy
- Turnover, avg exposure

### Walk-forward

- Rolling train/test windows (even if strategy is rule-based: use for parameter selection only when params are tuned)
- For fixed-rule strategies: still report **out-of-sample** segments and stability across regimes

### Integrity

- `tests/test_no_lookahead.py` constructs features at t and asserts no use of t+1 bars
- Corporate actions: document limitation; prefer adjusted closes from provider consistently

### Promotion thresholds (example defaults — tune in config)

| Check | Example |
|-------|---------|
| OOS Sharpe | > 0.5 (after costs) |
| Max DD | < 20% |
| Stress 2x slippage | still Sharpe > 0 or DD within bound |
| Min trades | ≥ 30 OOS (avoid tiny sample) |

`PromotionReport.passed` requires all enabled checks.

## Implementation plan

1. Simulate broker reuse of `PaperBroker` with historical quotes.
2. Metrics module + HTML/JSON report.
3. Walk-forward runner.
4. Wire `scripts/promote_check.py` to read last report + paper reconcile stats.

## Tests

- Known synthetic price path → expected PnL within epsilon.
- Look-ahead test fails if pipeline cheated (mutation test optional).
- promote_check fails on empty/missing report.

## Exit criteria (Phase 3)

- At least one strategy **promoted or rejected with evidence** (either is success).
- Integrity tests green.

## Open risks

- Survivorship bias in universe — start with fixed allowlist including losers.
- Overfitting via human iteration — keep a locked evaluation window.
