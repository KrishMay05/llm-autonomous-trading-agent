"""Centralized settings via pydantic-settings.

All runtime config is env-driven. Dangerous flags default safe.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Master switches ──────────────────────────────────────────
    live_trading_enabled: bool = False
    broker: Literal["paper", "alpaca", "robinhood_agentic"] = "paper"

    # ── LLM ──────────────────────────────────────────────────────
    llm_enabled: bool = True
    llm_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_max_usd_per_day: Decimal = Decimal("5.00")
    llm_veto_enabled: bool = False

    # ── Symbols ──────────────────────────────────────────────────
    symbol_allowlist: list[str] = ["SPY", "AAPL", "MSFT", "NVDA"]

    # ── Risk limits ──────────────────────────────────────────────
    max_position_pct: Decimal = Decimal("0.10")
    max_portfolio_heat_pct: Decimal = Decimal("0.40")
    max_daily_loss_pct: Decimal = Decimal("0.02")
    max_orders_per_day: int = 20
    max_quote_age_sec: int = 120
    kill_switch: bool = False
    pdt_guard_enabled: bool = False

    # ── Strategies ───────────────────────────────────────────────
    strategies: list[str] = ["trend_pullback_v1"]

    # ── Data providers ──────────────────────────────────────────
    market_data_provider: Literal["yfinance", "polygon", "alpaca_data"] = "yfinance"

    # ── Alpaca (Phase 4) ──────────────────────────────────────────
    alpaca_api_key: str | None = None
    alpaca_api_secret: str | None = None
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # ── Robinhood Agentic (Phase 5) ───────────────────────────────
    robinhood_mcp_url: str | None = None
    robinhood_account_id: str | None = None

    # ── Paths ────────────────────────────────────────────────────
    log_dir: Path = Path("logs")
    data_cache_dir: Path = Path("data_cache")

    @field_validator("symbol_allowlist", "strategies")
    @classmethod
    def _split_csv(cls, v: list[str] | str) -> list[str]:
        """Allow comma-separated string from env."""
        if isinstance(v, str):
            return [s.strip().upper() for s in v.split(",") if s.strip()]
        return [s.upper() for s in v]

    def get_broker(self) -> str:
        """Return broker name for factory."""
        return self.broker


def get_settings() -> Settings:
    """Get a fresh Settings instance. Use for testing or one-off reads."""
    return Settings()


# Singleton for app-wide use (tests can override by constructing their own).
_settings: Settings | None = None


def settings() -> Settings:
    """Get the cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
