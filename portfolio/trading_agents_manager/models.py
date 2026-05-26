"""Pydantic models for the TradingAgents Portfolio Manager API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class PortfolioRating(str, Enum):
    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


# ── Request / Response ─────────────────────────────────────────────────────


class AnalysisRequest(BaseModel):
    """Request to run a multi-agent analysis on a ticker."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=10,
        pattern=r"^[A-Za-z0-9.^]+$",
        description="Stock ticker symbol (e.g., AAPL, NVDA, MSFT)",
        examples=["AAPL"],
    )
    date: Optional[str] = Field(
        default=None,
        description="Analysis date in YYYY-MM-DD format. Defaults to today.",
        examples=["2026-05-25"],
    )
    analysts: Optional[list[str]] = Field(
        default=None,
        description="Analyst types to include: market, social, news, fundamentals. Defaults to all.",
        examples=[["market", "news", "fundamentals"]],
    )


class AgentCard(BaseModel):
    """Output card from a single agent in the pipeline."""

    agent_name: str = Field(..., description="Human-readable agent name")
    agent_type: str = Field(..., description="Agent role: security, sentiment, regime, decision, execution")
    icon: str = Field(default="", description="Emoji icon for the agent")
    status: str = Field(default="complete", description="complete, running, error, skipped")
    accent_color: str = Field(default="#4da6ff", description="CSS accent color for the card")
    content: str = Field(default="", description="Formatted analysis content (markdown)")
    reasoning: str = Field(default="", description="Agent's reasoning summary")


class PortfolioDecision(BaseModel):
    """Final portfolio manager decision."""

    rating: PortfolioRating = Field(..., description="Buy/Sell/Hold rating")
    symbol: str = Field(..., description="Ticker symbol analyzed")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0–1)",
    )
    summary: str = Field(default="", description="Executive summary of the decision")
    rationale: str = Field(default="", description="Detailed rationale with evidence")
    risk_assessment: str = Field(default="", description="Risk evaluation summary")
    timestamp: datetime = Field(default_factory=datetime.now)


class AnalysisResponse(BaseModel):
    """Complete analysis result returned by the API."""

    id: str = Field(..., description="Unique analysis ID")
    symbol: str = Field(..., description="Analyzed ticker")
    status: AnalysisStatus = Field(..., description="Current analysis status")
    decision: Optional[PortfolioDecision] = Field(
        default=None,
        description="Final portfolio decision (when complete)",
    )
    agent_cards: list[AgentCard] = Field(
        default_factory=list,
        description="Per-agent output cards from the pipeline",
    )
    execution_log: list[str] = Field(
        default_factory=list,
        description="Step-by-step execution log",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if status is failed",
    )
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service health status")
    version: str = Field(default="0.1.0", description="API version")
    tradingagents_version: str = Field(default="0.2.4", description="TradingAgents framework version")
    uptime_seconds: float = Field(default=0.0, description="Service uptime in seconds")
