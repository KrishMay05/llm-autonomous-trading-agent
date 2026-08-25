# ADR 0002: Risk is code

## Status

Accepted

## Context

An LLM “risk manager” can hallucinate approval, ignore limits, or be manipulated by untrusted text. Live capital requires enforceable constraints.

## Decision

- Implement `HardRiskGate` and circuit breakers in `src/risk/` as deterministic code.
- Risk decisions emit machine-readable reason codes.
- No configuration path allows LLM or strategy to skip the gate.
- Unit tests must demonstrate rejects for: allowlist, max position %, max daily loss, stale data, max orders/day, PDT blocks (when enabled).

## Consequences

- Slightly less “autonomous” marketing story; much safer operations.
- Sizing logic lives next to risk, not in prompts.
- Operators tune limits via config, not prompt wording.
