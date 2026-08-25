"""Research synthesizer — turns features + headlines into a ResearchNote.

This is the only place the trading system talks to the LLM. It is deliberately
thin: build a compact prompt, call the client, parse the JSON into a Pydantic
``ResearchNote``, and return it. All failure modes soft-fail to ``None`` so the
orchestrator's loop never breaks because of the LLM.

Cadence (from notes/features/llm-research.md): called once per session open
and hourly by the orchestrator — **not** on every strategy evaluation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.brokers.models import FeatureVector, NewsItem, Position, ResearchNote, StrategySignal
from src.config.settings import Settings
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)

_PROMPT_VERSION = "research_v1"
_PROMPT_PATH = Path(__file__).parent / "prompts" / "research_v1.md"

# Truncation limits to keep the prompt compact and limit prompt-injection
# surface area from headlines.
_MAX_HEADLINES = 10
_MAX_HEADLINE_CHARS = 200
_MAX_FEATURES = 8
_MAX_POSITIONS = 20
_MAX_NOTES_CHARS = 500


class ResearchSynthesizer:
    """Build a compact prompt, call the LLM, parse a :class:`ResearchNote`.

    Parameters
    ----------
    settings
        Application settings. Honors ``llm_enabled``, ``llm_veto_enabled``.
    client
        Injected :class:`LLMClient` (real or mock).
    """

    def __init__(self, settings: Settings, client: LLMClient) -> None:
        self._settings = settings
        self._client = client

    def synthesize(
        self,
        features: list[FeatureVector],
        signals: list[StrategySignal],
        positions: list[Position],
        headlines: list[NewsItem],
    ) -> ResearchNote | None:
        """Produce a :class:`ResearchNote` from market context.

        Returns ``None`` (soft-fail) when:
        - ``settings.llm_enabled`` is False
        - the daily LLM budget is exceeded
        - the LLM returns invalid JSON or a schema mismatch
        """
        if not self._settings.llm_enabled:
            logger.info("LLM_DISABLED synthesizer skipping call")
            return None

        if self._client.is_over_budget():
            logger.warning(
                "LLM_BUDGET daily cost %s exceeds max %s — skipping synthesizer call",
                self._client.get_daily_cost(),
                self._settings.llm_max_usd_per_day,
            )
            return None

        prompt = self._build_prompt(features, signals, positions, headlines)
        schema = self._research_note_schema()

        data, cost = self._client.complete_structured_with_cost(prompt, schema)
        if data is None:
            logger.warning("LLM_SYNTHESIZE_NO_RESULT soft-failing to None")
            return None

        try:
            note = self._to_research_note(data, cost)
        except Exception as exc:  # noqa: BLE001 — soft-fail on parse error
            logger.warning("LLM_NOTE_PARSE_FAILED err=%s raw=%s", exc, data)
            return None

        logger.info(
            "LLM_SYNTHESIZED regime=%s model=%s cost=%s vetos=%d",
            note.regime,
            note.model,
            note.cost_usd,
            len(note.proposed_veto_symbols),
        )
        return note

    def get_veto_symbols(self, note: ResearchNote | None) -> list[str]:
        """Return the advisory veto list from ``note``.

        Returns ``[]`` when:
        - ``settings.llm_veto_enabled`` is False, or
        - ``note`` is ``None`` (LLM was skipped/failed).
        """
        if not self._settings.llm_veto_enabled:
            return []
        if note is None:
            return []
        return list(note.proposed_veto_symbols)

    # ── prompt construction ──────────────────────────────────────

    def _build_prompt(
        self,
        features: list[FeatureVector],
        signals: list[StrategySignal],
        positions: list[Position],
        headlines: list[NewsItem],
    ) -> str:
        """Build the compact prompt sent to the LLM."""
        template = self._load_template()

        feature_block = self._format_features(features[:_MAX_FEATURES])
        signal_block = self._format_signals(signals[:_MAX_FEATURES])
        headline_block = self._format_headlines(headlines[:_MAX_HEADLINES])
        position_block = self._format_positions(positions[:_MAX_POSITIONS])

        now_iso = datetime.now(timezone.utc).isoformat()
        return (
            f"{template}\n\n"
            f"--- INPUTS ---\n"
            f"as_of: {now_iso}\n"
            f"model: {self._settings.llm_model}\n"
            f"prompt_version: {_PROMPT_VERSION}\n\n"
            f"## Feature summary\n{feature_block}\n\n"
            f"## Strategy signals\n{signal_block}\n\n"
            f"## Open positions\n{position_block}\n\n"
            f"## Recent headlines (truncated)\n{headline_block}\n\n"
            f"--- END INPUTS ---\n\n"
            f"Output JSON only. No prose. No markdown fences."
        )

    @staticmethod
    def _load_template() -> str:
        try:
            return _PROMPT_PATH.read_text(encoding="utf-8")
        except OSError:
            # Fall back to a minimal inline template if the file is missing.
            return (
                "You are a senior macro/quant research analyst. Output a single "
                "JSON object with fields: as_of, regime (risk_on|risk_off|mixed|"
                "unknown), notes, symbol_notes, proposed_veto_symbols, model, "
                "prompt_version. Output JSON only, no prose."
            )

    @staticmethod
    def _format_features(features: list[FeatureVector]) -> str:
        if not features:
            return "(none)"
        lines: list[str] = []
        for fv in features:
            values_str = ", ".join(f"{k}={v:.4f}" for k, v in fv.values.items())
            lines.append(f"- {fv.symbol} @ {fv.as_of.isoformat()}: {values_str}")
        return "\n".join(lines)

    @staticmethod
    def _format_signals(signals: list[StrategySignal]) -> str:
        if not signals:
            return "(none)"
        lines: list[str] = []
        for sig in signals:
            lines.append(
                f"- {sig.strategy_id} {sig.symbol} {sig.side.value} "
                f"strength={sig.strength:.3f} horizon={sig.horizon}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_positions(positions: list[Position]) -> str:
        if not positions:
            return "(none)"
        lines: list[str] = []
        for pos in positions:
            mv = f"${pos.market_value}" if pos.market_value is not None else "n/a"
            lines.append(f"- {pos.symbol} qty={pos.qty} avg=${pos.avg_price} mv={mv}")
        return "\n".join(lines)

    @staticmethod
    def _format_headlines(headlines: list[NewsItem]) -> str:
        if not headlines:
            return "(none)"
        lines: list[str] = []
        for item in headlines:
            headline = item.headline[:_MAX_HEADLINE_CHARS]
            lines.append(f"- [{item.published_at.isoformat()}] {headline}")
        return "\n".join(lines)

    # ── schema + parsing ─────────────────────────────────────────

    @staticmethod
    def _research_note_schema() -> dict[str, Any]:
        """JSON schema hint for the client's lightweight validation.

        The authoritative type contract is the Pydantic ``ResearchNote``
        model — this schema only enforces required-key presence.
        """
        return {
            "type": "object",
            "required": ["as_of", "regime", "notes", "symbol_notes",
                         "proposed_veto_symbols", "model", "prompt_version"],
            "properties": {
                "as_of": {"type": "string"},
                "regime": {"type": "string", "enum": ["risk_on", "risk_off", "mixed", "unknown"]},
                "notes": {"type": "string"},
                "symbol_notes": {"type": "object"},
                "proposed_veto_symbols": {"type": "array", "items": {"type": "string"}},
                "model": {"type": "string"},
                "prompt_version": {"type": "string"},
            },
        }

    def _to_research_note(self, data: dict[str, Any], cost: Any | None) -> ResearchNote:
        """Coerce a parsed dict into a :class:`ResearchNote`.

        Fills in safe defaults for missing fields and normalizes the
        ``as_of`` timestamp to timezone-aware UTC.
        """
        raw_as_of = data.get("as_of")
        if isinstance(raw_as_of, str):
            try:
                as_of = datetime.fromisoformat(raw_as_of)
            except ValueError:
                as_of = datetime.now(timezone.utc)
        elif isinstance(raw_as_of, datetime):
            as_of = raw_as_of
        else:
            as_of = datetime.now(timezone.utc)
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        regime = data.get("regime", "unknown")
        if regime not in ("risk_on", "risk_off", "mixed", "unknown"):
            regime = "unknown"

        symbol_notes = data.get("symbol_notes") or {}
        if not isinstance(symbol_notes, dict):
            symbol_notes = {}

        veto = data.get("proposed_veto_symbols") or []
        if not isinstance(veto, list):
            veto = []
        veto = [str(s).upper() for s in veto if isinstance(s, str | int)]

        notes = str(data.get("notes", ""))[:_MAX_NOTES_CHARS]
        model = str(data.get("model", self._settings.llm_model))
        prompt_version = str(data.get("prompt_version", _PROMPT_VERSION))

        cost_usd: Decimal | None = None
        if isinstance(cost, Decimal):
            cost_usd = cost
        elif cost is not None:
            try:
                cost_usd = Decimal(str(cost))
            except (ValueError, TypeError):
                cost_usd = None

        return ResearchNote(
            as_of=as_of,
            regime=regime,
            notes=notes,
            symbol_notes=symbol_notes,
            proposed_veto_symbols=veto,
            model=model,
            prompt_version=prompt_version,
            cost_usd=cost_usd,
        )
