"""LangGraph orchestration for the multi-agent trading workflow.

The graph executes 5 agents in sequence:

  START
    ↓
  [Security Agent]  →  Validate symbol, get company profile
    ↓
  [Risk/Sentiment Agent]  →  CNN Fear & Greed, world news
    ↓
  [Regime Agent]  →  Bull/Bear/Neutral classification
    ↓
  [Fetch Options Chain]  →  Polygon.io or synthetic
    ↓
  [Decision Agent]  →  Call/Put/Strangle strategy selection
    ↓
  [Execution Agent]  →  MCP paper trading
    ↓
  END

Each node reads from and writes to TradingState.
Nodes handle errors internally so the workflow always completes.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from ..agents.security_agent import SecurityAgent
from ..agents.risk_sentiment_agent import RiskSentimentAgent
from ..agents.regime_agent import RegimeAgent
from ..agents.decision_agent import DecisionAgent
from ..agents.execution_agent import ExecutionAgent
from ..options.polygon_client import fetch_option_chain
from ..models import OptionStrategy
from .state import TradingState


# ════════════════════════════════════════════════════════════════════════
# Node Functions — each is a LangGraph node with error isolation
# ════════════════════════════════════════════════════════════════════════

def _node_security(state: TradingState) -> dict[str, Any]:
    """Agent 1: Security identification & validation."""
    try:
        agent = SecurityAgent()
        security = agent.analyze(state["symbol"])
        return {
            "security": security,
            "stage": "security",
            "log": [f"[Security] Identified: {security.company_name} ({security.symbol}) — {security.sector}"],
        }
    except Exception as e:
        return {
            "stage": "security",
            "error": f"Security agent failed: {e}",
            "log": [f"[Security] ERROR: {e}"],
        }


def _node_sentiment(state: TradingState) -> dict[str, Any]:
    """Agent 2: Risk & sentiment analysis."""
    try:
        agent = RiskSentimentAgent()
        sentiment = agent.analyze()
        fg = sentiment.fear_greed
        return {
            "sentiment": sentiment,
            "stage": "sentiment",
            "log": [
                f"[Risk/Sentiment] Fear & Greed: {fg.value}/100 ({fg.zone.value}) | "
                f"News: {len(sentiment.top_news)} headlines"
            ],
        }
    except Exception as e:
        return {
            "stage": "sentiment",
            "error": f"Sentiment agent failed: {e}",
            "log": [f"[Risk/Sentiment] ERROR: {e}"],
        }


def _node_regime(state: TradingState) -> dict[str, Any]:
    """Agent 3: Market regime detection."""
    try:
        agent = RegimeAgent()
        sentiment = state.get("sentiment")
        regime = agent.analyze(sentiment=sentiment)
        return {
            "regime": regime,
            "stage": "regime",
            "log": [
                f"[Regime] {regime.regime.value} "
                f"(confidence: {regime.confidence:.0%}) | S&P Trend: {regime.sp500_trend}"
            ],
        }
    except Exception as e:
        return {
            "stage": "regime",
            "error": f"Regime agent failed: {e}",
            "log": [f"[Regime] ERROR: {e}"],
        }


def _node_fetch_chain(state: TradingState) -> dict[str, Any]:
    """Fetch options chain for the security."""
    try:
        symbol = state["symbol"]
        chain = fetch_option_chain(symbol)
        return {
            "options_chain": chain,
            "stage": "options_chain",
            "log": [
                f"[Options Chain] {len(chain.calls)} calls, {len(chain.puts)} puts | "
                f"Underlying: ${chain.underlying_price:.2f}"
            ],
        }
    except Exception as e:
        return {
            "stage": "options_chain",
            "error": f"Options chain fetch failed: {e}",
            "log": [f"[Options Chain] ERROR: {e}"],
        }


def _node_decision(state: TradingState) -> dict[str, Any]:
    """Agent 4: Strategy decision."""
    try:
        agent = DecisionAgent()
        security = state.get("security")
        sentiment = state.get("sentiment")
        regime = state.get("regime")
        chain = state.get("options_chain")

        if not security or not sentiment or not regime or not chain:
            return {
                "stage": "decision",
                "error": "Missing required context for decision agent.",
                "log": ["[Decision] ERROR: Missing upstream data."],
            }

        strategy = agent.decide(
            security=security,
            sentiment=sentiment,
            regime=regime,
            chain=chain,
        )

        log_msg = (
            f"[Decision] Strategy: {strategy.strategy.value} "
            f"(confidence: {strategy.confidence:.0%})"
            + (f" | Strike: ${strategy.recommended_strike:.2f}" if strategy.recommended_strike else "")
            + (" | No trade — see rationale" if strategy.strategy == OptionStrategy.NO_TRADE else "")
        )

        return {
            "strategy": strategy,
            "stage": "decision",
            "log": [log_msg],
        }
    except Exception as e:
        return {
            "stage": "decision",
            "error": f"Decision agent failed: {e}",
            "log": [f"[Decision] ERROR: {e}"],
        }


def _node_execution(state: TradingState) -> dict[str, Any]:
    """Agent 5: MCP execution."""
    try:
        agent = ExecutionAgent()
        strategy = state.get("strategy")
        symbol = state["symbol"]

        if not strategy:
            return {
                "stage": "execution",
                "error": "No strategy decision to execute.",
                "log": ["[Execution] ERROR: No strategy available."],
            }

        result = agent.execute(strategy, symbol)

        if strategy.strategy == OptionStrategy.NO_TRADE:
            log_msg = f"[Execution] No trade — {strategy.rationale[:100]}..."
        else:
            confirmation = result.confirmation  # dict[str, Any]
            status = confirmation.get("status", "Unknown")
            filled = confirmation.get("filled_price", "N/A")
            total = confirmation.get("total_cost", "N/A")
            log_msg = (
                f"[Execution] {status} | Strategy: {strategy.strategy.value} "
                f"| Fill: ${filled}/contract | Total: ${total}"
            )

        return {
            "execution": result,
            "stage": "execution",
            "log": [log_msg],
        }
    except Exception as e:
        return {
            "stage": "execution",
            "error": f"Execution agent failed: {e}",
            "log": [f"[Execution] ERROR: {e}"],
        }


# ════════════════════════════════════════════════════════════════════════
# Graph Construction — linear pipeline with add_edge
# ════════════════════════════════════════════════════════════════════════

def build_trading_graph() -> StateGraph:
    """Build and compile the LangGraph trading workflow.

    Returns:
        A compiled StateGraph ready for invocation.
    """
    graph = StateGraph(TradingState)

    # Add nodes
    graph.add_node("security", _node_security)
    graph.add_node("sentiment", _node_sentiment)
    graph.add_node("regime", _node_regime)
    graph.add_node("fetch_chain", _node_fetch_chain)
    graph.add_node("decision", _node_decision)
    graph.add_node("execution", _node_execution)

    # Set entry point
    graph.set_entry_point("security")

    # Linear pipeline — each node always proceeds to the next
    graph.add_edge("security", "sentiment")
    graph.add_edge("sentiment", "regime")
    graph.add_edge("regime", "fetch_chain")
    graph.add_edge("fetch_chain", "decision")
    graph.add_edge("decision", "execution")
    graph.add_edge("execution", END)

    return graph.compile()


def run_trading_workflow(symbol: str) -> dict:
    """Run the full multi-agent trading workflow for a symbol.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL').

    Returns:
        The final TradingState dict with all agent outputs.
    """
    graph = build_trading_graph()

    initial_state: TradingState = {
        "symbol": symbol.strip().upper(),
        "security": None,
        "sentiment": None,
        "regime": None,
        "options_chain": None,
        "strategy": None,
        "execution": None,
        "error": "",
        "stage": "initializing",
        "messages": [],
        "log": [f"Starting multi-agent workflow for {symbol}..."],
    }

    result = graph.invoke(initial_state)
    return result
