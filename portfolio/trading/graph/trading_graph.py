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

import os
from typing import Any

from langgraph.graph import END, StateGraph

from .._llm import create_llm
from ..agents.security_agent import SecurityAgent
from ..agents.risk_sentiment_agent import RiskSentimentAgent
from ..agents.regime_agent import RegimeAgent
from ..agents.decision_agent import DecisionAgent
from ..agents.execution_agent import ExecutionAgent
from ..mcp.trading_server import MCPTradingServer
from ..options.polygon_client import fetch_option_chain
from ..models import OptionChain, OptionContract, OptionStrategy
from .state import TradingState


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════

def _make_llm(state: TradingState) -> "BaseChatModel | None":
    """Build a ChatModel from the user's provider/model/key choices.

    Returns a ``BaseChatModel`` configured per the state, or ``None``
    if no API key is available — agents fall back to deterministic,
    rule-based reasoning when ``llm`` is ``None``.
    """
    provider = state.get("llm_provider", "") or "openai"
    model = state.get("llm_model", "") or None
    api_key = state.get("openai_api_key", "") or None

    if provider not in ("openai", "anthropic", "nvidia"):
        return None

    # Resolve API key: user-provided → env var → None (deterministic)
    effective_key = api_key.strip() if api_key else ""
    if not effective_key:
        env_var = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
        }[provider]
        effective_key = os.environ.get(env_var, "")

    if not effective_key:
        return None  # No key available → deterministic mode

    try:
        return create_llm(provider=provider, model=model, api_key=effective_key)  # type: ignore[arg-type]
    except Exception:
        return None


def _is_deterministic_mode(state: TradingState) -> bool:
    """Check whether the workflow is running in deterministic (no-LLM) mode."""
    provider = state.get("llm_provider", "") or "openai"
    api_key = (state.get("openai_api_key", "") or "").strip()
    if api_key:
        return False
    env_var = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
    }.get(provider, "OPENAI_API_KEY")
    return not os.environ.get(env_var, "")


def _option_chain_from_mcp_data(data: Any) -> tuple[OptionChain, dict[str, Any]]:
    """Validate a read-only MCP option-chain payload into the existing model."""
    if not isinstance(data, dict):
        raise ValueError("MCP option-chain payload was not an object")

    calls = [
        OptionContract(**contract)
        for contract in data.get("calls", [])
        if isinstance(contract, dict)
    ]
    puts = [
        OptionContract(**contract)
        for contract in data.get("puts", [])
        if isinstance(contract, dict)
    ]
    chain = OptionChain(
        symbol=str(data["symbol"]).upper(),
        underlying_price=float(data["underlying_price"]),
        expiration_dates=list(data.get("expiration_dates", [])),
        calls=calls,
        puts=puts,
    )
    if not chain.calls and not chain.puts:
        raise ValueError("MCP option-chain payload had no contracts")

    metadata = {
        "source": data.get("source", "yfinance"),
        "freshness": data.get("freshness", ""),
        "is_realtime": bool(data.get("is_realtime", False)),
    }
    if data.get("warning"):
        metadata["warning"] = data["warning"]
    return chain, metadata


def _provider_log_suffix(metadata: dict[str, Any]) -> str:
    source = metadata.get("source", "unknown")
    freshness = metadata.get("freshness", "")
    realtime = "realtime" if metadata.get("is_realtime") else "delayed/best effort"
    suffix = f" | Source: {source} ({realtime})"
    if freshness:
        suffix += f" | Freshness: {freshness}"
    if metadata.get("warning"):
        suffix += f" | Warning: {metadata['warning']}"
    return suffix


# ════════════════════════════════════════════════════════════════════════
# Node Functions — each is a LangGraph node with error isolation
# ════════════════════════════════════════════════════════════════════════

