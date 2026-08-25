# Domain models

Canonical Pydantic v2 contracts. Implement under `src/` (suggested modules noted).  
Agents: treat these field names as the shared language across features.

Related: [ARCHITECTURE.md](ARCHITECTURE.md), [features/brokers.md](features/brokers.md), [features/risk.md](features/risk.md).

## Conventions

- Money/prices: `Decimal` for order quantities/prices at broker boundary; `float` OK inside research features if documented.
- Timestamps: timezone-aware UTC (`datetime` with `tzinfo=UTC`).
- Enums: `str, Enum` for JSON friendliness.
- All models immutable where practical (`model_config = ConfigDict(frozen=True)` ) for audit hashing.

---

## Market data (`src/data` / `src/brokers/models.py` overlap)

### `Bar`

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | `str` | Uppercase ticker |
| `timeframe` | `str` | e.g. `1m`, `5m`, `1d` |
| `ts_open` | `datetime` | Bar open UTC |
| `ts_close` | `datetime` | Bar close UTC |
| `open` `high` `low` `close` | `Decimal` | |
| `volume` | `Decimal` | |
| `source` | `str` | Provider id |

### `Quote`

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | `str` | |
| `bid` `ask` `last` | `Decimal \| None` | |
| `ts` | `datetime` | Exchange/vendor time |
| `received_at` | `datetime` | Local receive time (for staleness) |
| `source` | `str` | |

### `NewsItem`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Stable vendor id or hash |
| `symbol` | `str \| None` | |
| `headline` | `str` | |
| `published_at` | `datetime` | |
| `url` | `str \| None` | |
| `source` | `str` | |

---

## Features & strategy

### `FeatureVector` (`src/features`)

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | `str` | |
| `as_of` | `datetime` | Feature time (no future data) |
| `values` | `dict[str, float]` | Named features |
| `meta` | `dict[str, str]` | e.g. calendar flags |

### `SignalSide`

`HOLD` | `BUY` | `SELL` | `REDUCE` (optional early) 

### `StrategySignal` (`src/strategies`)

| Field | Type | Notes |
|-------|------|-------|
| `strategy_id` | `str` | Registry key + version, e.g. `trend_pullback_v1` |
| `symbol` | `str` | |
| `side` | `SignalSide` | |
| `strength` | `float` | `0..1` |
| `horizon` | `str` | e.g. `intraday`, `swing` |
| `rationale` | `str` | Human-readable, deterministic text preferred |
| `as_of` | `datetime` | |
| `features_used` | `list[str]` | Feature keys referenced |

---

## LLM research

### `ResearchNote` (`src/llm`)

| Field | Type | Notes |
|-------|------|-------|
| `as_of` | `datetime` | |
| `regime` | `str` | Controlled vocabulary: `risk_on`, `risk_off`, `mixed`, `unknown` |
| `notes` | `str` | |
| `symbol_notes` | `dict[str, str]` | Optional per-symbol |
| `proposed_veto_symbols` | `list[str]` | Advisory only |
| `model` | `str` | Model id |
| `prompt_version` | `str` | |
| `cost_usd` | `Decimal \| None` | If available |

LLM must **not** emit broker orders. Optional later: `TradeProposal` from LLM still goes through risk.

---

## Risk & intents

### `TradeProposal` (`src/portfolio` or `src/orchestration`)

Pre-risk desired trade.

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | `str` | |
| `side` | `Literal["buy","sell"]` | |
| `qty` | `Decimal` | Absolute shares |
| `order_type` | `Literal["market","limit"]` | Start with market |
| `limit_price` | `Decimal \| None` | |
| `strategy_id` | `str` | |
| `signal_strength` | `float` | |
| `rationale` | `str` | |

### `RiskDecision` (`src/risk`)

| Field | Type | Notes |
|-------|------|-------|
| `status` | `Literal["APPROVE","RESIZE","REJECT"]` | |
| `approved_qty` | `Decimal` | `0` if reject |
| `reasons` | `list[str]` | Machine-readable codes |
| `checks_passed` | `list[str]` | |
| `checks_failed` | `list[str]` | |

### `TradeIntent`

Post-risk, ready for broker.

| Field | Type | Notes |
|-------|------|-------|
| `client_order_id` | `str` | Idempotency key |
| `symbol` | `str` | |
| `side` | `Literal["buy","sell"]` | |
| `qty` | `Decimal` | |
| `order_type` | `str` | |
| `limit_price` | `Decimal \| None` | |
| `time_in_force` | `str` | Default `day` |
| `strategy_id` | `str` | |
| `risk_decision` | `RiskDecision` | Embedded snapshot |
| `rationale` | `str` | |
| `created_at` | `datetime` | |

---

## Broker models (`src/brokers/models.py`)

### `OrderStatus`

`submitted` | `accepted` | `partially_filled` | `filled` | `canceled` | `rejected` | `expired`

### `Order`

| Field | Type | Notes |
|-------|------|-------|
| `broker_order_id` | `str \| None` | |
| `client_order_id` | `str` | |
| `symbol` | `str` | |
| `side` | `str` | |
| `qty` | `Decimal` | |
| `filled_qty` | `Decimal` | |
| `avg_fill_price` | `Decimal \| None` | |
| `status` | `OrderStatus` | |
| `submitted_at` | `datetime` | |
| `updated_at` | `datetime` | |
| `raw` | `dict \| None` | Vendor payload (redacted) |

### `Fill`

| Field | Type | Notes |
|-------|------|-------|
| `order_client_id` | `str` | |
| `qty` | `Decimal` | |
| `price` | `Decimal` | |
| `ts` | `datetime` | |
| `fee` | `Decimal` | Default `0` |

### `Position`

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | `str` | |
| `qty` | `Decimal` | Signed or long-only with side policy |
| `avg_price` | `Decimal` | |
| `market_value` | `Decimal \| None` | |

### `Account`

| Field | Type | Notes |
|-------|------|-------|
| `equity` | `Decimal` | |
| `cash` | `Decimal` | |
| `buying_power` | `Decimal` | |
| `currency` | `str` | `USD` |
| `pattern_day_trader` | `bool \| None` | If broker provides |

---

## Audit (`src/audit`)

### `AuditRecord`

See README example; required sections:

- `timestamp`, `symbol`, `decision` (`BUY`/`SELL`/`HOLD`/`REJECT`)
- `strategy_signal` (optional)
- `llm_research` (optional)
- `risk_gate` (`RiskDecision`-compatible)
- `action` / `execution` (optional if rejected pre-submit)
- `inputs_digest` — hash of feature keys + as_of for reproducibility

Persist as JSONL early; migrate to SQL in infra phases.

---

## Promotion (`src/orchestration/promotion.py`)

### `PromotionReport`

| Field | Type | Notes |
|-------|------|-------|
| `passed` | `bool` | |
| `checks` | `list[{name, passed, detail}]` | |
| `generated_at` | `datetime` | |

Used by `scripts/promote_check.py` and Phase 6 arming.

---

## Schema evolution

- Additive optional fields are OK.
- Renames require a short ADR or changelog note in this file.
- Version strategy ids (`_v1`, `_v2`) rather than silently changing signal semantics.
