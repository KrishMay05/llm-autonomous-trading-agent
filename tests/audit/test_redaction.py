"""Tests for src.audit.redaction — secret-stripping helpers."""

from __future__ import annotations

from src.audit.redaction import (
    compute_inputs_digest,
    redact_account,
    redact_raw,
)


def test_redact_account() -> None:
    account = {
        "equity": 10000.0,
        "cash": 5000.0,
        "account_number": "ABC-123-XYZ",
        "account_id": "acct-99",
        "currency": "USD",
    }
    out = redact_account(account)
    assert "account_number" not in out
    assert "account_id" not in out
    assert out["equity"] == 10000.0
    assert out["cash"] == 5000.0
    assert out["currency"] == "USD"
    # original is not mutated
    assert account["account_number"] == "ABC-123-XYZ"


def test_redact_raw() -> None:
    raw = {
        "api_key": "sk-live-1234",
        "secret": "hunter2",
        "token": "tok-abc",
        "password": "p@ss",
        "account_id": "acct-99",
        "symbol": "AAPL",
        "nested": {
            "api_key": "sk-inner",
            "ok": "yes",
        },
        "items": [{"api_key": "sk-list"}, {"safe": 1}],
    }
    out = redact_raw(raw)
    assert "api_key" not in out
    assert "secret" not in out
    assert "token" not in out
    assert "password" not in out
    assert "account_id" not in out
    assert out["symbol"] == "AAPL"
    assert "api_key" not in out["nested"]
    assert out["nested"]["ok"] == "yes"
    assert "api_key" not in out["items"][0]
    assert out["items"][1]["safe"] == 1


def test_redact_preserves_safe_fields() -> None:
    raw = {
        "symbol": "MSFT",
        "qty": 10,
        "side": "buy",
        "status": "filled",
        "meta": {"strategy_id": "mom-1", "tags": ["a", "b"]},
    }
    out = redact_raw(raw)
    assert out == raw


def test_compute_inputs_digest_same_inputs_same_hash() -> None:
    features = {"rsi": 0.7, "momentum": 1.2, "vol": 0.03}
    as_of = "2026-01-15T14:30:00Z"
    h1 = compute_inputs_digest(features, as_of)
    h2 = compute_inputs_digest(features, as_of)
    assert h1 == h2
    # values change but keys + as_of stay the same → same digest
    features2 = {"rsi": 0.9, "momentum": -0.1, "vol": 0.05}
    assert compute_inputs_digest(features2, as_of) == h1


def test_compute_inputs_digest_different_keys_different_hash() -> None:
    a = compute_inputs_digest({"rsi": 1, "momentum": 2}, "2026-01-15")
    b = compute_inputs_digest({"rsi": 1, "vol": 2}, "2026-01-15")
    assert a != b


def test_compute_inputs_digest_different_as_of_different_hash() -> None:
    a = compute_inputs_digest({"rsi": 1}, "2026-01-15")
    b = compute_inputs_digest({"rsi": 1}, "2026-01-16")
    assert a != b
