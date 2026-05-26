"""Gradio UI rendering for the TradingAgents Portfolio Manager tab."""

from __future__ import annotations

import gradio as gr

from .manager import PortfolioManager
from .models import AgentCard, AnalysisResponse, PortfolioDecision

# ── CSS Theme Variables ──────────────────────────────────────────────────

TA_BG = "var(--theme-bg, #0d1117)"
TA_CARD = "var(--theme-panel, #161b22)"
TA_BORDER = "var(--theme-line, #30363d)"
TA_ACCENT = "var(--theme-blue, #58a6ff)"
TA_TEXT = "var(--theme-ink, #c9d1d9)"
TA_SECONDARY = "var(--theme-muted, #b0b8c1)"
TA_GREEN = "#3fb950"
TA_RED = "#f85149"
TA_AMBER = "#d2991d"
TA_PURPLE = "#b388ff"
TA_TEAL = "#00bfa5"

# ── Card Renderer ────────────────────────────────────────────────────────


def _render_agent_card(card: AgentCard) -> str:
    """Render a single agent output card."""
    status_icon = {
        "complete": "✅",
        "running": "⏳",
        "error": "❌",
        "skipped": "⏭️",
    }.get(card.status, "")

    return f"""
    <div class="ta-card" style="border-left:4px solid {card.accent_color};">
        <div style="display:flex; align-items:center; margin-bottom:12px;">
            <span style="font-size:1.4em; margin-right:10px;">{card.icon}</span>
            <div>
                <div style="font-weight:700; color:{TA_TEXT}; font-size:1.05em;">{card.agent_name}</div>
                <div style="font-size:0.8em; color:{card.accent_color};">{status_icon} {card.status.title()}</div>
            </div>
        </div>
        <div style="color:{TA_SECONDARY}; font-size:0.92em; line-height:1.6;">{card.content}</div>
        <div style="color:{TA_SECONDARY}; font-size:0.82em; line-height:1.5; margin-top:10px; padding-top:10px; border-top:1px solid {TA_BORDER};">
            <i>🧠 Reasoning:</i> {card.reasoning[:400]}{'...' if len(card.reasoning) > 400 else ''}
        </div>
    </div>"""


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color like '#3fb950' to '63, 185, 80'."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r}, {g}, {b}"


def _render_decision(decision: PortfolioDecision) -> str:
    """Render the final portfolio decision highlight."""
    rating_colors = {
        "Buy": TA_GREEN,
        "Overweight": TA_TEAL,
        "Hold": TA_AMBER,
        "Underweight": "#f0883e",
        "Sell": TA_RED,
    }
    color = rating_colors.get(decision.rating.value, TA_AMBER)

    confidence_bar = "█" * max(1, int(decision.confidence * 10)) + "░" * max(0, 10 - int(decision.confidence * 10))

    rgb = _hex_to_rgb(color)
    return f"""
    <div class="ta-card" style="border-left:4px solid {color}; background: linear-gradient(135deg, {TA_CARD}, rgba({rgb}, 0.08));">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="font-size:2em;">📊</span>
                <div>
                    <div style="font-weight:700; color:{TA_TEXT}; font-size:1.2em;">Portfolio Decision</div>
                    <div style="font-size:0.85em; color:{TA_SECONDARY};">{decision.symbol} — {decision.rating.value}</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:2em; font-weight:900; color:{color};">{decision.rating.value.upper()}</div>
                <div style="font-size:0.78em; color:{TA_SECONDARY};">Confidence: {confidence_bar} {decision.confidence:.0%}</div>
            </div>
        </div>
        <div style="background:{TA_CARD}; border-radius:8px; padding:14px; margin-top:8px;">
            <div style="color:{TA_TEXT}; font-weight:700; margin-bottom:8px;">📝 Summary</div>
            <div style="color:{TA_SECONDARY}; font-size:0.9em; line-height:1.6;">{decision.summary}</div>
        </div>
        <div style="color:{TA_SECONDARY}; font-size:0.82em; line-height:1.6; margin-top:10px;">
            <i>🧠 Rationale:</i><br>{decision.rationale[:600]}{'...' if len(decision.rationale) > 600 else ''}
        </div>
        <div style="color:{TA_SECONDARY}; font-size:0.8em; margin-top:8px; padding-top:8px; border-top:1px solid {TA_BORDER};">
            ⚠️ Risk: {decision.risk_assessment[:300]}
        </div>
    </div>"""


# ── Singleton Manager ─────────────────────────────────────────────────

_manager = PortfolioManager()


