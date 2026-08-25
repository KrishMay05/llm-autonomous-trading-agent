"""Redaction helpers — strip secrets and account identifiers before logging."""

from __future__ import annotations

import hashlib
import re
from typing import Any

# Keys whose values must never appear in audit payloads. Matched as
# case-insensitive substrings so ``api_key``, ``APIKey``, ``apiKey`` all match.
_SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "api_key",
    "secret",
    "token",
    "password",
    "account_id",
    "account_number",
)

# Account-level sensitive fields (top-level Account dict).
_ACCOUNT_SENSITIVE: tuple[str, ...] = (
    "account_number",
    "account_id",
    "account_number_id",
)


def _is_sensitive_key(key: str, fragments: tuple[str, ...]) -> bool:
    low = key.lower()
    return any(frag in low for frag in fragments)


def redact_account(account: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``account`` with sensitive fields removed.

    Removes ``account_number`` and ``account_id``. Does not mutate the input.
    """
    return {
        k: v
        for k, v in account.items()
        if not _is_sensitive_key(k, _ACCOUNT_SENSITIVE)
    }


def redact_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``raw`` with any sensitive keys removed recursively.

    Drops keys matching ``api_key`` / ``secret`` / ``token`` / ``password`` /
    ``account_id`` (case-insensitive substring match). Nested dicts are
    redacted in place.
    """
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if _is_sensitive_key(k, _SENSITIVE_KEY_FRAGMENTS):
            continue
        if isinstance(v, dict):
            out[k] = redact_raw(v)
        elif isinstance(v, list):
            out[k] = [
                redact_raw(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            out[k] = v
    return out


def compute_inputs_digest(features: dict[str, Any], as_of: str) -> str:
    """SHA256 hex digest of the feature keys + ``as_of`` timestamp.

    Only the *keys* of ``features`` contribute to the digest (not their
    values), so two runs over the same feature set at the same ``as_of`` produce
    the same digest even if values change slightly.
    """
    keys = sorted(features.keys())
    payload = "|".join(keys) + "@" + str(as_of)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
