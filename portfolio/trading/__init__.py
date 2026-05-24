"""Multi-Agent Trading Application.

Orchestrates 5 specialized agents via LangGraph to analyze stocks,
detect market regimes, scrape CNN Fear & Greed, decide options
strategies (Call/Put/Strangle), and execute via MCP paper trading.

Architecture:
  1. Security Agent       — Symbol validation, company profile, buy/sell context
  2. Risk/Sentiment Agent — CNN Fear & Greed + world news analysis
  3. Regime Agent         — Bull/Bear/Neutral market regime detection
  4. Decision Agent       — Options strategy selection (Call/Put/Strangle)
  5. Execution Agent      — MCP paper trading execution with confirmation
"""
