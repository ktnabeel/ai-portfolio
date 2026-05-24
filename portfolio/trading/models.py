"""Data models for the multi-agent trading system.

All models use Pydantic for validation and serialization,
and TypedDict for LangGraph state management.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional, TypedDict

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════════════════
# Enums
# ════════════════════════════════════════════════════════════════════════

class MarketRegime(str, Enum):
    BULL = "Bull Market"
    BEAR = "Bear Market"
    NEUTRAL = "Neutral / Range-bound"


class OptionStrategy(str, Enum):
    CALL = "Long Call"
    PUT = "Long Put"
    STRANGLE = "Long Strangle"
    NO_TRADE = "No Trade"


class OrderStatus(str, Enum):
    PENDING = "Pending"
    FILLED = "Filled"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"


class OrderType(str, Enum):
    MARKET = "Market"
    LIMIT = "Limit"


class FearGreedZone(str, Enum):
    EXTREME_FEAR = "Extreme Fear"
    FEAR = "Fear"
    NEUTRAL = "Neutral"
    GREED = "Greed"
    EXTREME_GREED = "Extreme Greed"


# ════════════════════════════════════════════════════════════════════════
# Core Domain Models
# ════════════════════════════════════════════════════════════════════════

class SecurityInfo(BaseModel):
    """Security identification and profile from Security Agent."""
    symbol: str
    company_name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: Optional[float] = None
    current_price: Optional[float] = None
    exchange: str = ""
    currency: str = "USD"
    is_optionable: bool = True
    reasoning: str = ""  # Why this security was identified/validated


class FearGreedData(BaseModel):
    """CNN Fear & Greed Index data."""
    value: int = Field(ge=0, le=100, description="0-100 Fear & Greed score")
    zone: FearGreedZone
    description: str
    previous_close: Optional[int] = None
    one_week_ago: Optional[int] = None
    one_month_ago: Optional[int] = None
    one_year_ago: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class WorldNewsItem(BaseModel):
    """A single world news headline relevant to markets."""
    headline: str
    source: str = ""
    url: str = ""
    impact: str = "Neutral"  # Positive, Negative, Neutral
    category: str = ""  # geopolitics, economics, central-bank, corporate, etc.
    summary: str = ""


class RiskSentimentOutput(BaseModel):
    """Output from the Risk/Sentiment Agent."""
    fear_greed: FearGreedData
    top_news: list[WorldNewsItem] = Field(default_factory=list)
    market_trend: str = ""
    risk_assessment: str = ""
    reasoning: str = ""


class RegimeOutput(BaseModel):
    """Output from the Regime Detection Agent."""
    regime: MarketRegime
    confidence: float = Field(ge=0.0, le=1.0)
    volatility_index: Optional[float] = None
    trend_strength: Optional[float] = None
    sp500_trend: str = ""
    indicators: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


class OptionContract(BaseModel):
    """An option contract with pricing data."""
    symbol: str
    strike: float
    expiration: str  # ISO date string
    option_type: str  # "call" or "put"
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: int = 0
    open_interest: int = 0
    implied_volatility: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0


class OptionChain(BaseModel):
    """Full options chain for a symbol."""
    symbol: str
    underlying_price: float
    expiration_dates: list[str] = Field(default_factory=list)
    calls: list[OptionContract] = Field(default_factory=list)
    puts: list[OptionContract] = Field(default_factory=list)


class StrategyDecision(BaseModel):
    """Output from the Decision Agent."""
    strategy: OptionStrategy
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    recommended_strike: Optional[float] = None
    recommended_expiration: Optional[str] = None
    call_contract: Optional[OptionContract] = None
    put_contract: Optional[OptionContract] = None
    max_risk: Optional[float] = None
    max_reward: Optional[float] = None
    breakeven: Optional[str] = ""
    alternatives: list[str] = Field(default_factory=list)


class OrderRequest(BaseModel):
    """A request to execute a trade."""
    order_id: str = Field(default_factory=lambda: f"ORD-{uuid.uuid4().hex[:8].upper()}")
    symbol: str
    strategy: OptionStrategy
    option_symbol: Optional[str] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    option_type: Optional[str] = None
    quantity: int = 1
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None


class OrderConfirmation(BaseModel):
    """Confirmation of a trade execution."""
    order_id: str
    status: OrderStatus
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    commission: float = 0.0
    total_cost: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    notes: str = ""


class ExecutionResult(BaseModel):
    """Complete result from the Execution Agent."""
    request: OrderRequest
    confirmation: dict[str, Any]  # Dict for flexibility (MCP returns dicts, not OrderConfirmation)
    pnl_estimate: Optional[float] = None
    reasoning: str = ""
