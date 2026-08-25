# Runbook: Robinhood Agentic Trading

Status: **STUB — complete during Phase 5** when wiring the official MCP.

## Purpose

Operator steps to connect this agent to a **dedicated** Robinhood agentic account safely.

## Preconditions

- [ ] Phases 0–4 complete; Phase 5 adapter implemented against **current** official docs
- [ ] Strategy promotion evidence exists (or preview-only mode)
- [ ] `LIVE_TRADING_ENABLED=false` until Phase 6 arming
- [ ] Funds set aside are **risk capital only**

## Setup (fill with exact UI/API steps at implementation time)

1. Create/open Robinhood **Agentic Trading** account (separate from primary portfolio).
2. Deposit only the intended risk budget.
3. Create MCP / agentic credentials per Robinhood docs.
4. Put credentials in `.env` (never commit).
5. Set `BROKER=robinhood_agentic` and `ROBINHOOD_PREVIEW_ONLY=true`.
6. Run one preview iteration; verify activity feed in Robinhood apps.

## Kill / disconnect

1. Application: set `KILL_SWITCH=true` or call disarm API/CLI.
2. Robinhood: disconnect agent in-app (authoritative cut).
3. Verify no open orders remain that you do not want.
4. Rotate/delete credentials if compromise suspected.

## Incident: unexpected orders

1. Disconnect agent in Robinhood immediately.
2. Export audit logs for the window.
3. Reconcile positions vs audit intents.
4. Do not re-arm until root cause documented.

## References

- [ADR 0004](../adr/0004-robinhood-agentic-target.md)
- [Phase 5](../phases/05-robinhood-agentic.md)
- Robinhood newsroom: Agentic Trading announcement (verify latest support docs when implementing)
