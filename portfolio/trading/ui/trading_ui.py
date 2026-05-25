"""Gradio UI for the Multi-Agent Trading Application.

Displays the full trading workflow with per-agent reasoning panels.
Each section shows WHY each decision was made with transparency into
the agent's thought process.
"""

from __future__ import annotations

import gradio as gr

from ..graph.trading_graph import run_trading_workflow
from ..models import (
    ExecutionResult,
    MarketRegime,
    OptionStrategy,
    RegimeOutput,
    RiskSentimentOutput,
    SecurityInfo,
    StrategyDecision,
)


# ════════════════════════════════════════════════════════════════════════
# Color theme — uses CSS variables with dark fallbacks for standalone tabs
# ════════════════════════════════════════════════════════════════════════

BG = "var(--trading-bg, #0a0e17)"
CARD = "var(--trading-card, #141b26)"
BORDER = "var(--trading-border, #1e2d40)"
ACCENT = "var(--trading-accent, #4da6ff)"
GREEN = "var(--trading-green, #00c853)"
RED = "var(--trading-red, #ff3d3d)"
AMBER = "var(--trading-amber, #ffab00)"
PURPLE = "var(--trading-purple, #b388ff)"
TEAL = "var(--trading-teal, #00bfa5)"
TEXT = "var(--trading-text, #e8edf2)"
SECONDARY = "var(--trading-secondary, #8b95a5)"
ORANGE = "var(--trading-orange, #ff6d3d)"
GREEN_BRIGHT = "var(--trading-green-bright, #00e676)"


def _render_agent_card(
    icon: str,
    title: str,
    content: str,
    accent_color: str,
    status: str = "complete",
) -> str:
    """Render a single agent output card with reasoning."""
    status_icon = {"complete": "✅", "running": "⏳", "error": "❌", "skipped": "⏭️"}.get(status, "")
    return f"""
    <div class="trading-card" style="
        border-left:4px solid {accent_color};
    ">
        <div style="display:flex; align-items:center; margin-bottom:12px;">
            <span style="font-size:1.4em; margin-right:10px;">{icon}</span>
            <div>
                <div style="font-weight:700; color:{TEXT}; font-size:1.05em;">{title}</div>
                <div style="font-size:0.8em; color:{accent_color};">{status_icon} {status.title()}</div>
            </div>
        </div>
        <div style="color:{SECONDARY}; font-size:0.92em; line-height:1.6; white-space:pre-wrap;">{content}</div>
    </div>"""


def _render_security_card(security: SecurityInfo) -> str:
    """Render the Security Agent output."""
    content = ""
    if security.company_name:
        content += f"🏢 <b>Company:</b> {security.company_name}\n"
    if security.sector and security.industry:
        content += f"📊 <b>Sector/Industry:</b> {security.sector} / {security.industry}\n"
    if security.market_cap:
        cap = security.market_cap
        if cap >= 1e12:
            tier = f"Mega Cap (${cap/1e12:.1f}T)"
        elif cap >= 200e9:
            tier = f"Large Cap (${cap/1e9:.0f}B)"
        elif cap >= 10e9:
            tier = f"Mid Cap (${cap/1e9:.0f}B)"
        else:
            tier = f"Small/Micro Cap (${cap/1e6:.0f}M)"
        content += f"💰 <b>Market Cap:</b> {tier}\n"
    if security.current_price:
        content += f"💵 <b>Current Price:</b> ${security.current_price:.2f}\n"
    if security.exchange:
        content += f"🏛️ <b>Exchange:</b> {security.exchange}\n"
    content += f"\n{'✅ Options Available' if security.is_optionable else '❌ No Options Available'}\n\n"
    content += f"<i>🧠 Reasoning:</i>\n{security.reasoning}"
    return _render_agent_card("🔍", "Security Agent — Identification", content, ACCENT)


