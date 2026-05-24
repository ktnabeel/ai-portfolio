# Trading Workflow — Detailed Flows

## Main Flow: Symbol → Execution

```
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 1: SECURITY IDENTIFICATION                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Input:   "AAPL"                                                          │
│ Action:  yfinance fetch → validate symbol → get company profile          │
│ LLM:     GPT-4o reasons about company position, sector, optionability    │
│ Output:  SecurityInfo { name, sector, marketCap, price, isOptionable }   │
│                                                                          │
│ Fallback: If yfinance fails, return unknown company with error message.  │
│           If symbol has no options, isOptionable = false.                │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 2: RISK & SENTIMENT                                                 │
├──────────────────────────────────────────────────────────────────────────┤
│ Action:                                                                  │
│   a) Scrape https://www.cnn.com/markets/fear-and-greed                   │
│      - Extract current value (0-100)                                     │
│      - Classify zone: Extreme Fear → Extreme Greed                       │
│      - Extract historical comparison values                              │
│                                                                          │
│   b) Scrape RSS news feeds (Yahoo Finance, Reuters, CNBC)                │
│      - Filter for market-moving keywords                                 │
│      - Classify each headline: Positive / Negative / Neutral             │
│      - Cap at 8 items                                                    │
│                                                                          │
│ LLM:     GPT-4o synthesizes Fear & Greed + news into:                    │
│          - Market Trend summary (2-3 sentences)                          │
│          - Risk Level (LOW / MODERATE / HIGH)                            │
│          - Key driving factors (3-5 bullets)                             │
│                                                                          │
│ Output:  RiskSentimentOutput { fearGreed, topNews, marketTrend, risk }   │
│                                                                          │
│ Fallback: If scraping fails, use neutral Fear & Greed (50) with          │
│           warning message and "Unable to fetch" news item.               │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 3: MARKET REGIME DETECTION                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Action:                                                                  │
│   a) Fetch SPY (S&P 500 ETF) 6-month history                             │
│   b) Compute technical indicators:                                       │
│      - 50-day and 200-day Simple Moving Averages                         │
│      - RSI (14-period)                                                   │
│      - 20-day annualized volatility                                      │
│      - 50-day SMA slope (trend direction)                                │
│                                                                          │
│ LLM:     GPT-4o classifies regime using indicators + sentiment context:  │
│          - BULL:  Price > SMAs, RSI 55-70, positive slope, low vol      │
│          - BEAR:  Price < SMAs, RSI < 45, negative slope, high vol      │
│          - NEUTRAL: Mixed signals, RSI 45-55, sideways                  │
│                                                                          │
│ Output:  RegimeOutput { regime, confidence, volatility, indicators }     │
│                                                                          │
│ Fallback: Rule-based classification using price vs SMAs, RSI, and slope. │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 4: OPTIONS CHAIN FETCH                                              │
├──────────────────────────────────────────────────────────────────────────┤
│ Action:                                                                  │
│   a) Try Polygon.io API (if POLYGON_API_KEY set)                         │
│      - GET /v3/reference/options/contracts?underlying_ticker=AAPL        │
│      - GET /v3/snapshot/options/{tickers} for pricing                    │
│      - Compute Greeks for each contract                                  │
│                                                                          │
│   b) Fallback: Black-Scholes synthetic chain                             │
│      - Generate 7 strikes around current price                           │
│      - Apply volatility smile (higher IV for OTM)                        │
│      - Compute theoretical prices + Greeks                               │
│      - Simulate realistic bid/ask spreads                                │
│                                                                          │
│ Output:  OptionChain { underlyingPrice, calls[], puts[], expirations }   │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 5: STRATEGY DECISION                                                │
├──────────────────────────────────────────────────────────────────────────┤
│ Input:   SecurityInfo + RiskSentimentOutput + RegimeOutput + OptionChain │
│                                                                          │
│ LLM:     GPT-4o selects optimal strategy using comprehensive context:    │
│                                                                          │
│   Decision Matrix:                                                       │
│   ┌──────────┬───────────┬───────────┬──────────────┐                   │
│   │ Regime   │ IV Level  │ Strategy  │ Rationale    │                   │
│   ├──────────┼───────────┼───────────┼──────────────┤                   │
│   │ Bull     │ Moderate  │ Long Call │ Momentum up  │                   │
│   │ Bear     │ Moderate  │ Long Put  │ Momentum down│                   │
│   │ Neutral  │ High      │ Strangle  │ Vol expected │                   │
│   │ Any      │ Extreme   │ No Trade  │ IV too high  │                   │
│   │ Neutral  │ Low       │ No Trade  │ No edge      │                   │
│   └──────────┴───────────┴───────────┴──────────────┘                   │
│                                                                          │
│ Output:  StrategyDecision {                                              │
│   strategy, confidence, rationale, recommendedStrike,                    │
│   recommendedExpiration, maxRisk, maxReward, breakeven,                  │
│   callContract?, putContract?, alternatives[]                            │
│ }                                                                        │
│                                                                          │
│ Fallback: Rule-based: Bull→Call, Bear→Put, Neutral+HighVol→Strangle     │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 6: EXECUTION                                                        │
├──────────────────────────────────────────────────────────────────────────┤
│ Action:                                                                  │
│   a) If NO_TRADE: Skip execution, display rationale + account status     │
│                                                                          │
│   b) Otherwise:                                                          │
│      - Build MCP tool call: place_option_order {                         │
│          symbol, strategy, strike, expiration, optionType, quantity }    │
│      - Submit to MCP Trading Server                                      │
│      - Server executes in paper account:                                 │
│        · Prices option via Black-Scholes                                 │
│        · Checks available cash                                           │
│        · Creates position, deducts cash + commission                     │
│        · Returns OrderConfirmation                                       │
│      - Display fill price, total cost, remaining cash, P&L               │
│                                                                          │
│ Output:  ExecutionResult { orderRequest, confirmation, pnlEstimate }     │
│                                                                          │
│ Fallback: If MCP call fails, return rejected order with error message.   │
└──────────────────────────────────────────────────────────────────────────┘
```

