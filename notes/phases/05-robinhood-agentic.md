# Phase 5 — Robinhood Agentic integration

Status: **NOT STARTED**

## Goal

Official `RobinhoodAgenticBroker` via Trading MCP / Agentic Trading docs, dedicated account setup, preview/dry-run, kill/disconnect runbook. Live remains disarmed by default.

## Dependencies

Phase 4 exit criteria met (broker-parity discipline proven on Alpaca paper).

## Deliverables

| Item | Path |
|------|------|
| Adapter | `src/brokers/robinhood_agentic.py` |
| Settings | MCP/agentic credentials env vars in `.env.example` |
| Preview mode | config `ROBINHOOD_PREVIEW_ONLY=true` default true |
| Runbook | `notes/runbooks/robinhood-agentic.md` (complete with this phase) |
| Tests | mocks of MCP tool calls; reject unsupported assets |

## Implementation plan

1. Read current official Robinhood Agentic / Trading MCP documentation at implementation time (APIs evolve).
2. Map Broker protocol methods to MCP tools/APIs.
3. Enforce equities-only if beta requires; clear errors otherwise.
4. Preview/dry-run path before autonomous submits.
5. Document: create dedicated agentic account, fund minimally, connect agent, disconnect/kill steps.
6. Keep `LIVE_TRADING_ENABLED=false`; even with Robinhood selected, require Phase 6 arming.

## Tests required

- Unsupported symbol/asset → reject
- Preview mode does not call irreversible submit (or asserts preview API)
- Factory returns Robinhood adapter when configured
- Credentials missing → fail fast at startup

## Exit criteria

- [ ] Successful preview or paper-equivalent path against official integration
- [ ] Runbook merged
- [ ] Live still default-disarmed
- [ ] No unofficial scraper dependencies

## Non-goals

Funding meaningful capital; options trading.

## Next

[Phase 6 — Small live](06-small-live.md)

## Security checklist

- [ ] Agentic account ≠ primary brokerage nest egg
- [ ] Secrets in env/secret manager only
- [ ] Disconnect tested once manually