def _render_sentiment_card(sentiment: RiskSentimentOutput) -> str:
    """Render the Risk/Sentiment Agent output."""
    fg = sentiment.fear_greed
    zone_colors = {
        "Extreme Fear": RED,
        "Fear": ORANGE,
        "Neutral": AMBER,
        "Greed": GREEN,
        "Extreme Greed": GREEN_BRIGHT,
    }
    zone_color = zone_colors.get(fg.zone.value, AMBER)

    content = "📊 <b>CNN Fear & Greed Index</b>\n"
    content += f'  Value: <b style="color:{zone_color}">{fg.value}/100 — {fg.zone.value}</b>\n'
    if fg.previous_close:
        content += f"  Previous Close: {fg.previous_close}\n"
    if fg.one_week_ago:
        content += f"  1 Week Ago: {fg.one_week_ago}\n"
    content += f"\n📈 <b>Market Trend:</b>\n{sentiment.market_trend}\n"
    content += f"\n⚠️ <b>Risk Assessment:</b> {sentiment.risk_assessment}\n"

    if sentiment.top_news:
        content += "\n📰 <b>Key News Headlines:</b>\n"
        for n in sentiment.top_news[:5]:
            impact_icon = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪"}.get(n.impact, "⚪")
            content += f"  {impact_icon} [{n.source}] {n.headline[:120]}\n"

    content += f"\n<i>🧠 Full Analysis:</i>\n{sentiment.reasoning[:400]}..."
    return _render_agent_card("🌐", "Risk & Sentiment Agent — Fear & Greed + News", content, TEAL)


def _render_regime_card(regime: RegimeOutput) -> str:
    """Render the Regime Detection Agent output."""
    regime_colors = {
        "Bull Market": GREEN,
        "Bear Market": RED,
        "Neutral / Range-bound": AMBER,
    }
    reg_color = regime_colors.get(regime.regime.value, AMBER)
    confidence_bar = "█" * int(regime.confidence * 10) + "░" * (10 - int(regime.confidence * 10))

    content = f'🎯 <b style="color:{reg_color}; font-size:1.2em;">{regime.regime.value}</b>\n'
    content += f"Confidence: {confidence_bar} {regime.confidence:.0%}\n\n"

    if regime.volatility_index is not None:
        content += f"📉 Volatility: {regime.volatility_index:.1%} (annualized)\n"
    if regime.trend_strength is not None:
        content += f"📈 Trend Strength: {regime.trend_strength:.1%}\n"
    content += f"📊 S&P 500 Trend: {regime.sp500_trend}\n"

    if regime.indicators:
        content += "\n<b>Technical Indicators:</b>\n"
        for k, v in regime.indicators.items():
            content += f"  • {k}: {v}\n"

    content += f"\n<i>🧠 Reasoning:</i>\n{regime.reasoning[:500]}"
    return _render_agent_card("🔄", "Regime Detection Agent — Market Classification", content, reg_color)


def _render_decision_card(decision: StrategyDecision, symbol: str) -> str:
    """Render the Decision Agent output."""
    strategy_colors = {
        "Long Call": GREEN,
        "Long Put": RED,
        "Long Strangle": PURPLE,
        "No Trade": AMBER,
    }
    color = strategy_colors.get(decision.strategy.value, AMBER)

    content = f'🎯 <b style="color:{color}; font-size:1.3em;">{decision.strategy.value}</b>\n'
    content += f"Confidence: {decision.confidence:.0%}\n\n"

    if decision.strategy != OptionStrategy.NO_TRADE:
        if decision.recommended_strike:
            content += f"💵 <b>Strike:</b> ${decision.recommended_strike:.2f}\n"
        if decision.recommended_expiration:
            content += f"📅 <b>Expiration:</b> {decision.recommended_expiration}\n"
        if decision.max_risk is not None:
            content += f"⚠️ <b>Max Risk:</b> ${decision.max_risk:.2f}\n"
        if decision.max_reward is not None:
            reward_str = "Unlimited" if decision.max_reward == float("inf") else f"${decision.max_reward:.2f}"
            content += f"🚀 <b>Max Reward:</b> {reward_str}\n"
        if decision.breakeven:
            content += f"🎯 <b>Breakeven:</b> {decision.breakeven}\n"

        if decision.call_contract:
            content += f"\n<b>Call Contract:</b> {decision.call_contract.symbol} "
            content += f"(Bid/Ask: ${decision.call_contract.bid:.2f}/${decision.call_contract.ask:.2f}, "
            content += f"IV: {decision.call_contract.implied_volatility:.1%}, Δ: {decision.call_contract.delta:.2f})\n"
        if decision.put_contract:
            content += f"\n<b>Put Contract:</b> {decision.put_contract.symbol} "
            content += f"(Bid/Ask: ${decision.put_contract.bid:.2f}/${decision.put_contract.ask:.2f}, "
            content += f"IV: {decision.put_contract.implied_volatility:.1%}, Δ: {decision.put_contract.delta:.2f})\n"

    if decision.alternatives:
        content += "\n<b>Alternatives Considered:</b>\n"
        for alt in decision.alternatives:
            content += f"  • {alt}\n"

    content += f"\n<i>🧠 Rationale:</i>\n{decision.rationale}"
    return _render_agent_card("🎯", f"Decision Agent — Strategy for {symbol}", content, color)


