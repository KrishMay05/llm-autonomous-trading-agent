"""Tests for src/llm/research_synthesizer.py."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.brokers.models import FeatureVector, NewsItem, Position, ResearchNote, StrategySignal
from src.brokers.models import SignalSide
from src.config.settings import Settings
from src.llm.client import LLMClient
from src.llm.research_synthesizer import ResearchSynthesizer


# ── fixtures ───────────────────────────────────────────────────────

def _make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "llm_enabled": True,
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "llm_max_usd_per_day": Decimal("5.00"),
        "llm_veto_enabled": False,
    }
    base.update(overrides)
    return Settings(**base)


def _valid_note_payload() -> dict[str, Any]:
    return {
        "as_of": "2026-01-15T14:30:00+00:00",
        "regime": "risk_on",
        "notes": "Momentum positive, vol contained.",
        "symbol_notes": {"AAPL": "Strong trend."},
        "proposed_veto_symbols": ["NVDA"],
        "model": "gpt-4o-mini",
        "prompt_version": "research_v1",
    }


def _make_features() -> list[FeatureVector]:
    return [
        FeatureVector(
            symbol="AAPL",
            as_of=datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc),
            values={"momentum": 0.85, "volatility": 0.12},
        ),
    ]


def _make_signals() -> list[StrategySignal]:
    return [
        StrategySignal(
            strategy_id="trend_pullback_v1",
            symbol="AAPL",
            side=SignalSide.BUY,
            strength=0.7,
            horizon="swing",
            as_of=datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc),
        ),
    ]


def _make_positions() -> list[Position]:
    return [Position(symbol="MSFT", qty=Decimal("10"), avg_price=Decimal("380.00"))]


def _make_headlines() -> list[NewsItem]:
    return [
        NewsItem(
            id="n1",
            symbol="AAPL",
            headline="Apple announces strong quarterly earnings",
            published_at=datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc),
        ),
    ]


def _mock_client(return_json: str | None, *, over_budget: bool = False) -> MagicMock:
    """Build a mock LLMClient whose complete_structured_with_cost returns ``return_json``."""
    mock = MagicMock(spec=LLMClient)
    mock.is_over_budget.return_value = over_budget
    mock.get_daily_cost.return_value = Decimal("0")
    if return_json is None:
        mock.complete_structured_with_cost.return_value = (None, None)
    else:
        mock.complete_structured_with_cost.return_value = (
            json.loads(return_json),
            Decimal("0.0015"),
        )
    return mock


# ── synthesize ─────────────────────────────────────────────────────

def test_synthesize_disabled() -> None:
    """llm_enabled=False → returns None without calling client."""
    settings = _make_settings(llm_enabled=False)
    client = _mock_client(json.dumps(_valid_note_payload()))
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is None
    client.complete_structured_with_cost.assert_not_called()


def test_synthesize_over_budget() -> None:
    """Over budget → returns None, logs LLM_BUDGET, no LLM call."""
    settings = _make_settings(llm_enabled=True)
    client = _mock_client(None, over_budget=True)
    client.get_daily_cost.return_value = Decimal("10.00")
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is None
    client.complete_structured_with_cost.assert_not_called()


def test_synthesize_valid() -> None:
    """Mock client returns valid ResearchNote JSON → parsed into ResearchNote."""
    settings = _make_settings(llm_enabled=True)
    client = _mock_client(json.dumps(_valid_note_payload()))
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is not None
    assert isinstance(result, ResearchNote)
    assert result.regime == "risk_on"
    assert result.notes == "Momentum positive, vol contained."
    assert result.symbol_notes == {"AAPL": "Strong trend."}
    assert result.proposed_veto_symbols == ["NVDA"]
    assert result.model == "gpt-4o-mini"
    assert result.prompt_version == "research_v1"
    assert result.cost_usd == Decimal("0.0015")
    client.complete_structured_with_cost.assert_called_once()


def test_synthesize_invalid_json() -> None:
    """Mock returns None (simulating invalid JSON) → returns None (soft-fail)."""
    settings = _make_settings(llm_enabled=True)
    client = _mock_client(None)
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is None


def test_synthesize_invalid_regime_normalizes_to_unknown() -> None:
    """If LLM returns an invalid regime, it's normalized to 'unknown'."""
    payload = _valid_note_payload()
    payload["regime"] = "bullish"  # not a valid regime

    settings = _make_settings(llm_enabled=True)
    client = _mock_client(json.dumps(payload))
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is not None
    assert result.regime == "unknown"


