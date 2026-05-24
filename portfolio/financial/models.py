"""Data models for the multi-agent financial analysis system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalType(str, Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class RiskLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class DecisionAction(str, Enum):
    BUY = "Buy"
    SELL = "Sell"
    HOLD = "Hold"


@dataclass(frozen=True)
class AgentSignal:
    """Output from a single analysis agent."""
    agent_name: str
    signal: SignalType
    confidence: float
    summary: str
    metrics: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PortfolioHolding:
    """A single position in a portfolio."""
    ticker: str
    shares: float
    avg_price: Optional[float] = None


@dataclass(frozen=True)
class StockDecision:
    """Final decision for a single stock."""
    ticker: str
    action: DecisionAction
    confidence: float
    risk_level: RiskLevel
    current_price: float
    signals: list[AgentSignal] = field(default_factory=list)
    reasoning: str = ""


@dataclass(frozen=True)
class PortfolioDecision:
    """Aggregate decision with per-stock details."""
    timestamp: datetime = field(default_factory=datetime.now)
    decisions: list[StockDecision] = field(default_factory=list)
    portfolio_risk: RiskLevel = RiskLevel.MODERATE
    diversification_score: float = 0.0
    summary: str = ""