def _node_security(state: TradingState) -> dict[str, Any]:
    """Agent 1: Security identification & validation."""
    try:
        llm = _make_llm(state)
        agent = SecurityAgent(llm=llm)
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
        llm = _make_llm(state)
        agent = RiskSentimentAgent(llm=llm)
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
        llm = _make_llm(state)
        agent = RegimeAgent(llm=llm)
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
    symbol = state["symbol"]
    mcp_error = ""
    try:
        response = MCPTradingServer().call_tool("get_option_chain", {"symbol": symbol})
        if response.success and response.data:
            chain, metadata = _option_chain_from_mcp_data(response.data)
            return {
                "options_chain": chain,
                "options_chain_metadata": metadata,
                "stage": "options_chain",
                "log": [
                    f"[Options Chain] {len(chain.calls)} calls, {len(chain.puts)} puts | "
                    f"Underlying: ${chain.underlying_price:.2f}"
                    f"{_provider_log_suffix(metadata)}"
                ],
            }
        mcp_error = response.error or "MCP returned incomplete option-chain data."
    except Exception as e:
        mcp_error = str(e)

    try:
        chain = fetch_option_chain(symbol)
        fallback_source = "polygon" if os.environ.get("POLYGON_API_KEY") else "yfinance"
        metadata = {
            "source": fallback_source,
            "freshness": "",
            "is_realtime": False,
            "warning": (
                "Direct provider fallback used after MCP option-chain failure; "
                f"provider may have used synthetic data. MCP error: {mcp_error}"
            ),
        }
        return {
            "options_chain": chain,
            "options_chain_metadata": metadata,
            "stage": "options_chain",
            "log": [
                f"[Options Chain] {len(chain.calls)} calls, {len(chain.puts)} puts | "
                f"Underlying: ${chain.underlying_price:.2f}"
                f"{_provider_log_suffix(metadata)}"
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
        llm = _make_llm(state)
        agent = DecisionAgent(llm=llm)
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


def _route_after_decision(state: TradingState) -> str:
    """Conditional edge: only proceed to execution if the user approved.

    When ``user_approved`` is False, the graph ends after the Decision
    Agent so the user can review the analysis before committing to a trade.
    """
    if state.get("user_approved"):
        return "execution"
    return "end"


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
    graph.add_node("security_agent", _node_security)
    graph.add_node("sentiment_agent", _node_sentiment)
    graph.add_node("regime_agent", _node_regime)
    graph.add_node("fetch_chain", _node_fetch_chain)
    graph.add_node("decision_agent", _node_decision)
    graph.add_node("execution_agent", _node_execution)

    # Set entry point
    graph.set_entry_point("security_agent")

    # Linear pipeline for analysis (runs every time)
    graph.add_edge("security_agent", "sentiment_agent")
    graph.add_edge("sentiment_agent", "regime_agent")
    graph.add_edge("regime_agent", "fetch_chain")
    graph.add_edge("fetch_chain", "decision_agent")

    # Human-in-the-loop: conditional edge — only execute if user approved
    graph.add_conditional_edges(
        "decision_agent",
        _route_after_decision,
        {
            "execution": "execution_agent",
            "end": END,
        },
    )
    graph.add_edge("execution_agent", END)

    return graph.compile()


def run_trading_workflow(
    symbol: str,
    llm_provider: str = "openai",
    llm_model: str = "",
    openai_api_key: str = "",
    user_approved: bool = False,
    user_rejection_reason: str = "",
) -> dict:
    """Run the multi-agent trading workflow for a symbol.

    The workflow always runs the analysis pipeline (Security → Sentiment
    → Regime → Options Chain → Decision).  Execution only proceeds when
    *user_approved* is ``True`` — this provides human-in-the-loop review.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL').
        llm_provider: ``"openai"``, ``"anthropic"``, or ``"nvidia"``.
        llm_model: Model name (e.g. ``"gpt-4o"``, ``"claude-sonnet-4-20250514"``).
        openai_api_key: User-provided API key (empty → env var fallback).
        user_approved: Whether the user has approved the trade.
            Defaults to ``False`` so the first run stops before execution.
        user_rejection_reason: Human-readable reason if the user rejected.

    Returns:
        The final TradingState dict with all agent outputs.
    """
    graph = build_trading_graph()

    initial_state: TradingState = {
        "symbol": symbol.strip().upper(),
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "openai_api_key": openai_api_key,
        "user_approved": user_approved,
        "user_rejection_reason": user_rejection_reason,
        "security": None,
        "sentiment": None,
        "regime": None,
        "options_chain": None,
        "options_chain_metadata": {},
        "strategy": None,
        "execution": None,
        "error": "",
        "stage": "initializing",
        "messages": [],
        "log": [
            f"Starting multi-agent workflow for {symbol}..."
            f"{' [HITL: approved]' if user_approved else ' [HITL: pending review]'}"
        ],
    }

    result = graph.invoke(initial_state)
    return result
