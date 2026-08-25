# Phase 7 — Control plane & dashboard

Status: **NOT STARTED**

## Goal

FastAPI + React supervision: portfolio, trades, audit explorer, arm/disarm without SSH.

## Dependencies

Phase 4 recommended minimum; ideally after Phase 6 lessons so UI reflects real ops needs. See [features/control-plane.md](../features/control-plane.md).

## Deliverables

| Item | Path |
|------|------|
| API | `src/api/main.py` + routes |
| Frontend | `frontend/` |
| Auth | token or equivalent for mutating routes |
| Disarm | prominent + API wired to kill switch |

## Implementation plan

1. Read-only endpoints first (portfolio, trades, audit).
2. Disarm endpoint + UI button.
3. Arm endpoint gated by promotion + confirm.
4. Optional WebSocket.
5. Bind localhost / private network by default.

## Tests required

- API tests with mocks
- Disarm sets kill switch
- Arm rejected if promotion failed

## Exit criteria

- [ ] Operator can supervise PnL/positions/audit in UI
- [ ] Operator can disarm without SSH
- [ ] Mutating routes authenticated

## Non-goals

Public SaaS multi-user; mobile app.

## Next

[Phase 8 — Harden & expand](08-harden-expand.md)
