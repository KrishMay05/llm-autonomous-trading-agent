"""Tests for the startup CLI flags."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_help_includes_ui_flag():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_agent.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--ui" in result.stdout
    assert "--ui-port" in result.stdout
    assert "--no-browser" in result.stdout
