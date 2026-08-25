# Feature: Control plane & dashboard

Phase ownership: **7** (do not build early — [ADR 0006](../adr/0006-prove-edge-before-infra.md)).

## Purpose

Operator supervision: see positions/PnL/audit, arm/disarm, without SSH.

## Scope

**In:** FastAPI routes, authn basic, React UI, optional WebSocket.  
**Out:** Public multi-tenant SaaS; mobile app.

## Contracts

### API (minimum)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/portfolio` | Equity, cash, positions |
| GET | `/trades` | Recent orders/fills |
| GET | `/audit/{id}` | Full reasoning record |
| GET | `/agent/status` | Loop state, breakers, broker name |
| POST | `/agent/run` | Trigger one iteration (dev) |
| POST | `/agent/disarm` | Set kill switch / disable live |
| POST | `/agent/arm` | Only if promotion passed — still confirm |

All mutating routes: protected (token or local-only bind initially).

### UI

- Portfolio view, trade history, audit explorer (click trade → reasoning)
- Big **DISARM** control
- No need for fancy marketing visuals

## Implementation plan

1. FastAPI wrapping portfolio/audit stores + kill switch.
2. React + TS client.
3. Optional WS for order updates.
4. Deploy behind SSH tunnel or private network first.

## Tests

- API unit tests with mocked portfolio.
- Disarm endpoint sets kill switch true.
- Arm rejected when promotion failed.

## Exit criteria

- Operator can disarm without server shell access.
- Audit explorer shows Phase 2+ record shape.

## Open risks

- Accidentally exposing arm endpoint — default bind localhost; auth required.
