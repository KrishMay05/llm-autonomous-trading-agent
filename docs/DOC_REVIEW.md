# Documentation review checklist

Use this when updating `docs/` so future agents keep quality high.

## Completeness

- [ ] [docs/README.md](README.md) links resolve
- [ ] Every Phase 0–8 has exit criteria and non-goals
- [ ] Every major `src/` area has a feature spec
- [ ] ADRs cover locked cross-cutting decisions
- [ ] Domain models match feature contracts (field names)

## Consistency with root README

- [ ] Quant-first / risk-as-code / broker adapters / equities-first unchanged
- [ ] Robinhood path is official Agentic MCP + dedicated account
- [ ] No unofficial scraper guidance
- [ ] Infra deferred until promotion gates (ADR 0006)

## Agent navigability

- [ ] Playbook lists hard invariants
- [ ] Phase docs point to next phase
- [ ] Feature docs list tests and exit criteria
- [ ] Open risks are explicit (no silent assumptions)

## Safety

- [ ] Live default-off documented everywhere relevant
- [ ] Kill switch / disarm mentioned for live phases
- [ ] Secrets handling stated

## When to amend ADRs

Only for changes to locked decisions (e.g. allowing options earlier). Prefer feature/phase edits for tactical detail.
