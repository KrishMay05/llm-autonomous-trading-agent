# Phase 6 — Small live capital

Status: **NOT STARTED**

## Goal

Arm live trading with tiny notional only after promotion checks and manual confirmation; alert on fills/rejects/breakers; complete a defined live window and decide scale / hold / kill.

## Dependencies

- Phase 5 exit met
- Phase 3 promotion evidence for the strategy being armed
- Phase 4-style reconcile discipline on the live broker path (preview soak)

## Deliverables

| Item | Artifact |
|------|----------|
| Arming flow | `scripts/arm_live.py` or documented `promote_check` + env flip |
| Tight limits | live-specific max notional / daily loss overrides |
| Alerting | email/webhook/push on fill, reject, breaker |
| Post-trade review | checklist using audit logs |
| Decision record | short markdown note of scale/hold/kill outcome |

## Implementation plan

1. `promote_check.py` must pass; print actionable failures.
2. Manual confirm phrase / interactive confirm in arm script.
3. Set extreme-low caps for first window (e.g. max $X per order, $Y daily loss).
4. Alerting hooks (even if just webhook to a personal channel).
5. Run defined window (e.g. N sessions); then forced review before raising caps.

## Tests required

- Arm script refuses when promotion failed
- Arm script refuses when `BROKER=paper`
- Disarm / kill switch immediately blocks new buys

## Exit criteria

- [ ] Live window completed under tiny caps
- [ ] Written decision: scale up, hold, or kill
- [ ] No unresolved reconcile breaks
- [ ] Alerts observed to work at least once (test page)

## Non-goals

Scaling to full account; marketing claims; options.

## Next

[Phase 7 — Control plane](07-control-plane.md) (can start UI earlier only if Phase 4 done and it does not block live learning)