def _render_execution_card(execution: ExecutionResult, symbol: str) -> str:
    """Render the Execution Agent output."""
    confirmation: dict = execution.confirmation
    strategy = execution.request.strategy

    if strategy == OptionStrategy.NO_TRADE:
        content = "🚫 <b>No Trade Executed</b>\n\n"
        content += "The Decision Agent recommended no trade under current conditions.\n"
        if "cash" in confirmation:
            content += f"\n💰 Paper Account: ${confirmation.get('cash', 'N/A'):,.2f} cash\n"
            content += f"📊 Total Equity: ${confirmation.get('total_equity', 'N/A'):,.2f}\n"
            content += f"📈 P&L: ${confirmation.get('total_pnl', 'N/A'):,.2f}\n"
        return _render_agent_card("⏸️", f"Execution Agent — {symbol}", content, AMBER, status="skipped")

    status = confirmation.get("status", "Unknown")
    status_color = GREEN if "Filled" in str(status) else RED if "Rejected" in str(status) else AMBER

    content = f'📋 <b>Order:</b> {execution.request.order_id}\n'
    content += f'📊 <b>Strategy:</b> {strategy.value}\n'
    content += f'🎯 <b>Status:</b> <span style="color:{status_color}">{status}</span>\n'
    content += f'📅 <b>Timestamp:</b> {confirmation.get("timestamp", "N/A")}\n\n'

    fp = confirmation.get("filled_price")
    tc = confirmation.get("total_cost")

    if fp:
        content += f"💵 <b>Fill Price:</b> ${fp:.2f}/contract\n"
    content += f"📦 <b>Quantity:</b> {confirmation.get('filled_quantity', 1)} contract(s)\n"
    if tc:
        content += f"💰 <b>Total Cost:</b> ${tc:,.2f}\n"

    notes = confirmation.get("notes", "")
    if notes:
        content += f"\n📝 <b>Notes:</b> {notes}\n"
    if execution.pnl_estimate is not None:
        content += f"📈 <b>Account P&L:</b> ${execution.pnl_estimate:,.2f}\n"

    return _render_agent_card("💸", f"Execution Agent — Order Confirmation", content, status_color, status="complete" if "Filled" in str(status) else "error")


def _run_workflow(symbol: str) -> tuple[str, str, str, str, str, str, str]:
    """Run the full trading workflow and return all agent cards."""
    if not symbol or not symbol.strip():
        return (
            _render_agent_card("🔍", "Security Agent", "Please enter a stock symbol.",
                               ACCENT, "error"),
            "", "", "", "", "",
            f"<div style='color:{RED}; text-align:center;'>❌ Please enter a valid stock symbol.</div>",
        )

    try:
        state = run_trading_workflow(symbol)
    except Exception as e:
        error_card = _render_agent_card("❌", "Error", f"Workflow failed: {str(e)}", RED, "error")
        return (error_card, "", "", "", "", "",
                f"<div style='color:{RED}; text-align:center;'>❌ Error: {str(e)}</div>")

    # Render each agent's output
    security_html = _render_security_card(state.get("security")) if state.get("security") else _render_agent_card(
        "🔍", "Security Agent", "No security data available.", ACCENT, "error")

    sentiment_html = _render_sentiment_card(state.get("sentiment")) if state.get("sentiment") else ""
    regime_html = _render_regime_card(state.get("regime")) if state.get("regime") else ""
    decision_html = _render_decision_card(state.get("strategy"), symbol) if state.get("strategy") else ""
    execution_html = _render_execution_card(state.get("execution"), symbol) if state.get("execution") else ""

    # Build the execution log
    log = state.get("log", [])
    log_html = f"<div style='color:{SECONDARY}; font-size:0.85em; line-height:1.8;'><b>📋 Execution Log:</b><br>"
    for entry in log:
        log_html += f"  {entry}<br>"
    log_html += "</div>"

    # Summary at top
    stage = state.get("stage", "unknown")
    summary = f"<div style='color:{ACCENT}; text-align:center; font-size:1.1em;'>✅ Workflow complete — Stage: {stage}</div>"

    return (security_html, sentiment_html, regime_html, decision_html, execution_html, log_html, summary)


