"""TradingAgents Portfolio Manager — FastAPI service wrapping the multi-agent trading framework.

Provides a REST API for running multi-agent market analysis and portfolio
decision workflows powered by the TradingAgents LangGraph pipeline.
"""

from .api import app
from .manager import PortfolioManager
from .models import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    HealthResponse,
    AgentCard,
    PortfolioDecision,
    PortfolioRating,
)
from .render import render_trading_agents_tab, TRADING_AGENTS_CSS

__all__ = [
    "app",
    "PortfolioManager",
    "AnalysisRequest",
    "AnalysisResponse",
    "AnalysisStatus",
    "HealthResponse",
    "AgentCard",
    "PortfolioDecision",
    "PortfolioRating",
    "render_trading_agents_tab",
    "TRADING_AGENTS_CSS",
]