def _run_analysis(symbol: str) -> tuple[str, str, str]:
    """Run analysis and return decision HTML, agent cards HTML, and log HTML."""
    if not symbol or not symbol.strip():
        return (
            f"<div style='color:{TA_RED}; text-align:center; padding:20px;'>❌ Please enter a valid stock symbol.</div>",
            "",
            "",
        )

    result = _manager.analyze(symbol.strip().upper())

    # Decision
    decision_html = _render_decision(result.decision) if result.decision else (
        f"<div style='color:{TA_SECONDARY}; text-align:center; padding:20px;'>No decision available.</div>"
    )

    # Agent cards
    cards_html = "\n".join(_render_agent_card(card) for card in result.agent_cards)

    # Execution log
    log_lines = "\n".join(
        f"<div style='padding:4px 0; border-bottom:1px solid {TA_BORDER}; font-size:0.82em;'>{entry}</div>"
        for entry in result.execution_log
    )
    log_html = f"""
    <div style='color:{TA_SECONDARY}; font-family:monospace; max-height:280px; overflow-y:auto;'>
        <div style='font-weight:700; color:{TA_TEXT}; margin-bottom:8px;'>📋 Execution Log</div>
        {log_lines}
    </div>"""

    return decision_html, cards_html, log_html


# ── Tab Builder ──────────────────────────────────────────────────────────


def render_trading_agents_tab() -> None:
    """Build the TradingAgents Portfolio Manager Gradio tab."""
    gr.Markdown(f"""
    <h1 style="text-align:center; margin-bottom:4px; color:{TA_TEXT};">🤖 TradingAgents Portfolio Manager</h1>
    <p style="text-align:center; color:{TA_SECONDARY}; margin-bottom:12px;">
    Multi-agent trading analysis powered by <b>LangGraph</b> — Security → Sentiment → Regime → Decision → Execution
    </p>""")

    with gr.Row():
        with gr.Column(scale=1, min_width=340):
            gr.Markdown("### 🎯 Analysis Target")
            symbol_input = gr.Textbox(
                label="Stock Symbol",
                placeholder="e.g., AAPL, MSFT, NVDA, TSLA",
                value="AAPL",
                info="Enter any US stock symbol for multi-agent analysis",
            )
            run_btn = gr.Button("🚀 Run Multi-Agent Analysis", variant="primary", size="lg")

            # Agent flow diagram
            gr.Markdown(f"""
            <div style="background:{TA_CARD}; border:1px solid {TA_BORDER}; border-radius:10px; padding:16px; margin-top:20px; text-align:center;">
                <div style="color:{TA_TEXT}; font-weight:700; margin-bottom:12px;">📊 Agent Pipeline</div>
                <div style="display:flex; flex-direction:column; gap:6px; font-size:0.85em; color:{TA_SECONDARY};">
                    <span style="color:{TA_ACCENT};">🔍 1. Security Agent → Identify</span>
                    <span style="color:{TA_TEAL};">🌐 2. Risk/Sentiment → Fear & Greed</span>
                    <span style="color:{TA_AMBER};">🔄 3. Regime → Bull/Bear/Neutral</span>
                    <span style="color:{TA_PURPLE};">🎯 4. Decision → Strategy Selection</span>
                    <span style="color:{TA_GREEN};">💸 5. Execution → Paper Trade</span>
                    <span style="color:{TA_ACCENT};">📊 6. Portfolio Manager → Final Rating</span>
                </div>
            </div>""")

            # Execution log
            log_output = gr.HTML("")

        with gr.Column(scale=2, min_width=500):
            # Decision highlight at top
            decision_output = gr.HTML(f"""
            <div style="text-align:center; padding:40px 20px; color:{TA_SECONDARY};">
                <div style="font-size:3em; margin-bottom:16px;">🤖</div>
                <div style="font-size:1.2em; font-weight:600; color:{TA_TEXT};">TradingAgents Portfolio Manager</div>
                <div style="margin-top:8px;">Enter a symbol and click <b>Run Analysis</b> to orchestrate all 6 agents</div>
                <div style="margin-top:16px; font-size:0.82em; color:{TA_SECONDARY};">
                    FastAPI backend available at <code style="color:{TA_ACCENT};">/docs</code> for programmatic access
                </div>
            </div>""")

            # Agent cards
            cards_output = gr.HTML("")

    # Wire up
    run_btn.click(
        fn=_run_analysis,
        inputs=[symbol_input],
        outputs=[decision_output, cards_output, log_output],
    )


# ── CSS ──────────────────────────────────────────────────────────────────

TRADING_AGENTS_CSS = """
/* ===== TradingAgents Manager tab styles ===== */
.ta-card {
    background: var(--theme-panel, #161b22);
    border: 1px solid var(--theme-line, #30363d);
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 14px;
    transition: all 0.2s;
}
.ta-card:hover {
    border-color: var(--theme-blue, #58a6ff) !important;
    transform: translateX(4px);
}
"""
