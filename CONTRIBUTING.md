# Contributing

## For humans and coding agents

1. Skim the lean [README.md](README.md) repo map.
2. Read [notes/PRODUCT_PLAN.md](notes/PRODUCT_PLAN.md) and [notes/AGENT_PLAYBOOK.md](notes/AGENT_PLAYBOOK.md).
3. Implement against the active [phase plan](notes/phases/) and related [feature specs](notes/features/).
4. Do not skip risk gates, broker adapters, or live-default-off settings.
5. Update notes when you change contracts ([notes/DOC_REVIEW.md](notes/DOC_REVIEW.md)).

## PRs

- Prefer small vertical slices (signal → risk → broker → audit).
- Include tests for risk and broker behavior you touch.
- Never commit secrets or enable live trading in CI.
