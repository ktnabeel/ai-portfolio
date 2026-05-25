"""Gradio UI rendering for the Financial Agent tab."""

import gradio as gr

from .orchestrator import DecisionOrchestrator
from .models import PortfolioHolding

DARK_CSS = """
#financial-tab {
    background: var(--theme-bg, #0d1117);
    color: var(--theme-ink, #c9d1d9);
    font-family: 'Segoe UI', system-ui, sans-serif;
}
#financial-tab h1, #financial-tab h2, #financial-tab h3 {
    color: var(--theme-blue, #58a6ff);
}
.result-buy {
    color: #3fb950;
    font-weight: bold;
    font-size: 1.2em;
}
.result-sell {
    color: #f85149;
    font-weight: bold;
    font-size: 1.2em;
}
.result-hold {
    color: #d2991d;
    font-weight: bold;
    font-size: 1.2em;
}
.metric-card {
    background: var(--theme-panel, #161b22);
    border: 1px solid var(--theme-line, #30363d);
    border-radius: 8px;
    padding: 12px;
    margin: 6px 0;
}
"""


def _analyze_single(ticker: str) -> str:
    """Run analysis on a single ticker and return HTML result."""
    if not ticker or not ticker.strip():
        return "<p style='color:#f85149'>Please enter a stock ticker.</p>"

    orch = DecisionOrchestrator()
    result = orch.analyze_stock(ticker)

    action_color = {"Buy": "result-buy", "Sell": "result-sell", "Hold": "result-hold"}
    color_cls = action_color.get(result.action.value, "result-hold")

    signal_rows = ""
    for s in result.signals:
        icon = {"Bullish": "\U0001f7e2", "Bearish": "\U0001f534", "Neutral": "\u26aa"}
        signal_rows += (
            f"<div class='metric-card'>"
            f"<strong>{icon.get(s.signal.value, '')} {s.agent_name}</strong>: "
            f"{s.signal.value} ({s.confidence:.0%})<br>"
            f"<small>{s.summary}</small></div>"
        )

    html = f"""
    <div id='financial-tab' style='padding:10px'>
        <h2>{result.ticker} Analysis</h2>
        <div class='metric-card'>
            <span class='{color_cls}'>{result.action.value}</span>
            &nbsp;| Confidence: {result.confidence:.0%}
            &nbsp;| Risk: {result.risk_level.value}
            &nbsp;| Price: ${result.current_price:.2f}
        </div>
        <h3>Agent Signals</h3>
        {signal_rows}
    </div>
    """
    return html


def _analyze_portfolio(holdings_text: str) -> str:
    """Parse holdings text and run portfolio analysis, return HTML."""
    if not holdings_text or not holdings_text.strip():
        return "<p style='color:#f85149'>Please enter portfolio holdings.</p>"

    holdings = []
    for line in holdings_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 1:
            ticker = parts[0].upper()
            shares = float(parts[1]) if len(parts) >= 2 else 1.0
            avg_price = float(parts[2]) if len(parts) >= 3 else None
            holdings.append(PortfolioHolding(ticker=ticker, shares=shares, avg_price=avg_price))

    if not holdings:
        return "<p style='color:#f85149'>No valid holdings found.</p>"

    orch = DecisionOrchestrator()
    result = orch.analyze_portfolio(holdings)

    decision_rows = ""
    for d in result.decisions:
        action_color = {"Buy": "result-buy", "Sell": "result-sell", "Hold": "result-hold"}
        color_cls = action_color.get(d.action.value, "result-hold")
        decision_rows += (
            f"<div class='metric-card'>"
            f"<strong>{d.ticker}</strong>: "
            f"<span class='{color_cls}'>{d.action.value}</span>"
            f" ({d.confidence:.0%}) | Risk: {d.risk_level.value}"
            f" | ${d.current_price:.2f}</div>"
        )

    risk_color = {"Low": "result-buy", "Moderate": "result-hold", "High": "result-sell", "Critical": "result-sell"}
    risk_cls = risk_color.get(result.portfolio_risk.value, "result-hold")

    html = f"""
    <div id='financial-tab' style='padding:10px'>
        <h2>Portfolio Analysis</h2>
        <div class='metric-card'>
            <strong>{result.summary}</strong><br>
            <span class='{risk_cls}'>Portfolio Risk: {result.portfolio_risk.value}</span>
        </div>
        <h3>Per-Stock Decisions</h3>
        {decision_rows}
    </div>
    """
    return html


def render_financial_tab() -> gr.Blocks:
    """Build and return the Financial Agent Gradio tab."""
    with gr.Blocks(elem_id="financial-tab") as tab:
        gr.Markdown("""
        # \U0001f4c8 Multi-Agent Financial Analysis
        Analyze stocks using 5 specialized AI agents: Market Data, Technical Analysis,
        Fundamental Analysis, Sentiment Analysis, and Risk Assessment.
        """)

        with gr.Tabs():
            with gr.TabItem("\U0001f4ca Single Stock"):
                ticker_input = gr.Textbox(
                    label="Stock Ticker",
                    placeholder="e.g. AAPL, TSLA, MSFT",
                    value="AAPL",
                )
                analyze_btn = gr.Button("\U0001f50d Analyze", variant="primary")
                single_output = gr.HTML()
                analyze_btn.click(
                    fn=_analyze_single,
                    inputs=[ticker_input],
                    outputs=[single_output],
                )

            with gr.TabItem("\U0001f4cb Portfolio Risk"):
                gr.Markdown("""
                Enter one holding per line: `TICKER SHARES AVG_PRICE`<br>
                Example: `AAPL 10 180.50`
                """)
                holdings_input = gr.Textbox(
                    label="Portfolio Holdings",
                    placeholder="AAPL 10 180.50\nMSFT 5 420.00\nTSLA 3 250.00",
                    lines=6,
                )
                portfolio_btn = gr.Button("\U0001f4ca Analyze Portfolio", variant="primary")
                portfolio_output = gr.HTML()
                portfolio_btn.click(
                    fn=_analyze_portfolio,
                    inputs=[holdings_input],
                    outputs=[portfolio_output],
                )

    return tab
