"""LangGraph state management for the trading workflow.

Defines the TradingState TypedDict that flows through all agent nodes,
carrying accumulated context and agent outputs through the graph.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages

from ..models import (
    ExecutionResult,
    MarketRegime,
    OptionChain,
    RegimeOutput,
    RiskSentimentOutput,
    SecurityInfo,
    StrategyDecision,
)


class TradingState(TypedDict):
    """State that flows through the LangGraph trading workflow.

    Each agent node reads from and writes to this state dict.
    LangGraph handles state merging through reducers.
    """

    # Input
    symbol: str  # User-provided stock symbol
    llm_provider: str  # "openai", "anthropic", or "nvidia"
    llm_model: str  # e.g. "gpt-4o", "claude-sonnet-4-20250514"
    openai_api_key: str  # Generic user-provided API key (empty = use provider env var)

    # Agent 1: Security Identification
    security: Optional[SecurityInfo]

    # Agent 2: Risk & Sentiment
    sentiment: Optional[RiskSentimentOutput]

    # Agent 3: Regime Detection
    regime: Optional[RegimeOutput]

    # Options Chain (fetched by graph, not a separate agent)
    options_chain: Optional[OptionChain]
    options_chain_metadata: dict[str, Any]

    # Agent 4: Strategy Decision
    strategy: Optional[StrategyDecision]

    # Agent 5: Execution
    execution: Optional[ExecutionResult]

    # Human-in-the-loop approval
    user_approved: bool  # Whether user has approved the execution
    user_rejection_reason: str  # Reason if trade was rejected by user

    # Flow control
    error: str
    stage: str  # Current processing stage for UI progress

    # For LangGraph message handling — add_messages appends to lists
    messages: Annotated[list, add_messages]
    # operator.add concatenates lists so each node's log appends instead of replacing
    log: Annotated[list[str], operator.add]  # Step-by-step log for UI transparency
