"""Shared test fixtures and configuration."""

import sys
from pathlib import Path

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def utc_now():
    """A fixed UTC datetime for deterministic tests."""
    from datetime import datetime, timezone

    return datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
