"""Circuit breakers — trip and hold until explicitly reset.

Breakers stay tripped for the rest of the session (or until a human clears
them). The gate should consult ``is_tripped()`` before evaluating proposals,
but each individual check in ``HardRiskGate`` also does its own deterministic
evaluation so that the reason code is always attributable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    """Session-scoped trip flags for the risk system."""

    daily_loss: bool = False
    error_rate: bool = False
    reconcile_failed: bool = False
    _tripped_reasons: list[str] = field(default_factory=list)

    # ── mutate ───────────────────────────────────────────────────
    def trip(self, reason: str) -> None:
        """Trip the breaker corresponding to ``reason``.

        Accepted reasons: ``"daily_loss"``, ``"error_rate"``, ``"reconcile_failed"``.
        Unknown reasons raise ``ValueError`` so misuses surface in tests.
        """
        if reason == "daily_loss":
            self.daily_loss = True
        elif reason == "error_rate":
            self.error_rate = True
        elif reason == "reconcile_failed":
            self.reconcile_failed = True
        else:  # pragma: no cover - guard rail
            raise ValueError(f"Unknown breaker reason: {reason!r}")
        if reason not in self._tripped_reasons:
            self._tripped_reasons.append(reason)

    def is_tripped(self) -> bool:
        """True if any breaker flag is set."""
        return self.daily_loss or self.error_rate or self.reconcile_failed

    def reset(self) -> None:
        """Clear all flags (full reset — used on session rollover / manual)."""
        self.daily_loss = False
        self.error_rate = False
        self.reconcile_failed = False
        self._tripped_reasons.clear()

    def reset_daily(self) -> None:
        """Clear only the daily-loss flag (e.g. new trading day)."""
        self.daily_loss = False
        if "daily_loss" in self._tripped_reasons:
            self._tripped_reasons.remove("daily_loss")

    # ── audit ────────────────────────────────────────────────────
    @property
    def tripped_reasons(self) -> list[str]:
        """Reasons currently in tripped state (snapshot copy)."""
        out: list[str] = []
        if self.daily_loss:
            out.append("daily_loss")
        if self.error_rate:
            out.append("error_rate")
        if self.reconcile_failed:
            out.append("reconcile_failed")
        return out

    def __str__(self) -> str:  # pragma: no cover - trivial
        flags = ", ".join(self.tripped_reasons) if self.tripped_reasons else "none"
        return f"CircuitBreaker(tripped=[{flags}])"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"CircuitBreaker(daily_loss={self.daily_loss}, "
            f"error_rate={self.error_rate}, "
            f"reconcile_failed={self.reconcile_failed})"
        )
