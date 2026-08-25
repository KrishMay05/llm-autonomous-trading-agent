"""Broker factory — dispatch on Settings.broker to return the right adapter."""

from __future__ import annotations

from decimal import Decimal

from src.brokers.base import Broker
from src.brokers.paper import PaperBroker
from src.config.settings import Settings


def get_broker(settings: Settings) -> Broker:
    """Return a Broker instance based on ``settings.broker``.

    Currently only ``"paper"`` is implemented; ``"alpaca"`` and
    ``"robinhood_agentic"`` are stubbed for future phases.
    """
    broker_name = settings.broker

    if broker_name == "paper":
        return PaperBroker(
            initial_capital=Decimal("100000"),
            slippage_bps=5,
            commission=Decimal("0"),
            name="paper",
        )

    if broker_name == "alpaca":
        raise NotImplementedError("Alpaca adapter coming in Phase 4")

    if broker_name == "robinhood_agentic":
        raise NotImplementedError("Robinhood Agentic adapter coming in Phase 5")

    raise ValueError(f"Unknown broker: {broker_name}")
