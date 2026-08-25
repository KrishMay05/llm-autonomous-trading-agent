# Feature: Brokers

Phase ownership: **0** (protocol + paper), **4** (Alpaca), **5** (Robinhood Agentic).  
Models: [DOMAIN_MODELS.md](../DOMAIN_MODELS.md). ADR: [0003](../adr/0003-broker-adapter.md), [0004](../adr/0004-robinhood-agentic-target.md).

## Purpose

Uniform execution API so strategies/risk never depend on a vendor SDK. Enable paper → parity paper → live without rewriting the loop.

## Scope

**In**

- `Broker` protocol
- `PaperBroker` with slippage/latency/commission knobs
- `AlpacaBroker` (paper + live modes via credentials/base URL)
- `RobinhoodAgenticBroker` (official MCP / agentic)
- Shared `Order` / `Fill` / `Position` / `Account` models
- Idempotent submits via `client_order_id`

**Out**

- Unofficial Robinhood scrapers
- Smart multi-venue routing
- Options multi-leg (deferred)

## Contracts

### Protocol (`src/brokers/base.py`)

```python
class Broker(Protocol):
    name: str

    def get_account(self) -> Account: ...
    def list_positions(self) -> list[Position]: ...
    def get_order(self, client_order_id: str) -> Order | None: ...
    def list_open_orders(self) -> list[Order]: ...
    def submit_order(self, intent: TradeIntent) -> Order: ...
    def cancel_order(self, client_order_id: str) -> Order: ...
```

Factory: `src/brokers/factory.py` → `get_broker(settings) -> Broker`.

### PaperBroker behavior

- Maintain cash, positions, open orders in memory (optional persistence).
- Market orders fill at `last * (1 ± slippage_bps)`; configurable.
- Support rejects: insufficient cash, unknown symbol (optional).
- Same status enum as live adapters.

### AlpacaBroker

- Map intent ↔ Alpaca order fields.
- Paper base URL vs live base URL from settings.
- Normalize partial fills and statuses into shared `OrderStatus`.

### RobinhoodAgenticBroker

- Wrap official Trading MCP / agentic APIs only.
- Support **preview / dry-run** mode that does not autonomously commit when configured.
- Document required env vars and dedicated-account setup in Phase 5 plan.
- On unsupported asset class (e.g. options during equities-only beta): reject with clear reason code.

## Implementation plan

1. Define models + protocol + in-memory PaperBroker.
2. Contract test suite `tests/brokers/test_broker_contract.py` parameterized by broker fixture.
3. Wire factory to settings `BROKER=paper`.
4. (Phase 4) Alpaca adapter + marked integration tests.
5. (Phase 5) Robinhood Agentic adapter + runbook + preview mode.

## Tests

- Submit → filled (paper)
- Duplicate `client_order_id` does not double position
- Cancel path
- Insufficient buying power → rejected
- Contract tests for each adapter available in env

## Exit criteria (by phase)

- **P0:** PaperBroker used by CLI; contract tests green.
- **P4:** Alpaca paper multi-day reconcile clean.
- **P5:** Preview/submit path documented; live still default-off.

## Open risks

- MCP session lifetime / reconnect semantics
- Beta API changes on Robinhood Agentic
- Alpaca vs Robinhood order-type gaps — keep v1 at market/limit day orders
