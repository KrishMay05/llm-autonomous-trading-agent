#!/usr/bin/env python3
"""CLI entry point for the trading agent.

Phase 0: paper broker and stub quotes (no live APIs).

Usage:
    python scripts/run_agent.py --tickers SPY,AAPL --broker paper
    python scripts/run_agent.py --ui
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure src/ is importable when running as a script
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from src.config.settings import Settings  # noqa: E402
from src.orchestration.session import AgentSession  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the trading agent (Phase 0).")
    parser.add_argument(
        "--tickers",
        type=str,
        default="SPY,AAPL,MSFT,NVDA",
        help="Comma-separated ticker list (default: SPY,AAPL,MSFT,NVDA)",
    )
    parser.add_argument(
        "--broker",
        type=str,
        default="paper",
        choices=["paper", "alpaca", "robinhood"],
        help="Broker backend (default: paper). Local UI always uses paper.",
    )
    parser.add_argument(
        "--llm-disabled",
        action="store_true",
        help="Disable LLM research note",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Start the local operator UI instead of printing one CLI iteration",
    )
    parser.add_argument(
        "--ui-host",
        default="127.0.0.1",
        help="UI bind host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=8765,
        help="UI bind port (default: 8765)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser when starting --ui",
    )
    return parser


def build_settings(args: argparse.Namespace) -> Settings:
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    settings = Settings()
    return settings.model_copy(
        update={
            "symbol_allowlist": tickers,
            "broker": "paper",
            "llm_enabled": False if args.llm_disabled else settings.llm_enabled,
        }
    )


def run_cli(settings: Settings) -> None:
    tickers = [s.upper() for s in settings.symbol_allowlist]
    print("=== Trading Agent (Phase 0) ===")
    print("Broker: paper")
    print(f"Tickers: {tickers}")
    print(f"LLM enabled: {settings.llm_enabled}")
    print()

    def _print_audit(record) -> None:
        print(f"[AUDIT] {record.timestamp.isoformat()} {record.symbol} {record.decision}")

    session = AgentSession(settings, audit_hook=_print_audit)
    records = session.run_once()

    print(f"\n=== Results: {len(records)} audit records ===")
    for rec in records:
        try:
            print(json.dumps(rec.model_dump(mode="json"), default=str, indent=2))
        except Exception:
            print(f"  {rec.timestamp} {rec.symbol} {rec.decision}")


def run_ui(settings: Settings, args: argparse.Namespace) -> None:
    from src.api.main import serve_ui

    serve_ui(
        settings,
        host=args.ui_host,
        port=args.ui_port,
        open_browser=not args.no_browser,
    )


def main() -> None:
    args = build_parser().parse_args()
    settings = build_settings(args)
    if args.ui:
        run_ui(settings, args)
        return
    run_cli(settings)


if __name__ == "__main__":
    main()
