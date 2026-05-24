# Multi-Agent Options Trading — Usage Guide

## Quick Start

### Prerequisites
1. Python 3.10+
2. OpenAI API key (set as `OPENAI_API_KEY` environment variable)
3. Optional: Polygon.io API key (set as `POLYGON_API_KEY`) for real options data

### Installation
```bash
cd ai-portfolio
uv sync
```

### Running
```bash
uv run python app.py
```

Open http://127.0.0.1:7860 in your browser, then click the **🤖 Trading Agent** tab.

## Usage

1. **Enter a stock symbol** in the input field (e.g., `AAPL`, `NVDA`, `TSLA`, `SPY`)
2. **Click "Run Multi-Agent Analysis"**
3. Watch 5 specialized AI agents execute in sequence:
   - 🔍 **Security Agent**: Validates the symbol, shows company profile
   - 🌐 **Risk/Sentiment Agent**: Shows CNN Fear & Greed + world news
   - 🔄 **Regime Agent**: Classifies Bull/Bear/Neutral market
   - 🎯 **Decision Agent**: Selects Call/Put/Strangle strategy with rationale
   - 💸 **Execution Agent**: Executes paper trade via MCP server

4. **Browse per-agent tabs** to see WHY each decision was made — the LLM's full reasoning is displayed

## Paper Trading Account

- **Starting balance:** $100,000
- **Commission:** $0.65 per contract
- **Orders fill instantly** at estimated market prices
- **Access account status** via the MCP server's `get_account_status` tool
- **Reset account** via `reset_account` tool

## Strategies Explained

| Strategy | When Used | Market View | Risk | Reward |
|----------|-----------|-------------|------|--------|
| **Long Call** | Bullish outlook | Price will rise | Premium paid | Unlimited |
| **Long Put** | Bearish outlook | Price will fall | Premium paid | Strike - Premium |
| **Long Strangle** | High volatility expected | Big move, direction unclear | Premium paid (both legs) | Unlimited |
| **No Trade** | Unfavorable conditions | No clear edge | $0 | $0 |

## Agent Reasoning

Every agent uses OpenAI GPT-4o for reasoning. The LLM explains:
- **Why** the security is valid/invalid
- **What** the Fear & Greed index means for the market
- **Why** the regime is classified as Bull/Bear/Neutral
- **Why** a specific strategy was selected over alternatives
- **What** happened with the execution

This transparency ensures you understand every decision in the chain.

## Fallback Behavior

If any component fails:
- **No internet / yfinance down**: Agents use fallback data and notify you
- **No OpenAI API key**: Agents use rule-based decision logic
- **No Polygon API key**: Synthetic option chains generated via Black-Scholes

The system is designed to always produce output, even with degraded data sources.

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | (required) | GPT-4o for agent reasoning |
| `POLYGON_API_KEY` | (optional) | Real options chain data |

### Model Selection

By default, all agents use `gpt-4o`. To change:
- Edit `model_name="gpt-4o"` in each agent's `__init__` call
- Or set environment variable and modify `ChatOpenAI(model=...)` calls

## MCP Server Tools

The paper trading MCP server exposes these tools:

| Tool | Description |
|------|-------------|
| `get_account_status` | Returns cash, equity, P&L, positions |
| `place_option_order` | Places a Call/Put/Strangle order |
| `cancel_order` | Cancels a pending order |
| `get_order_history` | Returns recent order history |
| `reset_account` | Resets to $100,000 starting balance |

## Development

### Running Tests
```bash
uv run pytest tests/
```

### Adding a New Agent
1. Create `agents/my_agent.py` with `analyze()` method
2. Add agent node to `graph/trading_graph.py`
3. Add edge in the graph
4. Add output field to `TradingState` in `graph/state.py`
5. Add UI panel in `ui/trading_ui.py`

### Adding a New MCP Tool
1. Add tool definition to `MCP_TOOLS` list in `mcp/trading_server.py`
2. Implement `_handle_*` method in `MCPTradingServer`
3. Register in `self._tools` dict
