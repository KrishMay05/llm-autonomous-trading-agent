"""Tests for src/llm/client.py."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from src.config.settings import Settings
from src.llm.client import LLMClient


def _make_settings(**overrides: Any) -> Settings:
    """Build a Settings instance with overrides for LLM-related fields."""
    base: dict[str, Any] = {
        "llm_enabled": True,
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "llm_max_usd_per_day": Decimal("5.00"),
        "llm_veto_enabled": False,
    }
    base.update(overrides)
    return Settings(**base)


def _valid_note_json() -> str:
    """A valid ResearchNote-shaped JSON string."""
    return json.dumps(
        {
            "as_of": "2026-01-15T14:30:00+00:00",
            "regime": "risk_on",
            "notes": "Momentum positive, vol contained.",
            "symbol_notes": {"AAPL": "Strong trend."},
            "proposed_veto_symbols": [],
            "model": "gpt-4o-mini",
            "prompt_version": "research_v1",
        }
    )


# ── complete_structured ────────────────────────────────────────────

def test_complete_structured_valid_json() -> None:
    """Mock api_caller returns valid JSON → parsed dict returned."""
    def fake_caller(prompt: str, model: str) -> str:
        return _valid_note_json()

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)

    schema = {"required": ["as_of", "regime", "notes"]}
    result = client.complete_structured("test prompt", schema)

    assert result is not None
    assert result["regime"] == "risk_on"
    assert result["model"] == "gpt-4o-mini"
    assert result["proposed_veto_symbols"] == []


def test_complete_structured_invalid_json() -> None:
    """Mock returns garbage → returns None (soft-fail)."""
    def fake_caller(prompt: str, model: str) -> str:
        return "this is not json at all"

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)

    result = client.complete_structured("test prompt", {})
    assert result is None


def test_complete_structured_empty_response() -> None:
    """Empty string → None."""
    def fake_caller(prompt: str, model: str) -> str:
        return ""

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)
    assert client.complete_structured("test", {}) is None


def test_complete_structured_non_object_json() -> None:
    """Valid JSON but not an object (e.g. a list) → None."""
    def fake_caller(prompt: str, model: str) -> str:
        return json.dumps([1, 2, 3])

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)
    assert client.complete_structured("test", {}) is None


def test_complete_structured_schema_missing_keys() -> None:
    """Valid JSON but missing required keys → None."""
    def fake_caller(prompt: str, model: str) -> str:
        return json.dumps({"regime": "risk_on"})

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)
    schema = {"required": ["as_of", "regime", "notes"]}
    assert client.complete_structured("test", schema) is None


def test_complete_structured_api_exception_soft_fails() -> None:
    """If api_caller raises, the client soft-fails to None."""
    def fake_caller(prompt: str, model: str) -> str:
        raise RuntimeError("network down")

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)
    assert client.complete_structured("test", {}) is None


# ── complete_structured_with_cost ──────────────────────────────────

def test_complete_structured_with_cost() -> None:
    """Returns (dict, cost) tuple on success."""
    def fake_caller(prompt: str, model: str) -> str:
        return _valid_note_json()

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)

    result, cost = client.complete_structured_with_cost("test", {})
    assert result is not None
    assert result["regime"] == "risk_on"
    assert cost is not None
    assert isinstance(cost, Decimal)
    assert cost > Decimal("0")


def test_complete_structured_with_cost_invalid_json() -> None:
    """Invalid JSON → (None, None)."""
    def fake_caller(prompt: str, model: str) -> str:
        return "garbage"

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)
    result, cost = client.complete_structured_with_cost("test", {})
    assert result is None
    assert cost is None


# ── budget ────────────────────────────────────────────────────────

def test_is_over_budget() -> None:
    """After adding cost > max → True; before → False."""
    def fake_caller(prompt: str, model: str) -> str:
        return _valid_note_json()

    settings = _make_settings(llm_max_usd_per_day=Decimal("0.0001"))
    client = LLMClient(settings, api_caller=fake_caller)

    # One call with the valid JSON prompt — cost estimate should exceed $0.0001.
    # But first, check that a fresh client is NOT over budget.
    assert client.is_over_budget() is False

    # Force cost over budget by calling many times (each call adds a small
    # estimated cost). We use a very low max so even one call trips it.
    # Actually: the first call adds cost, then is_over_budget flips.
    # But _call_with_cost checks is_over_budget BEFORE calling — so the
    # first call goes through (cost is 0), then subsequent calls are blocked.
    # To test is_over_budget directly, we use the tracker.
    client.reset_daily_cost()
    assert client.is_over_budget() is False

    # Add cost directly via the tracker to exceed budget.
    client._tracker.add_cost(Decimal("1.00"))
    assert client.is_over_budget() is True


def test_is_over_budget_blocks_call() -> None:
    """When over budget, complete_structured returns None without calling."""
    call_count = 0

    def fake_caller(prompt: str, model: str) -> str:
        nonlocal call_count
        call_count += 1
        return _valid_note_json()

    settings = _make_settings(llm_max_usd_per_day=Decimal("0.01"))
    client = LLMClient(settings, api_caller=fake_caller)

    # Pre-charge the tracker past budget.
    client._tracker.add_cost(Decimal("1.00"))
    assert client.is_over_budget() is True

    result = client.complete_structured("test", {})
    assert result is None
    assert call_count == 0  # API was never called


# ── reset ──────────────────────────────────────────────────────────

def test_reset_daily_cost() -> None:
    """Reset brings daily cost back to 0."""
    def fake_caller(prompt: str, model: str) -> str:
        return _valid_note_json()

    settings = _make_settings()
    client = LLMClient(settings, api_caller=fake_caller)

    # Make a call to incur cost.
    client.complete_structured("test", {})
    assert client.get_daily_cost() > Decimal("0")

    client.reset_daily_cost()
    assert client.get_daily_cost() == Decimal("0")


def test_get_daily_cost_starts_at_zero() -> None:
    """Fresh client has zero daily cost."""
    settings = _make_settings()
    client = LLMClient(settings, api_caller=lambda p, m: "")
    assert client.get_daily_cost() == Decimal("0")
