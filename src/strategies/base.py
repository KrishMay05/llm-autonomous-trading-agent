"""Strategy protocol and evaluation context.

The Strategy protocol is the contract every deterministic signal generator
must satisfy.  Strategies are pure: given a frozen `FeatureVector` and a
read-only `StrategyContext`, they emit an immutable `StrategySignal`.

See notes/features/strategies.md for the authoritative spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.brokers.models import Account, FeatureVector, Position, ResearchNote, StrategySignal


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Read-only context handed to a strategy at evaluation time.

    Attributes:
        position: Currently held position for the symbol being evaluated, or
            ``None`` when flat / unknown.
        research_note: Most-recent LLM research note, or ``None`` when LLM
            research is disabled or not yet run.
        account: Snapshot of the account, or ``None`` when not available
            (e.g. backtest without portfolio state).
    """

    position: Position | None = None
    research_note: ResearchNote | None = None
    account: Account | None = None


@runtime_checkable
class Strategy(Protocol):
    """Protocol every strategy must implement.

    Implementations must be deterministic and side-effect free: the same
    ``(features, context)`` must always produce the same signal.  This is
    what makes strategies replayable in backtests without an LLM.
    """

    id: str

    def evaluate(self, features: FeatureVector, context: StrategyContext) -> StrategySignal:
        """Evaluate the feature vector and emit a trading signal."""
        ...
