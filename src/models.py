"""Shared Pydantic domain models. Re-exported from brokers.models for convenience."""
from src.brokers.models import (
    Account, AuditRecord, Bar, Fill, NewsItem, Order, OrderStatus,
    Position, Quote, ResearchNote, RiskDecision, RiskStatus,
    SessionState, SignalSide, StrategySignal, TradeIntent,
    TradeProposal, FeatureVector,
)

__all__ = [
    "Account", "AuditRecord", "Bar", "Fill", "NewsItem", "Order",
    "OrderStatus", "Position", "Quote", "ResearchNote", "RiskDecision",
    "RiskStatus", "SessionState", "SignalSide", "StrategySignal",
    "TradeIntent", "TradeProposal", "FeatureVector",
]
