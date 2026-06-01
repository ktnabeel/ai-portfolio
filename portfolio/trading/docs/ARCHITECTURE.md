# Multi-Agent Options Trading Application — Architecture

## Overview

A LangGraph-orchestrated multi-agent trading system that analyzes stock symbols, scrapes market sentiment (CNN Fear & Greed), detects market regimes (Bull/Bear/Neutral), selects options strategies (Call/Put/Strangle), pauses for human review, and executes approved paper trades via an MCP server.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GRADIO UI LAYER                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Hoverable Pipeline Map: Security → Sentiment → Regime → Chain │  │
│  │ → Decision → Human Review → Execution                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────┐        ┌────────────────────────────────┐ │
│  │ Left Control Panel  │        │ Right Trace Panel              │ │
│  │ Inputs, HITL review,│        │ Agent cards, MCP connectivity, │ │
│  │ order confirmation  │        │ tool-call details              │ │
│  └─────────────────────┘        └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LANGGRAPH ORCHESTRATION                        │
│                                                                     │
│  START → [Security] → [Sentiment] → [Regime] → [Chain] →           │
│          [Decision] → [Human Review] → [Execution] → END            │
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
- **Tools:** yfinance, selected LangChain chat model
- **Output:** `SecurityInfo` (company name, sector, market cap, price, options availability)
- **Reasoning:** Validates the symbol, identifies the company, determines if options are available

### 2. Risk & Sentiment Agent (`agents/risk_sentiment_agent.py`)
- **Input:** None (fetches independently)
- **Tools:** CNN Fear & Greed scraper, RSS news scraper, selected LangChain chat model
- **Output:** `RiskSentimentOutput` (Fear & Greed value/zone, world news, risk level, market trend)
- **Reasoning:** Synthesizes sentiment data and news into a risk assessment

### 3. Regime Detection Agent (`agents/regime_agent.py`)
- **Input:** `RiskSentimentOutput` (optional context)
- **Tools:** yfinance (SPY data), technical indicators (RSI, SMA, volatility), selected LangChain chat model
- **Output:** `RegimeOutput` (Bull/Bear/Neutral, confidence, indicators)
- **Reasoning:** Classifies the market regime using S&P 500 data and context

### 4. Decision Agent (`agents/decision_agent.py`)
- **Input:** All upstream outputs (`SecurityInfo`, `RiskSentimentOutput`, `RegimeOutput`, `OptionChain`)
- **Tools:** Options chain data, selected LangChain chat model
- **Output:** `StrategyDecision` (Call/Put/Strangle/No Trade, strike, expiration, risk/reward)
- **Reasoning:** Selects optimal options strategy based on comprehensive market context

### 5. Execution Agent (`agents/execution_agent.py`)
- **Input:** `StrategyDecision`
- **Tools:** MCP Trading Server (paper trading)
- **Output:** `ExecutionResult` (order confirmation, P&L, status)
- **Reasoning:** Formats and submits the order, confirms execution

### Human Review Gate (`ui/trading_ui.py`)
- **Input:** Serialized analysis state and `StrategyDecision`
- **Tools:** Gradio approval/rejection callbacks
- **Output:** Either a rejected recommendation record, a skipped No Trade path, or an approved execution request
- **Reasoning:** Keeps paper execution separate from analysis so users can inspect the recommendation before any simulated order is submitted

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
Decision Agent ←── Selected LLM provider/model reasoning
    │
    ▼
Human Review Gate ←── User approval/rejection
    │
    ▼
Execution Agent ←── MCP Paper Trading Server
    │
    ▼
UI displays: agent traces, MCP connectivity, left-panel order confirmation, account summary
```

## Key Design Decisions

1. **LangGraph over manual orchestration**: Directed graph ensures deterministic execution order and clean state management
2. **MCP Protocol**: Follows the Model Context Protocol pattern for tool exposure, enabling LLMs to interact with the broker through structured tool calls
3. **Black-Scholes fallback**: When Polygon API is unavailable, synthetic option chains are generated using Black-Scholes with volatility smiles
4. **Hoverable pipeline audit map**: Each agent tile exposes input/output traces, path summaries, and scrollable tooltip bodies for long Regime and Decision messages
5. **Human-in-the-loop execution**: Analysis stops before paper execution. A tradeable strategy must be approved or rejected before the MCP server receives an order
6. **Separated execution surfaces**: The left control panel owns the order confirmation card, while the right trace panel stays focused on MCP connectivity and tool-call status
7. **Rule-based fallbacks**: Every agent has a rule-based fallback path when the LLM is unavailable, ensuring the system always produces output

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
│   └── trading_ui.py        # Gradio UI with pipeline map, HITL review, order confirmation
└── docs/
    ├── ARCHITECTURE.md       # This file
    ├── FLOWS.md              # Detailed workflow flows
    └── README.md             # Usage guide
```

## Dependencies

- **langgraph**: Agent orchestration & state management
- **langchain**: LLM interaction framework
- **langchain-openai / langchain-anthropic**: OpenAI and Anthropic chat model integrations
- **mcp**: Model Context Protocol
- **yfinance**: Market data (prices, fundamentals, SPY)
- **httpx + beautifulsoup4**: Web scraping (Fear & Greed, news)
- **scipy**: Black-Scholes calculations (norm.cdf)
- **numpy**: Technical indicator computations
- **gradio**: UI framework

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | No | OpenAI model reasoning; rule-based fallback is used when absent |
| `ANTHROPIC_API_KEY` | No | Anthropic model reasoning; rule-based fallback is used when absent |
| `POLYGON_API_KEY` | No | Real options chain data (falls back to synthetic) |