def test_synthesize_empty_inputs() -> None:
    """Synthesize works with all-empty inputs."""
    settings = _make_settings(llm_enabled=True)
    client = _mock_client(json.dumps(_valid_note_payload()))
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize([], [], [], [])
    assert result is not None
    assert result.regime == "risk_on"


def test_synthesize_missing_as_of_defaults_to_now() -> None:
    """Missing/invalid as_of falls back to current UTC time."""
    payload = _valid_note_payload()
    payload["as_of"] = "not-a-date"

    settings = _make_settings(llm_enabled=True)
    client = _mock_client(json.dumps(payload))
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize([], [], [], [])
    assert result is not None
    assert result.as_of.tzinfo is not None
    assert result.as_of.utcoffset() == timezone.utc.utcoffset(result.as_of)


def test_synthesize_propagates_cost_from_client() -> None:
    """cost_usd on the note matches what the client returned."""
    settings = _make_settings(llm_enabled=True)
    client = _mock_client(json.dumps(_valid_note_payload()))
    # Override the return to use a specific cost.
    client.complete_structured_with_cost.return_value = (
        _valid_note_payload(),
        Decimal("0.0420"),
    )
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is not None
    assert result.cost_usd == Decimal("0.0420")


# ── get_veto_symbols ───────────────────────────────────────────────

def test_get_veto_symbols_disabled() -> None:
    """llm_veto_enabled=False → always empty list, even with a note."""
    settings = _make_settings(llm_veto_enabled=False)
    client = _mock_client(json.dumps(_valid_note_payload()))
    synth = ResearchSynthesizer(settings, client)

    note = ResearchNote(
        as_of=datetime.now(timezone.utc),
        regime="risk_off",
        proposed_veto_symbols=["AAPL", "MSFT"],
        model="gpt-4o-mini",
        prompt_version="research_v1",
    )
    assert synth.get_veto_symbols(note) == []


def test_get_veto_symbols_enabled() -> None:
    """llm_veto_enabled=True → returns veto list from the note."""
    settings = _make_settings(llm_veto_enabled=True)
    client = _mock_client(json.dumps(_valid_note_payload()))
    synth = ResearchSynthesizer(settings, client)

    note = ResearchNote(
        as_of=datetime.now(timezone.utc),
        regime="risk_off",
        proposed_veto_symbols=["AAPL", "MSFT"],
        model="gpt-4o-mini",
        prompt_version="research_v1",
    )
    vetos = synth.get_veto_symbols(note)
    assert vetos == ["AAPL", "MSFT"]


def test_get_veto_symbols_enabled_none_note() -> None:
    """llm_veto_enabled=True but note is None → empty list."""
    settings = _make_settings(llm_veto_enabled=True)
    client = _mock_client(None)
    synth = ResearchSynthesizer(settings, client)
    assert synth.get_veto_symbols(None) == []


def test_get_veto_symbols_enabled_empty_note() -> None:
    """llm_veto_enabled=True, note has no vetos → empty list."""
    settings = _make_settings(llm_veto_enabled=True)
    client = _mock_client(json.dumps(_valid_note_payload()))
    synth = ResearchSynthesizer(settings, client)

    note = ResearchNote(
        as_of=datetime.now(timezone.utc),
        regime="risk_on",
        proposed_veto_symbols=[],
        model="gpt-4o-mini",
        prompt_version="research_v1",
    )
    assert synth.get_veto_symbols(note) == []


# ── integration: synthesizer + real LLMClient with injected caller ──

def test_synthesize_with_real_client_and_mock_caller() -> None:
    """End-to-end: synthesizer drives a real LLMClient with an injected api_caller."""
    payload = _valid_note_payload()

    def fake_caller(prompt: str, model: str) -> str:
        assert "research_v1" in prompt
        return json.dumps(payload)

    settings = _make_settings(llm_enabled=True)
    client = LLMClient(settings, api_caller=fake_caller)
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is not None
    assert result.regime == "risk_on"
    assert result.cost_usd is not None
    assert result.cost_usd > Decimal("0")


def test_synthesize_with_real_client_invalid_json_soft_fails() -> None:
    """Real client + garbage caller → None (soft-fail)."""
    def fake_caller(prompt: str, model: str) -> str:
        return "<<<not json>>>"

    settings = _make_settings(llm_enabled=True)
    client = LLMClient(settings, api_caller=fake_caller)
    synth = ResearchSynthesizer(settings, client)

    result = synth.synthesize(_make_features(), _make_signals(),
                              _make_positions(), _make_headlines())
    assert result is None
