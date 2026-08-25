# Phase 8 — Harden & expand

Status: **NOT STARTED**

## Goal

Only after live stability: production market data, optional options (when supported), more strategies/portfolios, CI nightly backtests, deployment with secret injection, optional IBKR.

## Dependencies

Phase 6 decision was **scale** or **hold with stability** — not **kill due to systemic bugs**. Fix systemic issues before expanding scope.

## Deliverables (pick in priority order)

1. Production `MarketDataProvider` (Polygon/Alpaca data/etc.)
2. Nightly backtest workflow + artifact retention
3. Deployment runbook (VPS/cloud), secrets, monitoring
4. Additional strategies / risk profiles
5. Options module **if** data + Robinhood/Alpaca options support ready
6. Optional `IBKRBroker` for multi-asset needs
7. Crypto only via **official** Robinhood Crypto API if explicitly desired

## Implementation plan

1. Replace yfinance in production config; keep as dev fallback.
2. Harden CI: lint, typecheck, unit, nightly backtest.
3. Add strategies behind registry; each needs Phase 3-style evaluation before live.
4. Options: new feature spec + ADR amendment before coding.
5. IBKR: new adapter behind same Broker protocol.

## Exit criteria

- [ ] Production data path used for live
- [ ] Nightly backtests running
- [ ] Deploy/runbook documented
- [ ] Any new asset class has its own promotion evidence

## Explicitly still out of scope unless new ADR

- RL-as-primary-edge
- Unofficial Robinhood automation
- “Guaranteed alpha” claims
