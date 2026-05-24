# Multi-Agent Options Trading Application — Architecture

## Overview

A LangGraph-orchestrated multi-agent trading system that analyzes stock symbols, scrapes market sentiment (CNN Fear & Greed), detects market regimes (Bull/Bear/Neutral), selects options strategies (Call/Put/Strangle), and executes paper trades via an MCP server.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GRADIO UI LAYER                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Security │  │Sentiment │  │  Regime  │  │ Decision │  │Exec   │ │
│  │  Panel   │  │  Panel   │  │  Panel   │  │  Panel   │  │Panel  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └───────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LANGGRAPH ORCHESTRATION                        │
│                                                                     │
│  START → [Security] → [Sentiment] → [Regime] → [Chain] →           │
│          [Decision] → [Execution] → END                             │
│                                                                     │
│  State: TradingState (TypedDict) flows through all nodes            │
└─────────────────────────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   yfinance API    │ │  CNN Fear & Greed │ │  Polygon.io API   │
│  (Market Data)    │ │    (Scraper)      │ │ (Options Chains)  │
└───────────────────┘ └───────────────────┘ └───────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MCP TRADING SERVER                               │
│  Tools: get_account_status, place_option_order,                     │
│         cancel_order, get_order_history, reset_account              │
│  Brokers: Paper Trading (Simulated), Polygon.io (Real data)         │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent Responsibilities

### 1. Security Agent (`agents/security_agent.py`)
- **Input:** Stock symbol (e.g., "AAPL")
- **Tools:** yfinance, OpenAI GPT-4o
- **Output:** `SecurityInfo` (company name, sector, market cap, price, options availability)
- **Reasoning:** Validates the symbol, identifies the company, determines if options are available

### 2. Risk & Sentiment Agent (`agents/risk_sentiment_agent.py`)
- **Input:** None (fetches independently)
- **Tools:** CNN Fear & Greed scraper, RSS news scraper, OpenAI GPT-4o
- **Output:** `RiskSentimentOutput` (Fear & Greed value/zone, world news, risk level, market trend)
- **Reasoning:** Synthesizes sentiment data and news into a risk assessment

### 3. Regime Detection Agent (`agents/regime_agent.py`)
- **Input:** `RiskSentimentOutput` (optional context)
- **Tools:** yfinance (SPY data), technical indicators (RSI, SMA, volatility), OpenAI GPT-4o
- **Output:** `RegimeOutput` (Bull/Bear/Neutral, confidence, indicators)
- **Reasoning:** Classifies the market regime using S&P 500 data and context

### 4. Decision Agent (`agents/decision_agent.py`)
- **Input:** All upstream outputs (`SecurityInfo`, `RiskSentimentOutput`, `RegimeOutput`, `OptionChain`)
- **Tools:** Options chain data, OpenAI GPT-4o
- **Output:** `StrategyDecision` (Call/Put/Strangle/No Trade, strike, expiration, risk/reward)
- **Reasoning:** Selects optimal options strategy based on comprehensive market context

### 5. Execution Agent (`agents/execution_agent.py`)
- **Input:** `StrategyDecision`
- **Tools:** MCP Trading Server (paper trading)
- **Output:** `ExecutionResult` (order confirmation, P&L, status)
- **Reasoning:** Formats and submits the order, confirms execution

## Data Flow

```
User Input (Symbol)
    │
    ▼
Security Agent ←── yfinance API
    │
    ▼
Risk/Sentiment Agent ←── CNN Fear & Greed scraper, RSS news
    │
    ▼
Regime Agent ←── yfinance (SPY), technical indicators
    │
    ▼
Options Chain Fetch ←── Polygon.io API / Black-Scholes synthetic
    │
    ▼
Decision Agent ←── OpenAI GPT-4o reasoning
    │
    ▼
Execution Agent ←── MCP Paper Trading Server
    │
    ▼
UI displays: all agent reasoning, execution confirmation
```

## Key Design Decisions

1. **LangGraph over manual orchestration**: Directed graph ensures deterministic execution order and clean state management
2. **MCP Protocol**: Follows the Model Context Protocol pattern for tool exposure, enabling LLMs to interact with the broker through structured tool calls
3. **Black-Scholes fallback**: When Polygon API is unavailable, synthetic option chains are generated using Black-Scholes with volatility smiles
4. **Per-agent reasoning panels**: Each agent's output is displayed in its own UI tab with the LLM's reasoning visible, providing full transparency
5. **Rule-based fallbacks**: Every agent has a rule-based fallback path when the LLM is unavailable, ensuring the system always produces output

## File Structure

```
portfolio/trading/
├── __init__.py              # Package overview
├── models.py                # Pydantic models & TypedDict
├── agents/
│   ├── __init__.py
│   ├── security_agent.py    # Agent 1: Symbol validation
│   ├── risk_sentiment_agent.py  # Agent 2: Fear & Greed + News
│   ├── regime_agent.py      # Agent 3: Market regime
│   ├── decision_agent.py    # Agent 4: Strategy selection
│   └── execution_agent.py   # Agent 5: Trade execution
├── graph/
│   ├── __init__.py
│   ├── state.py             # TradingState TypedDict
│   └── trading_graph.py     # LangGraph workflow
├── mcp/
│   ├── __init__.py
│   ├── broker.py            # Simulated paper trading broker
│   └── trading_server.py    # MCP server with tool definitions
├── options/
│   ├── __init__.py
│   ├── black_scholes.py     # Black-Scholes pricing & Greeks
│   └── polygon_client.py    # Polygon.io API + synthetic fallback
├── scrapers/
│   ├── __init__.py
│   ├── cnn_fear_greed.py    # CNN Fear & Greed scraper
│   └── news_scraper.py      # World news RSS scraper
├── ui/
│   ├── __init__.py
│   └── trading_ui.py        # Gradio UI with per-agent panels
└── docs/
    ├── ARCHITECTURE.md       # This file
    ├── FLOWS.md              # Detailed workflow flows
    └── README.md             # Usage guide
```

## Dependencies

- **langgraph**: Agent orchestration & state management
- **langchain**: LLM interaction framework
- **langchain-openai**: OpenAI GPT-4o integration
- **mcp**: Model Context Protocol
- **yfinance**: Market data (prices, fundamentals, SPY)
- **httpx + beautifulsoup4**: Web scraping (Fear & Greed, news)
- **scipy**: Black-Scholes calculations (norm.cdf)
- **numpy**: Technical indicator computations
- **gradio**: UI framework

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | GPT-4o reasoning for all agents |
| `POLYGON_API_KEY` | No | Real options chain data (falls back to synthetic) |