## MCP Tool Call Flow

```
LLM Agent                MCP Server                Paper Broker
    │                        │                         │
    │── get_account_status ──▶                         │
    │                        │── get_account() ──────▶ │
    │                        │◀── account state ───── │
    │◀── {cash, equity, ...}─│                         │
    │                        │                         │
    │── place_option_order ─▶                         │
    │   {symbol, strategy,  │── execute_paper_trade() ▶
    │    strike, qty}       │                         │
    │                        │    · Price option       │
    │                        │    · Check cash         │
    │                        │    · Create position    │
    │                        │    · Update account     │
    │                        │◀── confirmation ────── │
    │◀── {order_id, fill,   │                         │
    │     status, cost}                                      │
```

## Error Handling

| Stage | Error Scenario | Behavior |
|-------|---------------|----------|
| Security | Invalid symbol | Returns SecurityInfo with error reasoning, workflow continues |
| Security | yfinance down | Returns fallback SecurityInfo, isOptionable=False |
| Sentiment | CNN scrape fails | Returns neutral Fear & Greed (50), warning message |
| Sentiment | News scrape fails | Returns empty news list with system fallback message |
| Regime | yfinance down | Returns Neutral regime with low confidence |
| Options | Polygon API down | Falls back to Black-Scholes synthetic chain |
| Options | No API key set | Uses synthetic chain by default |
| Decision | LLM API error | Uses rule-based fallback decision matrix |
| Execution | MCP call fails | Returns rejected order with error message |
| Execution | Insufficient cash | Returns rejected order with cash details |

## LLM Reasoning Transparency

Every agent's `reasoning` field is displayed in the UI. The LLM explains:
- **Security Agent**: Why this is a valid symbol, company context
- **Risk/Sentiment Agent**: Fear & Greed interpretation, news impact synthesis
- **Regime Agent**: Why the regime was classified as Bull/Bear/Neutral
- **Decision Agent**: Why the specific strategy was chosen over alternatives
- **Execution Agent**: Order confirmation details and context

This provides full audit trail for every trading decision.
