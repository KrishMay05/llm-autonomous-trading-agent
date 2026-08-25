# Feature: LLM research layer

Phase ownership: **2**.  
ADR: [0001](../adr/0001-quant-first-llm-second.md).

## Purpose

Add regime context and explainability without controlling the order path.

## Scope

**In:** thin client, prompt templates versioned on disk, structured `ResearchNote` parse, cost logging, advisory veto list.  
**Out:** multi-agent debate graphs; LLM risk approval; per-tick calls.

## Contracts

### Client (`src/llm/client.py`)

- `complete_structured(prompt, schema) -> ResearchNote`
- Providers: OpenAI / Anthropic / Ollama via settings `LLM_PROVIDER`, `LLM_MODEL`
- Timeouts and max tokens enforced

### Synthesizer (`src/llm/research_synthesizer.py`)

Inputs: compact feature summary, recent headlines (truncated), open positions.  
Output: `ResearchNote`.

Cadence: e.g. once per session open + hourly — **not** every strategy evaluation.

### Veto policy

- `proposed_veto_symbols` is advisory.
- Orchestrator may convert veto → skip new BUYs for those symbols **only if** config `LLM_VETO_ENABLED=true`.
- Veto never forces sells unless a separate deterministic rule exists (default: no).

### Cost budget

- Settings: `LLM_MAX_USD_PER_DAY`
- If exceeded: skip LLM, log `LLM_BUDGET`, continue.

## Implementation plan

1. Client + JSON schema validation (Pydantic).
2. Prompt `prompts/research_v1.md` with clear “JSON only” instructions.
3. Wire optional path in loop.
4. Record `cost_usd` / token usage in audit when available.

## Tests

- Invalid JSON → soft-fail (None note), loop continues.
- Budget exceeded → no call.
- Fixture model response parses to `ResearchNote`.

## Exit criteria

- Paper session works with LLM on and off.
- No code path from LLM → `Broker.submit_order` without risk.

## Open risks

- Prompt injection via headlines — sanitize/truncate; prefer local sentiment for numbers.
- Model drift — pin `prompt_version` + model id in audit.
