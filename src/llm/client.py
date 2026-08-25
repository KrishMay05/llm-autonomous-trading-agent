"""LLM client abstraction — provider-pluggable, cost-tracked, soft-fail.

The client is deliberately thin: it sends a prompt, receives a text response,
and parses it as JSON against an optional schema dict. It does **not** import
any provider SDK at module import time — providers are imported lazily inside
``_call_api`` so the package has zero hard dependency on openai/anthropic/ollama
and tests can inject a fake ``api_caller``.

Design rules (from notes/features/llm-research.md):
- Invalid JSON → return None (soft-fail). The caller keeps the loop running.
- Cost is tracked via :class:`CostTracker` and enforced against the daily
  budget before every call.
- The LLM can never emit broker orders; this layer only parses structured
  notes.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Callable

from src.config.settings import Settings
from src.llm.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# Rough per-1k-token USD prices for cost estimation. These are conservative
# averages across the supported providers and are only used when the provider
# doesn't return an explicit cost. Real usage should ideally come from the
# API response's usage block.
_ESTIMATED_PRICE_PER_1K_TOKENS: dict[str, float] = {
    "gpt-4o-mini": 0.0015,
    "gpt-4o": 0.005,
    "gpt-4-turbo": 0.01,
    "claude-3-5-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "llama3": 0.0,  # local
    "default": 0.003,
}

# Rough token-per-char heuristic for fallback cost estimation.
_CHARS_PER_TOKEN = 4


class LLMClient:
    """Provider-pluggable LLM client with daily cost tracking.

    Parameters
    ----------
    settings
        Application settings. Uses ``llm_provider``, ``llm_model``, and
        ``llm_max_usd_per_day``.
    api_caller
        Optional callable ``(prompt: str, model: str) -> str`` for dependency
        injection. When omitted, :meth:`_call_api` lazily imports the
        provider SDK selected by ``settings.llm_provider``. Tests inject a
        mock here to avoid real network calls.
    """

    def __init__(
        self,
        settings: Settings,
        api_caller: Callable[[str, str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._api_caller = api_caller
        self._tracker = CostTracker()

    # ── public API ────────────────────────────────────────────────

    def complete_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any] | None:
        """Call the LLM and parse the response as JSON.

        Returns the parsed dict on success, or ``None`` on any failure
        (network error, non-JSON response, schema mismatch). Soft-fails by
        design — the orchestrator must keep running.
        """
        result, _cost = self._call_with_cost(prompt)
        if result is None:
            return None
        return self._validate(result, schema)

    def complete_structured_with_cost(
        self, prompt: str, schema: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, Decimal | None]:
        """Same as :meth:`complete_structured` but also returns the cost.

        Returns ``(parsed_dict_or_none, cost_usd_or_none)``.
        """
        result, cost = self._call_with_cost(prompt)
        if result is None:
            return None, cost
        return self._validate(result, schema), cost

    def get_daily_cost(self) -> Decimal:
        """Cumulative USD spend for today."""
        return self._tracker.get_daily_cost()

    def is_over_budget(self) -> bool:
        """True if today's spend exceeds ``settings.llm_max_usd_per_day``."""
        return self._tracker.is_over_budget(self._settings.llm_max_usd_per_day)

    def reset_daily_cost(self) -> None:
        """Reset the daily cost counter (tests / manual override)."""
        self._tracker.reset()

    # ── internals ─────────────────────────────────────────────────

    def _call_with_cost(self, prompt: str) -> tuple[dict[str, Any] | None, Decimal | None]:
        """Call the API, parse JSON, and estimate cost.

        Soft-fails: returns ``(None, cost_or_none)`` on any error.
        """
        if self.is_over_budget():
            logger.warning("LLM_BUDGET daily cost %s exceeds max %s", self.get_daily_cost(),
                           self._settings.llm_max_usd_per_day)
            return None, None

        model = self._settings.llm_model
        try:
            raw = self._call_api(prompt, model)
        except Exception as exc:  # noqa: BLE001 — soft-fail on any provider error
            logger.warning("LLM_CALL_FAILED provider=%s model=%s err=%s",
                           self._settings.llm_provider, model, exc)
            return None, None

        if not raw or not raw.strip():
            logger.warning("LLM_EMPTY_RESPONSE provider=%s model=%s", self._settings.llm_provider,
                           model)
            return None, None

        try:
            parsed: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("LLM_INVALID_JSON provider=%s model=%s err=%s",
                           self._settings.llm_provider, model, exc)
            return None, None

        if not isinstance(parsed, dict):
            logger.warning("LLM_NON_OBJECT_JSON provider=%s model=%s type=%s",
                           self._settings.llm_provider, model, type(parsed).__name__)
            return None, None

        cost = self._estimate_cost(prompt, raw, model)
        if cost is not None:
            self._tracker.add_cost(cost)
        return parsed, cost

    def _validate(self, data: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any] | None:
        """Lightweight schema validation.

        We don't pull in jsonschema as a hard dep. If ``schema`` declares a
        ``required`` list, we check that all required keys are present. The
        heavy lifting (field types, enums) is done downstream by the Pydantic
        ``ResearchNote`` model.
        """
        if not isinstance(schema, dict):
            return data
        required = schema.get("required") or []
        missing = [k for k in required if k not in data]
        if missing:
            logger.warning("LLM_SCHEMA_MISSING keys=%s", missing)
            return None
        return data

    def _estimate_cost(self, prompt: str, response: str, model: str) -> Decimal | None:
        """Estimate USD cost for a call when the provider doesn't give us one.

        Uses a coarse chars-per-token heuristic and a per-model price table.
        Returns ``None`` if estimation isn't possible (e.g. local model).
        """
        price = _ESTIMATED_PRICE_PER_1K_TOKENS.get(model)
        if price is None:
            price = _ESTIMATED_PRICE_PER_1K_TOKENS["default"]
        if price <= 0:
            return None
        tokens_in = max(1, len(prompt)) / _CHARS_PER_TOKEN
        tokens_out = max(1, len(response)) / _CHARS_PER_TOKEN
        total_tokens = tokens_in + tokens_out
        cost = (total_tokens / 1000.0) * price
        return Decimal(str(round(cost, 6)))

    def _call_api(self, prompt: str, model: str) -> str:
        """Send ``prompt`` to the configured provider and return raw text.

        Uses the injected ``api_caller`` if provided (tests). Otherwise lazily
        imports the provider SDK. Raises on any provider error — the caller
        catches and soft-fails.
        """
        if self._api_caller is not None:
            return self._api_caller(prompt, model)

        provider = self._settings.llm_provider
        if provider == "openai":
            return self._call_openai(prompt, model)
        if provider == "anthropic":
            return self._call_anthropic(prompt, model)
        if provider == "ollama":
            return self._call_ollama(prompt, model)
        raise ValueError(f"unsupported llm_provider: {provider!r}")

    # ── provider adapters (lazy import) ──────────────────────────

    def _call_openai(self, prompt: str, model: str) -> str:
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("openai package not installed") from exc
        client = OpenAI()  # reads OPENAI_API_KEY from env
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str, model: str) -> str:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("anthropic package not installed") from exc
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text if resp.content else ""

    def _call_ollama(self, prompt: str, model: str) -> str:
        try:
            import ollama  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("ollama package not installed") from exc
        resp = ollama.generate(model=model, prompt=prompt)
        return resp.get("response", "") if isinstance(resp, dict) else str(resp)
