"""Gradio UI rendering for the TradingAgents Portfolio Manager tab."""

from __future__ import annotations

import gradio as gr

from .manager import PortfolioManager
from .models import AgentCard, AnalysisResponse, PortfolioDecision
from ..trading._llm import PROVIDER_MODELS, get_default_model

# ── CSS Theme Variables ──────────────────────────────────────────────────

TA_BG = "var(--theme-bg, #2f3437)"
TA_CARD = "var(--theme-panel, #373c3f)"
TA_BORDER = "var(--theme-line, rgba(255,255,255,.14))"
TA_ACCENT = "var(--theme-blue, #1ca0f1)"
TA_TEXT = "var(--theme-ink, rgba(255,255,255,.92))"
TA_SECONDARY = "var(--theme-muted, rgba(255,255,255,.68))"
TA_GREEN = "#37c78a"
TA_RED = "#ff7369"
TA_AMBER = "#dfab01"
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
    """Convert hex color like '#37c78a' to '55, 199, 138'."""
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
        "Underweight": "#ff9a56",
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


def _model_choices_for(provider: str) -> list[tuple[str, str]]:
    models = PROVIDER_MODELS.get(provider, {})
    return [(desc, model_id) for model_id, desc in models.items()]


def _on_provider_change(provider: str) -> gr.Dropdown:
    provider_key = provider.lower()
    return gr.Dropdown(
        choices=_model_choices_for(provider_key),
        value=get_default_model(provider_key),
        interactive=True,
    )


def _run_analysis(
    symbol: str,
    llm_provider: str,
    llm_model: str,
    api_key: str,
) -> tuple[str, str, str]:
    """Run analysis and return decision HTML, agent cards HTML, and log HTML."""
    if not symbol or not symbol.strip():
        return (
            f"<div style='color:{TA_RED}; text-align:center; padding:20px;'>❌ Please enter a valid stock symbol.</div>",
            "",
            "",
        )

    result = _manager.analyze(
        symbol.strip().upper(),
        llm_provider=llm_provider.lower(),
        llm_model=llm_model,
        api_key=api_key.strip() or None,
    )

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
    with gr.Column(elem_id="ta-shell", elem_classes=["app-floating-window"]):
        gr.Markdown(f"""
        <div class="app-window-header">
            <div>
                <h1>TradingAgents Portfolio Manager</h1>
                <p>Multi-agent trading analysis powered by <b>LangGraph</b></p>
            </div>
            <span class="app-window-badge">Configurable</span>
        </div>""")

        with gr.Row():
            with gr.Column(scale=1, min_width=340):
                # ── LLM model note ────────────────────────────────────
                gr.Markdown(f"""
                <div style="background:{TA_CARD}; border:1px solid {TA_BORDER}; border-radius:10px; padding:16px; margin-bottom:16px;">
                    <div style="color:{TA_GREEN}; font-weight:700; margin-bottom:6px;">🧠 LLM Configuration</div>
                    <div style="color:{TA_SECONDARY}; font-size:0.9em; line-height:1.5;">
                    Choose a provider/model and optionally enter a session API key.<br>
                    If no key is provided, the manager falls back to local environment variables.
                    </div>
                </div>""")
                provider_input = gr.Dropdown(
                    label="Provider",
                    choices=[("OpenAI", "openai"), ("Anthropic", "anthropic"), ("NVIDIA", "nvidia")],
                    value="openai",
                    interactive=True,
                )
                model_input = gr.Dropdown(
                    label="Model",
                    choices=_model_choices_for("openai"),
                    value=get_default_model("openai"),
                    interactive=True,
                )
                api_key_input = gr.Textbox(
                    label="API Key (Optional)",
                    type="password",
                    placeholder="Provider key for this session only (never stored)",
                )

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
                # Decision highlight
                decision_output = gr.HTML(f"""
                <div style="text-align:center; padding:40px 20px; color:{TA_SECONDARY};">
                    <div style="font-size:2em; margin-bottom:12px;">🤖</div>
                    <div style="font-size:1.1em; font-weight:600; color:{TA_TEXT};">Ready to Analyze</div>
                    <div style="margin-top:4px;">Enter a symbol and click <b>Run Analysis</b> to orchestrate all 6 agents</div>
                </div>""")

                # Agent cards
                cards_output = gr.HTML("")

        # Wire up
        run_btn.click(
            fn=_run_analysis,
            inputs=[symbol_input, provider_input, model_input, api_key_input],
            outputs=[decision_output, cards_output, log_output],
        )
        provider_input.change(
            fn=_on_provider_change,
            inputs=[provider_input],
            outputs=[model_input],
        )


# ── CSS ──────────────────────────────────────────────────────────────────

TRADING_AGENTS_CSS = """
/* ===== Portfolio Manager tab styles ===== */
#ta-shell {
    max-width: 1380px;
    margin: 18px auto 34px;
    padding: 20px;
    background: var(--theme-panel, #fff);
    border: 1px solid var(--theme-line, #d9e2ec);
    border-radius: 18px;
    box-shadow: 0 24px 70px var(--theme-shadow, rgba(16,24,40,.08));
}
.ta-card {
    background: var(--theme-panel, #373c3f);
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
    box-shadow: 0 16px 40px var(--theme-shadow, rgba(16,24,40,.08));
    transition: all 0.2s;
}
.ta-card:hover {
    border-color: var(--theme-blue, #1ca0f1) !important;
    transform: translateX(4px);
}
"""
