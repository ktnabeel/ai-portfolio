# Multi-Agent Options Trading — Usage Guide

## Quick Start

### Prerequisites
1. Python 3.10+
2. Optional LLM API key: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
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

Open http://127.0.0.1:7860 in your browser, then click the **Trading Desk** tab.

## Usage

1. **Enter a stock symbol** in the input field (e.g., `AAPL`, `NVDA`, `TSLA`, `SPY`)
2. **Click "Run Multi-Agent Analysis"**
3. Watch the specialized agents execute in sequence on the pipeline map:
   - 🔍 **Security Agent**: Validates the symbol, shows company profile
   - 🌐 **Risk/Sentiment Agent**: Shows CNN Fear & Greed + world news
   - 🔄 **Regime Agent**: Classifies Bull/Bear/Neutral market
   - 🎯 **Decision Agent**: Selects Call/Put/Strangle strategy with rationale
   - 🔍 **Human Review**: Pauses for approval when the decision is tradeable
   - 💸 **Execution Agent**: Executes paper trade via MCP server after approval

4. **Hover or focus each pipeline tile** to inspect its input and output trace. Long traces scroll inside the tooltip so full detection and decision messages remain readable.
5. If the Decision Agent recommends **No Trade**, no execution review is required.
6. If the Decision Agent recommends a tradeable strategy, use the left-panel review controls:
   - **Execute Trade** submits the paper order through MCP.
   - **Reject Trade** records the rejection reason and skips execution.
7. After execution, the **order confirmation card appears in the left control panel** below the review controls. The right-side trace remains reserved for MCP connectivity and tool-call details.
8. The account summary appears after execution or rejection and continues to show positions, order history, rejection history, balances, and P&L.

## Trading Desk UI

- **Pipeline audit map:** Displays Security, Risk/Sentiment, Regime, Options Chain, Decision, Human Review, and Execution tiles.
- **Trace tooltips:** Each tile includes `Input` and `Output` sections. Top-row tooltips open below the tile; bottom-row tooltips open upward on desktop and stack below on smaller screens.
- **Path summary:** The flow footer explains the route taken through the workflow, including No Trade, Human Review, Rejected, and Execution outcomes.
- **Review panel:** Approval/rejection controls appear only for tradeable recommendations.
- **Order confirmation slot:** Successful execution renders the full order confirmation in the left panel so it stays close to the approval action.
- **MCP trace panel:** The right trace shows server connectivity and tool-call status without duplicating the full order confirmation card.
- **Stale-state clearing:** New analysis, rejection, No Trade, account reset, or invalid execution state clears old confirmation HTML.

## Paper Trading Account

- **Starting balance:** $100,000
- **Commission:** $0.65 per contract
- **Orders fill instantly** at estimated market prices
- **Access account status** via the MCP server's `get_account_status` tool
- **Reset account** via `reset_account` tool
- **Rejected recommendations** are recorded in rejection history without changing positions

## Strategies Explained

| Strategy | When Used | Market View | Risk | Reward |
|----------|-----------|-------------|------|--------|
| **Long Call** | Bullish outlook | Price will rise | Premium paid | Unlimited |
| **Long Put** | Bearish outlook | Price will fall | Premium paid | Strike - Premium |
| **Long Strangle** | High volatility expected | Big move, direction unclear | Premium paid (both legs) | Unlimited |
| **No Trade** | Unfavorable conditions | No clear edge | $0 | $0 |

## Agent Reasoning

Every agent uses the selected LLM provider/model for reasoning when an API key is available, with rule-based fallbacks otherwise. The UI surfaces each stage's trace through the pipeline map:
- **Why** the security is valid/invalid
- **What** the Fear & Greed index means for the market
- **Why** the regime is classified as Bull/Bear/Neutral
- **Why** a specific strategy was selected over alternatives
- **What** happened with the execution

This transparency ensures you understand every decision in the chain.

## Fallback Behavior

If any component fails:
- **No internet / yfinance down**: Agents use fallback data and notify you
- **No LLM API key**: Agents use rule-based decision logic
- **No Polygon API key**: Synthetic option chains generated via Black-Scholes

The system is designed to always produce output, even with degraded data sources.

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | (optional) | OpenAI model reasoning; rule-based fallback is used when absent |
| `ANTHROPIC_API_KEY` | (optional) | Anthropic model reasoning; rule-based fallback is used when absent |
| `POLYGON_API_KEY` | (optional) | Real options chain data |

### Model Selection

The Trading Desk has provider and model dropdowns in the left control panel.

- OpenAI default: `gpt-4o`
- Anthropic default: `claude-sonnet-4-20250514`
- Leave the API key field blank to use the matching environment variable.

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
python -m compileall app.py portfolio scripts tests
python -m pytest -q tests/test_trading_ui_flow.py tests/test_trading_features.py
python -m pytest -q
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
