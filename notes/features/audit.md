# Feature: Audit trail

Phase ownership: **2** (JSONL), SQL in later infra.

## Purpose

Immutable-enough history of why the system traded or refused — for debugging, promotion evidence, and post-trade review.

## Scope

**In:** `AuditRecord` writer, query helpers, retention policy.  
**Out:** Public sharing of logs; using “LLM graded coherence” as performance.

## Contracts

- Writer appends one JSON object per decision cycle per symbol (or per proposal).
- Include: timestamps, signal, research, risk, intent ids, execution, `inputs_digest`.
- Never store API keys; redact account identifiers.

### Storage

| Stage | Backend |
|-------|---------|
| Early | `logs/audit/YYYYMMDD.jsonl` |
| Later | Postgres table `audit_records` |

### Query

- By `client_order_id`, symbol, date range.
- Phase 7 API: `GET /audit/{id}`.

## Implementation plan

1. Pydantic `AuditRecord` + JSONL sink.
2. Hook every reject/approve/fill.
3. Optional SQLite index for queries.
4. Retention: e.g. keep 365 days locally; document.

## Tests

- Round-trip serialize.
- Reject path still writes audit.
- Redaction unit test for sensitive fields if present.

## Exit criteria (Phase 2)

- Paper session produces reviewable audit files matching README shape.

## Open risks

- Disk growth — rotation policy.
- Hash stability of `inputs_digest` when feature set evolves — version the digest schema.