def render_trading_tab() -> None:
    """Build the Trading tab in the Gradio app."""
    gr.Markdown(f"""
    <h1 style="text-align:center; margin-bottom:4px; color:{TEXT};">🤖 Multi-Agent Options Trading</h1>
    <p style="text-align:center; color:{SECONDARY}; margin-bottom:12px;">
    5 specialized AI agents orchestrated by <b>LangGraph</b> — from symbol to execution
    </p>""")

    with gr.Row():
        with gr.Column(scale=1, min_width=340):
            gr.Markdown("### 🎯 Trading Target")
            symbol_input = gr.Textbox(
                label="Stock Symbol",
                placeholder="e.g., AAPL, MSFT, NVDA, TSLA, SPY",
                value="AAPL",
                info="Enter any US stock symbol with options",
            )
            run_btn = gr.Button("🚀 Run Multi-Agent Analysis", variant="primary", size="lg")

            # Flow diagram
            gr.Markdown(f"""
            <div style="background:{CARD}; border:1px solid {BORDER}; border-radius:10px; padding:16px; margin-top:20px; text-align:center;">
                <div style="color:{TEXT}; font-weight:700; margin-bottom:12px;">📊 Agent Flow</div>
                <div style="display:flex; flex-direction:column; gap:6px; font-size:0.85em; color:{SECONDARY};">
                    <span>🔍 1. Security Agent → Identify</span>
                    <span style="color:{TEAL};">🌐 2. Risk/Sentiment → Fear & Greed</span>
                    <span style="color:{AMBER};">🔄 3. Regime → Bull/Bear/Neutral</span>
                    <span>📊 4. Options Chain → Contracts</span>
                    <span style="color:{PURPLE};">🎯 5. Decision → Strategy</span>
                    <span style="color:{GREEN};">💸 6. Execution → MCP Trade</span>
                </div>
            </div>""")

            # Log output
            log_output = gr.HTML("", elem_id="trading-log")

        with gr.Column(scale=2, min_width=500):
            status_output = gr.HTML(f"""
            <div style="text-align:center; padding:20px; color:{SECONDARY};">
                <div style="font-size:2em; margin-bottom:12px;">🤖</div>
                <div style="font-size:1.1em; font-weight:600; color:{TEXT};">Ready to Trade</div>
                <div style="margin-top:4px;">Enter a symbol and click <b>Run Analysis</b> to orchestrate all 5 agents</div>
            </div>""")

            # Per-agent output panels
            with gr.Tabs():
                with gr.TabItem("🔍 Security"):
                    security_output = gr.HTML("")
                with gr.TabItem("🌐 Sentiment"):
                    sentiment_output = gr.HTML("")
                with gr.TabItem("🔄 Regime"):
                    regime_output = gr.HTML("")
                with gr.TabItem("🎯 Decision"):
                    decision_output = gr.HTML("")
                with gr.TabItem("💸 Execution"):
                    execution_output = gr.HTML("")

    # Wire up the workflow
    run_btn.click(
        fn=_run_workflow,
        inputs=[symbol_input],
        outputs=[
            security_output,
            sentiment_output,
            regime_output,
            decision_output,
            execution_output,
            log_output,
            status_output,
        ],
    )


TRADING_CSS = """
/* ===== Trading tab styles ===== */
.trading-card {
    background: var(--trading-card, #141b26);
    border: 1px solid var(--trading-border, #1e2d40);
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 14px;
    transition: all 0.2s;
}
.trading-card:hover {
    border-color: var(--trading-accent, #4da6ff) !important;
    transform: translateX(4px);
}
#trading-log {
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
}
"""
