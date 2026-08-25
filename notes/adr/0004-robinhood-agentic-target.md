# ADR 0004: Robinhood Agentic as live target

## Status

Accepted

## Context

The operator intends to connect this system to Robinhood for real trading. Historically retail Robinhood lacked an official equities trading API (unofficial scrapers risk ToS/bans). As of May 2026, Robinhood offers **Agentic Trading** via official Trading MCP to a **dedicated agentic account**. Separate official **Crypto Trading API** exists for crypto only.

## Decision

- Primary personal live destination: **`RobinhoodAgenticBroker`** using **official** Agentic Trading / Trading MCP docs.
- Use a **dedicated agentic account** funded only with risk capital (blast radius).
- **Alpaca** remains first-class for REST paper/live parity and CI-friendly integration.
- **Forbidden** for live money: unofficial mobile-session automation / scraping libraries.
- Crypto via Robinhood Crypto API only if/when crypto strategies are explicitly in scope (Phase 8+).

## Consequences

- Must design for MCP/beta constraints (equities-first, preview/approval flows).
- Docs and runbooks must include disconnect / kill-switch procedures.
- Dual-broker support increases test surface but reduces lock-in.
