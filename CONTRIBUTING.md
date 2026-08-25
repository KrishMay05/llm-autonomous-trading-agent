# Contributing

## For humans and coding agents

1. Read [README.md](README.md) design principles.
2. Follow [docs/AGENT_PLAYBOOK.md](docs/AGENT_PLAYBOOK.md).
3. Implement against the active [phase plan](docs/phases/) and related [feature specs](docs/features/).
4. Do not skip risk gates, broker adapters, or live-default-off settings.
5. Update docs when you change contracts ([docs/DOC_REVIEW.md](docs/DOC_REVIEW.md)).

## PRs

- Prefer small vertical slices (signal → risk → broker → audit).
- Include tests for risk and broker behavior you touch.
- Never commit secrets or enable live trading in CI.
