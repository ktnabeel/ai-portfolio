"""Gradio UI for the Multi-Agent Trading Application.

Full-featured trading desk with:
- Workflow-step layout: Configure → Analyze → Review → Account
- Deterministic mode when no API key is provided (rule-based agents)
- MCP paper-trading connectivity display
- Provider/model selection (OpenAI / Anthropic)
- Human-in-the-loop approval before trade execution
- LangGraph-style flow diagram showing agent decisions
- Simulated account positions, balances, and P&L
- Toggle to show/hide execution traces
"""

from __future__ import annotations

import json
import os
from typing import Any

import gradio as gr

from .._llm import PROVIDER_MODELS, get_default_model
from ..agents.execution_agent import ExecutionAgent
from ..graph.trading_graph import run_trading_workflow
from ..mcp.broker import close_position, get_account, record_rejection, reset_account
from ..models import (
    ExecutionResult,
    OptionStrategy,
    OrderRequest,
    StrategyDecision,
)


# ════════════════════════════════════════════════════════════════════════
# Color theme
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

_PROVIDER_CHOICES: list[str] = sorted(PROVIDER_MODELS.keys())


def _model_choices_for(provider: str) -> list[tuple[str, str]]:
    models = PROVIDER_MODELS.get(provider, {})
    return [(desc, model_id) for model_id, desc in models.items()]


# ════════════════════════════════════════════════════════════════════════
# Agent card renderers (unchanged — same rich output per agent)
# ════════════════════════════════════════════════════════════════════════

def _render_agent_card(
    icon: str, title: str, content: str, accent_color: str,
    status: str = "complete",
) -> str:
    status_icon = {"complete": "✅", "running": "⏳", "error": "❌", "skipped": "⏭️",
                   "pending_review": "⏸️"}.get(status, "")
    return f"""
    <div class="trading-card" style="border-left:4px solid {accent_color};">
        <div style="display:flex; align-items:center; margin-bottom:12px;">
            <span style="font-size:1.4em; margin-right:10px;">{icon}</span>
            <div>
                <div style="font-weight:700; color:{TEXT}; font-size:1.05em;">{title}</div>
                <div style="font-size:0.8em; color:{accent_color};">{status_icon} {status.replace('_', ' ').title()}</div>
            </div>
        </div>
        <div style="color:{SECONDARY}; font-size:0.92em; line-height:1.6; white-space:pre-wrap;">{content}</div>
    </div>"""


def _render_security_card(security) -> str:
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


def _render_sentiment_card(sentiment) -> str:
    fg = sentiment.fear_greed
    zone_colors = {
        "Extreme Fear": RED, "Fear": ORANGE, "Neutral": AMBER,
        "Greed": GREEN, "Extreme Greed": GREEN_BRIGHT,
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
    return _render_agent_card("🌐", "Risk & Sentiment Agent", content, TEAL)


def _render_regime_card(regime) -> str:
    regime_colors = {
        "Bull Market": GREEN, "Bear Market": RED, "Neutral / Range-bound": AMBER,
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
    return _render_agent_card("🔄", "Regime Detection Agent", content, reg_color)


def _render_decision_card(decision: StrategyDecision, symbol: str) -> str:
    strategy_colors = {
        "Long Call": GREEN, "Long Put": RED, "Long Strangle": PURPLE, "No Trade": AMBER,
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
            c = decision.call_contract
            content += f"\n<b>Call Contract:</b> {c.symbol} "
            content += f"(Bid/Ask: ${c.bid:.2f}/${c.ask:.2f}, "
            content += f"IV: {c.implied_volatility:.1%}, Δ: {c.delta:.2f})\n"
        if decision.put_contract:
            p = decision.put_contract
            content += f"\n<b>Put Contract:</b> {p.symbol} "
            content += f"(Bid/Ask: ${p.bid:.2f}/${p.ask:.2f}, "
            content += f"IV: {p.implied_volatility:.1%}, Δ: {p.delta:.2f})\n"
    if decision.alternatives:
        content += "\n<b>Alternatives Considered:</b>\n"
        for alt in decision.alternatives:
            content += f"  • {alt}\n"
    content += f"\n<i>🧠 Rationale:</i>\n{decision.rationale}"
    return _render_agent_card("🎯", f"Decision Agent — {symbol}", content, color)


def _render_execution_card(execution: ExecutionResult, symbol: str) -> str:
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
    return _render_agent_card("💸", "Execution Agent — Order Confirmation", content, status_color)


# ════════════════════════════════════════════════════════════════════════
# Simulated account summary
# ════════════════════════════════════════════════════════════════════════

def _render_account_summary() -> str:
    """Render the simulated paper trading account summary with P&L chart."""
    account = get_account()

    # ── Open positions table ───────────────────────────────────────────
    positions_html = ""
    pnl_values: list[tuple[str, float, str]] = []  # (label, amount, color) for bar chart
    for p in account.positions:
        pnl_sign = "+" if p.unrealized_pnl >= 0 else ""
        pnl_color = GREEN if p.unrealized_pnl >= 0 else RED
        pnl_values.append((p.symbol, p.unrealized_pnl, pnl_color))
        positions_html += f"""
        <tr>
            <td style="padding:6px 8px; color:{TEXT}; font-weight:600;">{p.symbol}</td>
            <td style="padding:6px 8px; color:{SECONDARY};">{p.strategy}</td>
            <td style="padding:6px 8px; color:{SECONDARY};">{p.option_type}</td>
            <td style="padding:6px 8px; color:{SECONDARY};">${p.strike:.0f}</td>
            <td style="padding:6px 8px; color:{SECONDARY};">{p.expiration[:10] if p.expiration else '-'}</td>
            <td style="padding:6px 8px; color:{SECONDARY};">{p.quantity}</td>
            <td style="padding:6px 8px; color:{SECONDARY};">${p.entry_price:.2f}</td>
            <td style="padding:6px 8px; color:{pnl_color}; font-weight:600;">{pnl_sign}${p.unrealized_pnl:,.2f}</td>
            <td style="padding:4px 6px;">
                <button onclick="var inp=document.querySelector('#close-pos-input input');if(inp){{inp.value='{p.position_id}';inp.dispatchEvent(new Event('input',{{bubbles:true}}));setTimeout(function(){{document.querySelector('#close-pos-btn').click()}},50);}}"
                    style="background:{RED}22; color:{RED}; border:1px solid {RED}44; border-radius:4px;
                    padding:3px 10px; cursor:pointer; font-size:0.78em; white-space:nowrap;"
                    title="Close this position and realise P&amp;L">
                    ✕ Close
                </button>
            </td>
        </tr>"""

    no_positions = (
        '<tr><td colspan="9" style="text-align:center; padding:14px; color:{c}; font-style:italic;">'
        'No open positions — run an analysis and approve a trade to get started.</td></tr>'
    ).format(c=SECONDARY)

    real_pnl = account.realized_pnl
    unreal_pnl = account.unrealized_pnl
    pnl_total = account.total_pnl

    pnl_color = GREEN if pnl_total >= 0 else RED
    real_color = GREEN if real_pnl >= 0 else RED
    unreal_color = GREEN if unreal_pnl >= 0 else RED

    def _pnl_str(val: float) -> str:
        s = "+" if val >= 0 else ""
        return f"{s}${val:,.2f}"

    # ── P&L bar chart ─────────────────────────────────────────────────
    chart_html = ""
    if pnl_values:
        # Sort by absolute P&L, largest first
        pnl_values.sort(key=lambda x: abs(x[1]), reverse=True)
        max_abs = max(abs(v[1]) for v in pnl_values) if pnl_values else 1
        max_abs = max(max_abs, 1.0)  # avoid division by zero

        for label, amount, color in pnl_values:
            bar_pct = min(abs(amount) / max_abs * 100, 100)
            is_positive = amount >= 0
            bar_color = GREEN if is_positive else RED
            bar_bg = f"{GREEN}18" if is_positive else f"{RED}18"
            chart_html += f"""
            <div style="display:flex; align-items:center; margin-bottom:6px; gap:8px;">
                <div style="min-width:52px; color:{TEXT}; font-size:0.8em; font-weight:600; text-align:right;">{label}</div>
                <div style="flex:1; background:{bar_bg}; border-radius:4px; height:22px; display:flex; align-items:center; padding:0 6px;">
                    <div style="height:14px; width:{bar_pct:.0f}%; background:{bar_color}; border-radius:3px;
                        min-width:4px; transition:width 0.4s ease;"></div>
                </div>
                <div style="min-width:80px; color:{color}; font-size:0.78em; font-weight:600;">{_pnl_str(amount)}</div>
            </div>"""
    else:
        chart_html = (
            f'<div style="text-align:center; padding:20px; color:{SECONDARY}; font-style:italic;">'
            'No open positions — P&L chart will appear after your first trade.'
            '</div>'
        )

    # ── Trade history (closed positions) ──────────────────────────────
    trade_history_html = ""
    for t in reversed(account.trade_history[-15:]):
        t_color = GREEN if t.realized_pnl >= 0 else RED
        t_sign = "+" if t.realized_pnl >= 0 else ""
        trade_history_html += f"""
        <tr>
            <td style="padding:4px 6px; color:{SECONDARY}; font-size:0.78em;">{t.exit_date.strftime('%m/%d %H:%M')}</td>
            <td style="padding:4px 6px; color:{TEXT}; font-weight:600; font-size:0.8em;">{t.symbol}</td>
            <td style="padding:4px 6px; color:{SECONDARY}; font-size:0.78em;">{t.strategy}</td>
            <td style="padding:4px 6px; color:{SECONDARY}; font-size:0.78em;">${t.entry_price:.2f}</td>
            <td style="padding:4px 6px; color:{SECONDARY}; font-size:0.78em;">${t.exit_price:.2f}</td>
            <td style="padding:4px 6px; color:{t_color}; font-weight:700; font-size:0.8em;">{t_sign}${t.realized_pnl:,.2f}</td>
        </tr>"""

    no_history = (
        '<tr><td colspan="6" style="text-align:center; padding:12px; color:{c}; font-style:italic; font-size:0.82em;">'
        'No closed trades yet. Close a position to see your realised P&amp;L history.'
        '</td></tr>'
    ).format(c=SECONDARY)

    # ── Rejection history ────────────────────────────────────────────
    rejection_html = ""
    for r in reversed(account.rejection_history[-15:]):
        rejection_html += f"""
        <tr>
            <td style="padding:4px 6px; color:{SECONDARY}; font-size:0.78em;">{r.rejected_at.strftime('%m/%d %H:%M')}</td>
            <td style="padding:4px 6px; color:{TEXT}; font-weight:600; font-size:0.8em;">{r.symbol}</td>
            <td style="padding:4px 6px; color:{SECONDARY}; font-size:0.78em;">{r.strategy}</td>
            <td style="padding:4px 6px; color:{SECONDARY}; font-size:0.78em; max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{r.reason}">{r.reason}</td>
            <td style="padding:4px 6px; color:{RED}; font-weight:700; font-size:0.8em;">✕ Rejected</td>
        </tr>"""

    no_rejections = (
        '<tr><td colspan="5" style="text-align:center; padding:12px; color:{c}; font-style:italic; font-size:0.82em;">'
        'No rejected trades yet. Rejections appear here when you decline a recommended trade.'
        '</td></tr>'
    ).format(c=SECONDARY)

    # Equity performance chart
    equity_html = ""
    snapshots = account.equity_snapshots
    if len(snapshots) >= 2:
        start_equity = snapshots[0].equity if snapshots else 100_000.0
        min_e = min(s.equity for s in snapshots)
        max_e = max(s.equity for s in snapshots)
        range_e = max(max_e - min_e, 1.0)
        bar_width_pct = max(1, 100 // max(len(snapshots), 1))
        bars_parts = []
        for s in snapshots[-40:]:
            height_pct = max(4, ((s.equity - min_e) / range_e) * 100)
            is_above_start = s.equity >= start_equity
            bar_color = GREEN if is_above_start else RED
            title_str = f'${s.equity:,.2f} -- {s.label}'
            bars_parts.append(
                f'<div style="flex:1; display:flex; flex-direction:column; align-items:center; min-width:{bar_width_pct}px;">'
                f'<div style="width:100%; height:80px; display:flex; align-items:flex-end; justify-content:center;">'
                f'<div title="{title_str}" style="width:{max(2, bar_width_pct - 4)}px; height:{height_pct:.0f}%;'
                f'background:{bar_color}; border-radius:2px 2px 0 0; min-height:3px; transition:height .3s ease;"></div>'
                f'</div></div>'
            )
        bars_html = ''.join(bars_parts)
        equity_html = (
            f'<div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">'
            f'📈 Equity Performance '
            f'<span style="font-weight:400; color:{SECONDARY}; font-size:0.85em;">-- {len(snapshots)} snapshots</span>'
            f'</div>'
            f'<div style="background:{BG}; border-radius:8px; padding:14px 10px 8px; margin-bottom:16px; overflow-x:auto;">'
            f'<div style="display:flex; align-items:flex-end; gap:1px; height:90px; min-width:200px;">'
            f'{bars_html}'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.68em; color:{SECONDARY};">'
            f'<span>${snapshots[0].equity:,.0f}</span>'
            f'<span>{snapshots[0].timestamp.strftime("%H:%M")}</span>'
            f'<span>-></span>'
            f'<span>{snapshots[-1].timestamp.strftime("%H:%M")}</span>'
            f'<span>${snapshots[-1].equity:,.0f}</span>'
            f'</div></div>'
        )
    elif len(snapshots) == 1:
        equity_html = (
            f'<div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">'
            f'📈 Equity Performance</div>'
            f'<div style="background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center;'
            f'color:{SECONDARY}; font-style:italic; font-size:0.82em;">'
            f'Starting equity: ${snapshots[0].equity:,.2f} -- more data will appear after your next trade.'
            f'</div>'
        )
    else:
        equity_html = (
            f'<div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">'
            f'📈 Equity Performance</div>'
            f'<div style="background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center;'
            f'color:{SECONDARY}; font-style:italic; font-size:0.82em;">'
            f'No trades yet -- equity chart will appear after your first trade.'
            f'</div>'
        )


    return f"""
    <div class="trading-card" style="border-left:4px solid {TEAL}; margin-top:20px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.4em;">💼</span>
                <div>
                    <div style="font-weight:700; color:{TEXT}; font-size:1.05em;">Simulated Account</div>
                    <div style="font-size:0.8em; color:{SECONDARY};">Paper Trading — No Real Money</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.85em; color:{SECONDARY};">Cash</div>
                <div style="font-weight:700; color:{GREEN};">${account.cash:,.2f}</div>
            </div>
        </div>

        <!-- Key metrics -->
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin-bottom:16px;">
            <div style="background:{BG}; border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:0.78em; color:{SECONDARY};">Total Equity</div>
                <div style="font-weight:700; color:{TEXT}; font-size:1.1em;">${account.total_equity:,.2f}</div>
            </div>
            <div style="background:{BG}; border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:0.78em; color:{SECONDARY};">Total P&amp;L</div>
                <div style="font-weight:700; color:{pnl_color}; font-size:1.1em;">{_pnl_str(pnl_total)}</div>
            </div>
            <div style="background:{BG}; border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:0.78em; color:{SECONDARY};">Open Positions</div>
                <div style="font-weight:700; color:{ACCENT}; font-size:1.1em;">{len(account.positions)}</div>
            </div>
            <div style="background:{BG}; border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:0.78em; color:{SECONDARY};">Closed Trades</div>
                <div style="font-weight:700; color:{PURPLE}; font-size:1.1em;">{len(account.trade_history)}</div>
            </div>
        </div>

        {equity_html}
        <!-- P&L Breakdown: Realised vs Unrealised -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
            <div style="background:{BG}; border-radius:8px; padding:12px; border-left:3px solid {GREEN};">
                <div style="font-size:0.72em; color:{SECONDARY}; text-transform:uppercase; letter-spacing:0.5px;">✅ Realised P&amp;L</div>
                <div style="font-weight:700; color:{real_color}; font-size:1.05em; margin-top:2px;">{_pnl_str(real_pnl)}</div>
            </div>
            <div style="background:{BG}; border-radius:8px; padding:12px; border-left:3px solid {AMBER};">
                <div style="font-size:0.72em; color:{SECONDARY}; text-transform:uppercase; letter-spacing:0.5px;">📊 Unrealised P&amp;L</div>
                <div style="font-weight:700; color:{unreal_color}; font-size:1.05em; margin-top:2px;">{_pnl_str(unreal_pnl)}</div>
            </div>
        </div>

        <!-- P&L Bar Chart -->
        <div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">
            📊 P&amp;L Breakdown by Position
        </div>
        <div style="background:{BG}; border-radius:8px; padding:14px 16px; margin-bottom:16px;">
            {chart_html}
        </div>

        <!-- Open Positions -->
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <div style="font-weight:700; color:{TEXT}; font-size:0.92em;">📋 Open Positions</div>
            <div style="font-size:0.75em; color:{SECONDARY};">{len(account.positions)} active</div>
        </div>
        <div style="overflow-x:auto; margin-bottom:16px;">
            <table style="width:100%; font-size:0.8em; border-collapse:collapse;">
                <thead>
                    <tr style="color:{SECONDARY}; border-bottom:1px solid {BORDER};">
                        <th style="text-align:left; padding:6px 8px;">Symbol</th>
                        <th style="text-align:left; padding:6px 8px;">Strategy</th>
                        <th style="text-align:left; padding:6px 8px;">Type</th>
                        <th style="text-align:left; padding:6px 8px;">Strike</th>
                        <th style="text-align:left; padding:6px 8px;">Expiry</th>
                        <th style="text-align:left; padding:6px 8px;">Qty</th>
                        <th style="text-align:left; padding:6px 8px;">Entry</th>
                        <th style="text-align:left; padding:6px 8px;">P&amp;L</th>
                        <th style="text-align:center; padding:6px 6px;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {positions_html if account.positions else no_positions}
                </tbody>
            </table>
        </div>

        <!-- Trade History (closed positions) -->
        <div style="font-weight:700; color:{TEXT}; margin-bottom:8px; font-size:0.92em;">
            📜 Trade History <span style="font-weight:400; color:{SECONDARY}; font-size:0.85em;">— Last 15 closed trades</span>
        </div>
        <div style="overflow-x:auto; margin-bottom:12px;">
            <table style="width:100%; font-size:0.78em; border-collapse:collapse;">
                <thead>
                    <tr style="color:{SECONDARY}; border-bottom:1px solid {BORDER};">
                        <th style="text-align:left; padding:4px 6px;">Date</th>
                        <th style="text-align:left; padding:4px 6px;">Symbol</th>
                        <th style="text-align:left; padding:4px 6px;">Strategy</th>
                        <th style="text-align:left; padding:4px 6px;">Entry</th>
                        <th style="text-align:left; padding:4px 6px;">Exit</th>
                        <th style="text-align:left; padding:4px 6px;">Realised P&amp;L</th>
                    </tr>
                </thead>
                <tbody>
                    {trade_history_html if account.trade_history else no_history}
                </tbody>
            </table>
        </div>

        <!-- Rejection History -->
        <div style="font-weight:700; color:{TEXT}; margin-bottom:8px; font-size:0.92em;">
            🚫 Rejection History <span style="font-weight:400; color:{SECONDARY}; font-size:0.85em;">— Last 15 rejected trades</span>
        </div>
        <div style="overflow-x:auto; margin-bottom:12px;">
            <table style="width:100%; font-size:0.78em; border-collapse:collapse;">
                <thead>
                    <tr style="color:{SECONDARY}; border-bottom:1px solid {BORDER};">
                        <th style="text-align:left; padding:4px 6px;">Date</th>
                        <th style="text-align:left; padding:4px 6px;">Symbol</th>
                        <th style="text-align:left; padding:4px 6px;">Strategy</th>
                        <th style="text-align:left; padding:4px 6px;">Reason</th>
                        <th style="text-align:left; padding:4px 6px;">Outcome</th>
                    </tr>
                </thead>
                <tbody>
                    {rejection_html if account.rejection_history else no_rejections}
                </tbody>
            </table>
        </div>

        <div style="display:flex; gap:8px; margin-top:12px; justify-content:flex-end;">
            <button onclick="document.querySelector('#reset-account-btn').click()"
                style="background:{BORDER}; color:{SECONDARY}; border:none; border-radius:6px;
                padding:6px 14px; cursor:pointer; font-size:0.82em;">
                🔄 Reset Account
            </button>
        </div>
    </div>"""



def _render_flow_diagram(
    security_ok: bool = False,
    sentiment_ok: bool = False,
    regime_ok: bool = False,
    chain_ok: bool = False,
    decision_ok: bool = False,
    strategy_name: str = "",
    execution_ok: bool = False,
    pending_approval: bool = False,
    rejected: bool = False,
) -> str:
    """Render a LangGraph-style flow diagram showing agent pipeline status."""

    def _node(status: str, icon: str, label: str, detail: str = "",
              is_decision: bool = False, is_exec: bool = False) -> str:
        if status == "active":
            bg = f"linear-gradient(135deg, {ACCENT}22, {ACCENT}08)"
            border = ACCENT
            glow = "box-shadow: 0 0 12px rgba(77,166,255,0.25);"
            pulse = ""
        elif status == "complete":
            bg = f"linear-gradient(135deg, {GREEN}18, {GREEN}06)"
            border = GREEN
            glow = ""
            pulse = ""
        elif status == "pending_review":
            bg = f"linear-gradient(135deg, {AMBER}18, {AMBER}06)"
            border = AMBER
            glow = "box-shadow: 0 0 12px rgba(255,171,0,0.3);"
            pulse = "animation: pulse-amber 1.8s ease-in-out infinite;"
        elif status == "error":
            bg = f"linear-gradient(135deg, {RED}18, {RED}06)"
            border = RED
            glow = ""
            pulse = ""
        elif status == "rejected":
            bg = f"linear-gradient(135deg, {RED}15, {RED}05)"
            border = RED
            glow = ""
            pulse = ""
        else:  # pending
            bg = f"linear-gradient(135deg, {BORDER}44, {BORDER}22)"
            border = BORDER
            glow = ""
            pulse = ""

        if is_decision:
            shape = "border-radius:6px;"
            width = "min-width:200px;"
        elif is_exec:
            shape = "border-radius:6px;"
            width = "min-width:180px;"
        else:
            shape = "border-radius:8px;"
            width = "min-width:180px;"

        return f"""
        <div style="
            {shape} {width}
            background:{bg};
            border:1.5px solid {border};
            padding:14px 16px;
            text-align:center;
            {glow} {pulse}
            transition: all 0.3s ease;
        ">
            <div style="font-size:1.5em; margin-bottom:4px;">{icon}</div>
            <div style="font-weight:700; color:{TEXT}; font-size:0.88em; line-height:1.3;">{label}</div>
            {f'<div style="color:{SECONDARY}; font-size:0.75em; margin-top:3px;">{detail}</div>' if detail else ''}
        </div>"""

    def _arrow(color: str = BORDER, label: str = "") -> str:
        lbl = f'<div style="font-size:0.68em; color:{color}; text-align:center; margin:2px 0;">{label}</div>' if label else ""
        return f"""
        <div style="display:flex; flex-direction:column; align-items:center; margin:0 4px;">
            {lbl}
            <div style="width:2px; height:16px; background:{color};"></div>
            <div style="width:0; height:0; border-left:5px solid transparent; border-right:5px solid transparent; border-top:7px solid {color};"></div>
        </div>"""

    # Determine node statuses
    sec_s = "complete" if security_ok else "pending"
    sent_s = "complete" if sentiment_ok else "pending"
    reg_s = "complete" if regime_ok else "pending"
    chain_s = "complete" if chain_ok else "pending"
    
    if rejected:
        dec_s = "rejected"
    elif decision_ok and pending_approval:
        dec_s = "pending_review"
    elif decision_ok:
        dec_s = "complete"
    else:
        dec_s = "pending"

    if rejected:
        exec_s = "pending"
    elif execution_ok:
        exec_s = "complete"
    else:
        exec_s = "pending"

    # Decision detail text
    dec_detail = ""
    if strategy_name and decision_ok:
        dec_detail = f"→ {strategy_name}"
    elif rejected:
        dec_detail = "✕ Rejected"
    elif strategy_name:
        dec_detail = f"⏸️ {strategy_name}"

    return f"""
    <div class="trading-card" style="border-left:4px solid {PURPLE};">
        <div style="font-weight:700; color:{TEXT}; margin-bottom:14px; display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.2em;">📊</span> Agent Pipeline Flow
            <span style="font-size:0.75em; color:{SECONDARY}; font-weight:400;">
                — LangGraph Orchestration
            </span>
        </div>

        <div style="display:flex; flex-wrap:wrap; align-items:flex-start; gap:2px; justify-content:center;">
            {_node(sec_s, "🔍", "Security<br>Agent", detail="Identify & validate")}
            {_arrow()}
            {_node(sent_s, "🌐", "Risk &<br>Sentiment", detail="Fear & Greed + News")}
            {_arrow()}
            {_node(reg_s, "🔄", "Regime<br>Detection", detail="Bull / Bear / Neutral")}
            {_arrow()}
            {_node(chain_s, "📈", "Options<br>Chain", detail="Fetch contracts")}
            {_arrow()}
            {_node(dec_s, "🎯", "Decision<br>Agent", detail=dec_detail, is_decision=True)}

            <div style="display:flex; flex-direction:column; align-items:center; margin:0 4px;">
                <div style="font-size:0.65em; color:{AMBER}; text-align:center; padding:2px 6px; border-radius:4px;
                    background:{AMBER}15; margin-bottom:2px;">🔍 Human Review</div>
                <div style="width:2px; height:16px; background:{AMBER if pending_approval else BORDER};"></div>
                <div style="width:0; height:0; border-left:5px solid transparent; border-right:5px solid transparent;
                    border-top:7px solid {AMBER if pending_approval else BORDER};"></div>
            </div>

            {_node(exec_s, "💸", "Execution<br>Agent", detail="MCP Paper Trade", is_exec=True)}
        </div>

        <div style="margin-top:14px; padding:10px 14px; background:{BG}; border-radius:8px;
            border:1px solid {BORDER}; font-size:0.82em;">
            <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap; justify-content:center;">
                <span style="display:flex; align-items:center; gap:4px; color:{GREEN};">
                    <span>●</span> Complete
                </span>
                <span style="display:flex; align-items:center; gap:4px; color:{ACCENT};">
                    <span>●</span> Running
                </span>
                <span style="display:flex; align-items:center; gap:4px; color:{AMBER};">
                    <span>◉</span> Awaiting Approval
                </span>
                <span style="display:flex; align-items:center; gap:4px; color:{RED};">
                    <span>●</span> Rejected / Error
                </span>
                <span style="display:flex; align-items:center; gap:4px; color:{SECONDARY};">
                    <span>○</span> Pending
                </span>
            </div>
        </div>
    </div>
    <style>
        @keyframes pulse-amber {{
            0%, 100% {{ box-shadow: 0 0 8px rgba(255,171,0,0.2); }}
            50% {{ box-shadow: 0 0 16px rgba(255,171,0,0.45); }}
        }}
    </style>"""


# ════════════════════════════════════════════════════════════════════════
# Core workflow — two-phase: ① analyze → ② approve/reject → execute
# ════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════
# Helpers — deterministic mode, step indicator, MCP connectivity
# ════════════════════════════════════════════════════════════════════

def _is_deterministic(api_key: str, provider: str) -> bool:
    """Check whether the workflow will run in deterministic (no-LLM) mode."""
    if api_key.strip():
        return False
    env_var = "OPENAI_API_KEY" if provider.lower() == "openai" else "ANTHROPIC_API_KEY"
    return not os.environ.get(env_var, "")


def _render_badge(label: str, color: str, bg_alpha: str = "18") -> str:
    """Render a small inline badge."""
    return f'<span style="background:{color}{bg_alpha}; color:{color}; border:1px solid {color}44; border-radius:4px; padding:2px 8px; font-size:0.72em; font-weight:600; white-space:nowrap;">{label}</span>'


def _render_step_indicator(current_step: int, deterministic: bool = False) -> str:
    """Render a workflow step indicator showing the pipeline stages."""
    steps = [
        (1, "\u2699\ufe0f", "Configure"),
        (2, "\U0001f50d", "Analyze"),
        (3, "\U0001f441\ufe0f", "Review"),
        (4, "\U0001f4bc", "Account"),
    ]
    items_parts: list[str] = []
    for i, (num, icon, label) in enumerate(steps):
        if num < current_step:
            color = GREEN
            bg = f"{GREEN}18"
            border = GREEN
            badge = "\u2713"
        elif num == current_step:
            color = ACCENT
            bg = f"{ACCENT}18"
            border = ACCENT
            badge = str(num)
        else:
            color = SECONDARY
            bg = f"{BORDER}44"
            border = BORDER
            badge = str(num)

        arrow = ""
        if i < len(steps) - 1:
            arrow_color = GREEN if num < current_step else BORDER
            arrow = f'<div style="flex:0 0 24px; height:2px; background:{arrow_color}; margin:0 2px; align-self:center;"></div>'

        items_parts.append(f"""
        <div style="display:flex; align-items:center; gap:5px; background:{bg}; border:1.5px solid {border};
            border-radius:7px; padding:5px 10px; white-space:nowrap; transition:all 0.3s;">
            <span style="font-size:0.9em;">{icon}</span>
            <span style="font-weight:700; color:{color}; font-size:0.78em;">{label}</span>
            <span style="background:{border}; color:{TEXT}; border-radius:50%; width:16px; height:16px;
                display:inline-flex; align-items:center; justify-content:center; font-size:0.65em; font-weight:700;">
                {badge}
            </span>
        </div>""")
        items_parts.append(arrow)

    det_badge = _render_badge("\U0001f9e0 Deterministic", PURPLE) if deterministic else _render_badge("\U0001f916 LLM", ACCENT)
    return f"""
    <div style="display:flex; align-items:center; justify-content:center; padding:8px 0; margin-bottom:4px;
        flex-wrap:wrap; gap:2px;">
        {"".join(items_parts)}
        <div style="margin-left:12px;">{det_badge}</div>
    </div>"""


def _render_mcp_connectivity(mcp_calls: list[dict] | None = None) -> str:
    """Render MCP paper-trading server connectivity status."""
    if not mcp_calls:
        return f"""
        <div style="background:{CARD}; border:1px solid {BORDER}; border-radius:8px; padding:10px 14px;
            margin-bottom:12px; display:flex; align-items:center; gap:10px;">
            <span style="font-size:1.2em;">\U0001f50c</span>
            <div>
                <div style="font-weight:600; color:{TEXT}; font-size:0.85em;">MCP Paper-Trading Server</div>
                <div style="color:{SECONDARY}; font-size:0.78em;">
                    <span style="color:{GREEN};">\u25cf</span> Connected &mdash; ready for order submission
                </div>
            </div>
        </div>"""

    call_rows = ""
    for call in mcp_calls:
        tool = call.get("tool", "?")
        status = call.get("status", "?")
        sc = GREEN if status == "success" else RED
        si = "\u2705" if status == "success" else "\u274c"
        detail = call.get("detail", "")
        call_rows += f"""
        <tr>
            <td style="padding:4px 8px; color:{SECONDARY}; font-size:0.78em; font-family:monospace;">{tool}</td>
            <td style="padding:4px 8px; color:{sc}; font-size:0.78em;">{si} {status}</td>
            <td style="padding:4px 8px; color:{SECONDARY}; font-size:0.76em;">{detail}</td>
        </tr>"""

    return f"""
    <div style="background:{CARD}; border:1px solid {ACCENT}33; border-radius:8px; padding:10px 14px;
        margin-bottom:12px;">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="font-size:1.2em;">\U0001f50c</span>
            <div style="flex:1;">
                <div style="font-weight:600; color:{TEXT}; font-size:0.85em;">MCP Paper-Trading Server</div>
                <div style="color:{ACCENT}; font-size:0.78em;">\u25cf Active &mdash; {len(mcp_calls)} tool call(s)</div>
            </div>
        </div>
        <table style="width:100%; font-size:0.75em; border-collapse:collapse;">
            <thead>
                <tr style="color:{SECONDARY}; border-bottom:1px solid {BORDER};">
                    <th style="text-align:left; padding:4px 8px;">Tool</th>
                    <th style="text-align:left; padding:4px 8px;">Status</th>
                    <th style="text-align:left; padding:4px 8px;">Detail</th>
                </tr>
            </thead>
            <tbody>
                {call_rows}
            </tbody>
        </table>
    </div>"""


# ════════════════════════════════════════════════════════════════════
# Core workflow — two-phase: analyze / approve-reject / execute
# ════════════════════════════════════════════════════════════════════

def _run_analysis(
    symbol: str,
    api_key: str,
    provider: str,
    model: str,
    show_trace: bool,
) -> tuple[str, str, str, str, str]:
    """Phase 1: Run the analysis pipeline (stops before execution).

    Returns:
        (flow_html, trace_html, status_html, log_html, state_json)
    """
    deterministic = _is_deterministic(api_key, provider)

    if not symbol or not symbol.strip():
        error = _render_agent_card("🔍", "Security Agent",
                                    "Please enter a stock symbol.", ACCENT, "error")
        return (
            _render_flow_diagram(),
            error,
            _render_step_indicator(1, deterministic) + f"<div style='color:{RED}; text-align:center;'>❌ Please enter a valid stock symbol.</div>",
            "",
            "{}",
        )

    try:
        state = run_trading_workflow(
            symbol=symbol,
            llm_provider=provider.lower(),
            llm_model=model,
            openai_api_key=api_key.strip(),
            user_approved=False,
        )
    except Exception as e:
        error = _render_agent_card("❌", "Error", f"Workflow failed: {str(e)}", RED, "error")
        return (
            _render_flow_diagram(),
            error,
            _render_step_indicator(1, deterministic) + f"<div style='color:{RED}; text-align:center;'>❌ Error: {str(e)}</div>",
            "",
            "{}",
        )

    # ── Build execution trace ──────────────────────────────────────────
    security = state.get("security")
    sentiment = state.get("sentiment")
    regime = state.get("regime")
    chain = state.get("options_chain")
    strategy = state.get("strategy")

    trace_parts: list[str] = []

    # Header
    key_status = "🔑 User key" if api_key.strip() else "🌐 Environment variable"
    trace_parts.append(
        f"<div style='color:{SECONDARY}; font-size:0.82em; text-align:center; margin-bottom:16px; "
        f"padding:8px 12px; background:{CARD}; border:1px solid {BORDER}; border-radius:8px;'>"
        f"Provider: <b style='color:{ACCENT};'>{provider.upper()}</b> &nbsp;|&nbsp; "
        f"Model: <b style='color:{ACCENT};'>{model or get_default_model(provider)}</b> &nbsp;|&nbsp; "
        f"Auth: {key_status}"
        f"</div>"
    )

    if security:
        trace_parts.append(_render_security_card(security))
    else:
        trace_parts.append(_render_agent_card(
            "🔍", "Security Agent", "No security data available.", ACCENT, "error"))

    if sentiment:
        trace_parts.append(_render_sentiment_card(sentiment))

    if regime:
        trace_parts.append(_render_regime_card(regime))

    if chain:
        chain_html = f"📊 <b>Options Chain</b> — {chain.symbol} @ ${chain.underlying_price:.2f}\n"
        chain_html += f"📅 Expirations: {', '.join(chain.expiration_dates[:3])}\n"
        chain_html += f"📈 {len(chain.calls)} calls, {len(chain.puts)} puts available\n"
        trace_parts.append(_render_agent_card("📈", "Options Chain", chain_html, TEAL))

    if strategy:
        trace_parts.append(_render_decision_card(strategy, symbol))
    elif state.get("error"):
        trace_parts.append(_render_agent_card(
            "🎯", "Decision Agent", f"Error: {state['error']}", AMBER, "error"))

    # Conditional: pending approval or no-trade
    is_no_trade = strategy and strategy.strategy == OptionStrategy.NO_TRADE
    if is_no_trade:
        trace_parts.append(f"""
        <div class="trading-card" style="border-left:4px solid {AMBER}; text-align:center;">
            <div style="font-size:1.5em; margin-bottom:8px;">⏸️</div>
            <div style="font-weight:700; color:{TEXT}; font-size:1.1em;">
                No Trade Recommended
            </div>
            <div style="color:{SECONDARY}; font-size:0.9em; margin-top:6px;">
                The Decision Agent recommends no trade under current conditions.
                No execution is needed — review the rationale above.
            </div>
        </div>""")

    execution_trace = "\n".join(trace_parts)

    # ── Flow diagram ───────────────────────────────────────────────────
    flow = _render_flow_diagram(
        security_ok=bool(security),
        sentiment_ok=bool(sentiment),
        regime_ok=bool(regime),
        chain_ok=bool(chain),
        decision_ok=bool(strategy),
        strategy_name=strategy.strategy.value if strategy else "",
        pending_approval=(not is_no_trade and bool(strategy)),
    )

    # ── Status (with step indicator) ───────────────────────────────────
    stage = state.get("stage", "unknown")
    error = state.get("error", "")
    if error:
        status = _render_step_indicator(2, deterministic) + f"<div style='color:{RED}; text-align:center; font-size:1.1em;'>⚠️ Workflow completed with errors — Stage: {stage}</div>"
    elif is_no_trade:
        status = _render_step_indicator(2, deterministic) + f"<div style='color:{AMBER}; text-align:center; font-size:1.1em;'>⏸️ Analysis complete — No trade recommended</div>"
    else:
        status = _render_step_indicator(3, deterministic) + f"<div style='color:{ACCENT}; text-align:center; font-size:1.1em;'>✅ Analysis complete — Review the recommendation below</div>"

    # ── Log ────────────────────────────────────────────────────────────
    log = state.get("log", [])
    log_html = _format_log(log)

    # ── State for next phase ───────────────────────────────────────────
    # Serialize only what we need for the execution phase
    state_payload = {
        "symbol": state.get("symbol", symbol),
        "llm_provider": state.get("llm_provider", provider),
        "llm_model": state.get("llm_model", model),
        "openai_api_key": state.get("openai_api_key", ""),
        "deterministic": deterministic,
    }
    # Include strategy if present
    if strategy:
        state_payload["strategy_value"] = strategy.strategy.value
        state_payload["strategy_strike"] = strategy.recommended_strike
        state_payload["strategy_expiration"] = strategy.recommended_expiration

    return flow, execution_trace if show_trace else "", status, log_html, json.dumps(state_payload)


def _run_execution_phase(state_json: str, show_trace: bool) -> tuple[str, str, str, str]:
    """Phase 2: User approved — execute the trade using the captured decision.

    Calls the ExecutionAgent directly with a StrategyDecision reconstructed
    from the serialised state (no re-analysis needed).
    """
    try:
        prior = json.loads(state_json)
    except (json.JSONDecodeError, TypeError):
        return (
            _render_flow_diagram(),
            "",
            _render_step_indicator(2, False) + f"<div style='color:{RED}; text-align:center;'>❌ Invalid analysis state. Please re-run the analysis.</div>",
            "",
        )

    symbol = prior.get("symbol", "")
    strategy_value = prior.get("strategy_value", "")
    deterministic = prior.get("deterministic", False)

    # Guard: refuse to execute if there is no tradeable strategy
    if not strategy_value or strategy_value == "No Trade":
        return (
            _render_flow_diagram(
                security_ok=True, sentiment_ok=True, regime_ok=True,
                chain_ok=True, decision_ok=True,
                strategy_name=strategy_value or "No Trade",
            ),
            f"<div class='trading-card' style='border-left:4px solid {AMBER}; text-align:center;'>"
            f"<div style='font-size:1.5em; margin-bottom:8px;'>⏸️</div>"
            f"<div style='font-weight:700; color:{TEXT}; font-size:1.1em;'>No Trade to Execute</div>"
            f"<div style='color:{SECONDARY}; font-size:0.9em; margin-top:6px;'>"
            f"The decision was <b>{strategy_value or 'no trade'}</b>. "
            f"Please re-run the analysis if you want to trade.</div></div>",
            _render_step_indicator(2, deterministic) + f"<div style='color:{AMBER}; text-align:center;'>⏸️ No trade executed — strategy was {strategy_value or 'not set'}</div>",
            "",
        )

    # Map strategy value string back to OptionStrategy enum
    strategy_map: dict[str, OptionStrategy] = {
        "Long Call": OptionStrategy.CALL,
        "Long Put": OptionStrategy.PUT,
        "Long Strangle": OptionStrategy.STRANGLE,
        "No Trade": OptionStrategy.NO_TRADE,
    }
    strategy_enum = strategy_map.get(strategy_value, OptionStrategy.NO_TRADE)

    # Build a minimal StrategyDecision from the saved state
    decision = StrategyDecision(
        strategy=strategy_enum,
        confidence=0.8,  # user approved, so high confidence
        recommended_strike=prior.get("strategy_strike"),
        recommended_expiration=prior.get("strategy_expiration"),
        rationale="User approved the trade after human-in-the-loop review.",
    )

    # Call the ExecutionAgent directly — no re-analysis
    agent = ExecutionAgent()
    try:
        result: ExecutionResult = agent.execute(decision, symbol)
        mcp_calls = agent.last_mcp_calls
    except Exception as e:
        mcp_calls = agent.last_mcp_calls
        mcp_calls.append({"tool": "place_option_order", "status": "failed", "detail": str(e)})
        return (
            _render_flow_diagram(
                security_ok=True, sentiment_ok=True, regime_ok=True,
                chain_ok=True, decision_ok=True,
                strategy_name=strategy_value,
            ),
            _render_mcp_connectivity(mcp_calls) + _render_agent_card(
                "💸", "Execution Agent",
                f"Execution failed: {str(e)}", RED, "error"),
            _render_step_indicator(3, deterministic) + f"<div style='color:{RED}; text-align:center;'>❌ Execution failed: {str(e)}</div>",
            "",
        )

    trace_parts: list[str] = []
    trace_parts.append(_render_mcp_connectivity(mcp_calls))
    trace_parts.append(_render_execution_card(result, symbol))
    execution_trace = "\n".join(trace_parts)

    flow = _render_flow_diagram(
        security_ok=True, sentiment_ok=True, regime_ok=True,
        chain_ok=True, decision_ok=True,
        strategy_name=strategy_value,
        execution_ok=True,
    )

    status = _render_step_indicator(4, deterministic) + f"<div style='color:{GREEN}; text-align:center; font-size:1.1em;'>✅ Trade Executed — {strategy_value} on {symbol}</div>"
    log_html = _format_log([
        f"[Execution] User approved {strategy_value} on {symbol}",
        f"[Execution] Order submitted via MCP paper trading",
        f"[Execution] Status: {result.confirmation.get('status', 'Unknown')}",
    ])

    return flow, execution_trace if show_trace else "", status, log_html


def _reject_trade(state_json: str, reason: str) -> tuple[str, str, str, str]:
    """User rejected the trade — record in rejection history."""
    try:
        prior = json.loads(state_json)
    except (json.JSONDecodeError, TypeError):
        return (
            _render_flow_diagram(),
            "",
            _render_step_indicator(2, False) + f"<div style='color:{RED}; text-align:center;'>❌ Invalid analysis state.</div>",
            "",
        )

    symbol = prior.get("symbol", "")
    strategy_val = prior.get("strategy_value", "unknown")
    deterministic = prior.get("deterministic", False)
    reason_text = reason.strip() or "User rejected the trade without providing a reason."

    # Persist the rejection so it appears in the account summary's history
    record_rejection(
        symbol=symbol,
        strategy=strategy_val,
        reason=reason_text,
        notes=f"Rejected {strategy_val} on {symbol} after human-in-the-loop review.",
    )

    flow = _render_flow_diagram(
        security_ok=True, sentiment_ok=True, regime_ok=True, chain_ok=True,
        decision_ok=True,
        strategy_name=strategy_val,
        rejected=True,
    )

    trace = _render_agent_card(
        "🚫", f"Trade Rejected — {symbol}",
        f"<b>Rejection Reason:</b> {reason_text}\n\n"
        f"Recommended strategy was <b>{strategy_val}</b>.\n"
        f"No trade was executed. You may re-run the analysis at any time.",
        RED, status="complete",
    )

    status = _render_step_indicator(4, deterministic) + f"<div style='color:{AMBER}; text-align:center; font-size:1.1em;'>🚫 Trade Rejected — No positions changed</div>"
    return flow, trace, status, ""


def _format_log(log: list[str]) -> str:
    """Format execution log as HTML."""
    if not log:
        return ""
    lines = "\n".join(
        f"<div style='padding:3px 0; border-bottom:1px solid {BORDER}; font-size:0.82em;'>{entry}</div>"
        for entry in log
    )
    return f"""
    <div style='color:{SECONDARY}; font-family:monospace; max-height:300px; overflow-y:auto;'>
        <div style='font-weight:700; color:{TEXT}; margin-bottom:8px;'>📋 Execution Log</div>
        {lines}
    </div>"""


def _reset_account_ui() -> tuple[str, str]:
    """Reset the paper trading account and return updated UI."""
    reset_account()
    return _render_account_summary(), ""


def _close_position_ui(position_id: str) -> tuple[str, str]:
    """Close a position by ID and refresh the account display."""
    if not position_id or not position_id.strip():
        return _render_account_summary(), ""
    close_position(position_id.strip())
    return _render_account_summary(), ""


def _approval_panel_update(state_json: str) -> gr.Column:
    """Show the execution panel only when a tradeable strategy exists."""
    if not state_json or state_json == "{}":
        return gr.update(visible=False)
    try:
        prior = json.loads(state_json)
    except (json.JSONDecodeError, TypeError):
        return gr.update(visible=False)
    if prior.get("strategy_value") and prior.get("strategy_value") != "No Trade":
        return gr.update(visible=True)
    return gr.update(visible=False)


# ════════════════════════════════════════════════════════════════════════
# Provider change handler
# ════════════════════════════════════════════════════════════════════════

def _on_provider_change(provider: str) -> gr.Dropdown:
    choices = _model_choices_for(provider.lower())
    default = get_default_model(provider.lower())
    return gr.Dropdown(choices=choices, value=default, interactive=True)


# ════════════════════════════════════════════════════════════════════════
# API key notice
# ════════════════════════════════════════════════════════════════════════

_API_KEY_NOTICE = """<div style="background:{card}; border:1px solid {border}; border-radius:10px; padding:16px; margin-bottom:16px;">
<div style="color:{accent}; font-weight:700; margin-bottom:6px;">🔑 API Key Required</div>
<div style="color:{secondary}; font-size:0.9em; line-height:1.5;">
This tab uses LLM agents that need an API key.<br>
<b>OpenAI:</b> Get yours at <a href="https://platform.openai.com/api-keys" target="_blank" style="color:{accent};">platform.openai.com/api-keys</a><br>
<b>Anthropic:</b> Get yours at <a href="https://console.anthropic.com/settings/keys" target="_blank" style="color:{accent};">console.anthropic.com/settings/keys</a><br><br>
Your key is used only for this session and <b>never stored</b>. Leave blank to use system environment variables.
</div>
</div>""".format(card=CARD, border=BORDER, accent=ACCENT, secondary=SECONDARY)


# ════════════════════════════════════════════════════════════════════════
# Tab builder
# ════════════════════════════════════════════════════════════════════════

def render_trading_tab() -> None:
    """Build the Trading Desk tab with HITL, flow diagram, and account summary."""
    # Hidden state to carry analysis results between phases
    analysis_state = gr.State("{}")

    with gr.Column(elem_id="trading-desk-shell", elem_classes=["trading-window"]):
        gr.Markdown(f"""
        <div class="trading-window-header">
            <div>
                <h1>Multi-Agent Options Trading Desk</h1>
                <p>5 specialized AI agents + <b>human-in-the-loop</b> execution review</p>
            </div>
            <span class="trading-window-badge">Paper Trading</span>
        </div>""")

        with gr.Row(elem_classes=["trading-workspace"]):
            # ── Left column: controls ──────────────────────────────────
            with gr.Column(scale=1, min_width=340, elem_classes=["trading-control-panel"]):
                gr.Markdown(_API_KEY_NOTICE)

                # LLM Configuration
                gr.Markdown(f"### ⚙️ LLM Configuration")
                provider_input = gr.Dropdown(
                    label="Provider",
                    choices=[("OpenAI", "openai"), ("Anthropic", "anthropic")],
                    value="openai", interactive=True,
                )
                model_input = gr.Dropdown(
                    label="Model",
                    choices=_model_choices_for("openai"),
                    value=get_default_model("openai"), interactive=True,
                )
                api_key_input = gr.Textbox(
                    label="API Key",
                    placeholder="sk-... or sk-ant-... (leave empty for env var)",
                    type="password",
                    info="Used only for this session — never stored.",
                )

                # Symbol input
                gr.Markdown("### 🎯 Trading Target")
                symbol_input = gr.Textbox(
                    label="Stock Symbol",
                    placeholder="e.g., AAPL, MSFT, NVDA, TSLA, SPY",
                    value="AAPL",
                    info="Enter any US stock symbol with options",
                )

                # Show/hide trace toggle
                show_trace = gr.Checkbox(
                    label="Show Execution Traces",
                    value=True,
                    info="Display detailed agent outputs as the pipeline runs",
                )

                # Run analysis button
                run_btn = gr.Button("🚀 Run Multi-Agent Analysis", variant="primary", size="lg")

                # HITL: execution panel (hidden initially, revealed when analysis has a trade)
                with gr.Column(elem_id="approval-panel", visible=False) as approval_column:
                    gr.Markdown(f"""
                    <div class="trading-action-panel">
                        <div style="color:{AMBER}; font-weight:800; font-size:1.05em; margin-bottom:8px;">Trade Execution Review</div>
                        <div style="color:{SECONDARY}; font-size:0.9em; margin-bottom:10px;">
                        The Decision Agent found a tradeable option strategy. Execute it in the simulated account or reject it.
                        </div>
                    </div>""")
                    rejection_reason = gr.Textbox(
                        label="Rejection Reason (optional)",
                        placeholder="Why are you rejecting this trade?",
                        visible=True,
                    )
                    with gr.Row():
                        execute_btn = gr.Button("Execute Trade", variant="primary", size="lg")
                        reject_btn = gr.Button("❌ Reject Trade", variant="stop", size="lg")

                # Reset account button (hidden — triggered by the account summary UI button)
                reset_btn = gr.Button("🔄 Reset Account", elem_id="reset-account-btn", visible=False)

                # Close position (hidden — triggered by close buttons in the positions table)
                close_pos_input = gr.Textbox(
                    elem_id="close-pos-input", visible=False, value="",
                )
                close_pos_btn = gr.Button(
                    "Close Position", elem_id="close-pos-btn", visible=False,
                )

                # Log output
                log_output = gr.HTML("", elem_id="trading-log")

            # ── Right column: outputs ──────────────────────────────────
            with gr.Column(scale=2, min_width=500, elem_classes=["trading-main-panel"]):
                # Status banner
                status_output = gr.HTML(_render_step_indicator(1, False) + f"""
                <div style="text-align:center; padding:20px; color:{SECONDARY};">
                    <div style="font-size:2em; margin-bottom:12px;">🤖</div>
                    <div style="font-size:1.1em; font-weight:600; color:{TEXT};">Ready to Trade</div>
                    <div style="margin-top:4px;">Configure your LLM, enter a symbol, and click <b>Run Analysis</b></div>
                </div>""")

                # Flow diagram
                flow_output = gr.HTML(
                    _render_flow_diagram()
                )

                # Execution trace — all agent outputs in sequence
                trace_output = gr.HTML(
                    f"<div style='text-align:center; padding:40px 20px; color:{SECONDARY};'>"
                    f"<div style='font-size:2em; margin-bottom:12px;'>📊</div>"
                    f"<div>Agent outputs will appear here after analysis.</div></div>"
                )

                # Account summary appears only after Execute Trade or Reject Trade.
                account_output = gr.HTML("", elem_id="trading-account-summary")

    # ── Wire up provider → model cascading ────────────────────────────
    provider_input.change(
        fn=_on_provider_change,
        inputs=[provider_input],
        outputs=[model_input],
    )

    # ── Phase 1: Run analysis ─────────────────────────────────────────
    run_btn.click(
        fn=_run_analysis,
        inputs=[symbol_input, api_key_input, provider_input, model_input, show_trace],
        outputs=[flow_output, trace_output, status_output, log_output, analysis_state],
    ).then(
        fn=_approval_panel_update,
        inputs=[analysis_state],
        outputs=[approval_column],
        js="""
        function() {
            var accountEl = document.getElementById('trading-account-summary');
            if (accountEl) accountEl.style.display = 'none';
        }
        """,
    )

    # ── Phase 2a: Execute approved trade ──────────────────────────────
    execute_btn.click(
        fn=_run_execution_phase,
        inputs=[analysis_state, show_trace],
        outputs=[flow_output, trace_output, status_output, log_output],
    ).then(
        fn=_render_account_summary,
        inputs=[],
        outputs=[account_output],
    ).then(
        fn=lambda: ("", ""),
        outputs=[analysis_state, rejection_reason],
    ).then(
        fn=None,
        js="""
        function() {
            var panel = document.getElementById('approval-panel');
            if (panel) panel.style.display = 'none';
            setTimeout(function() {
                var accountEl = document.getElementById('trading-account-summary');
                if (accountEl) {
                    accountEl.style.display = 'block';
                    accountEl.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            }, 200);
        }
        """,
    )

    # ── Phase 2b: Reject ──────────────────────────────────────────────
    reject_btn.click(
        fn=_reject_trade,
        inputs=[analysis_state, rejection_reason],
        outputs=[flow_output, trace_output, status_output, log_output],
    ).then(
        fn=_render_account_summary,
        inputs=[],
        outputs=[account_output],
    ).then(
        fn=lambda: ("", ""),
        outputs=[analysis_state, rejection_reason],
    ).then(
        fn=None,
        js="""
        function() {
            var panel = document.getElementById('approval-panel');
            if (panel) panel.style.display = 'none';
            setTimeout(function() {
                var accountEl = document.getElementById('trading-account-summary');
                if (accountEl) {
                    accountEl.style.display = 'block';
                    accountEl.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            }, 200);
        }
        """,
    )

    # ── Close position (hidden btn, triggered by position table JS)
    close_pos_btn.click(
        fn=_close_position_ui,
        inputs=[close_pos_input],
        outputs=[account_output, trace_output],
    )

    # ── Reset account ─────────────────────────────────────────────────
    reset_btn.click(
        fn=_reset_account_ui,
        inputs=[],
        outputs=[account_output, trace_output],
    )


# ════════════════════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════════════════════

TRADING_CSS = """
/* ===== Trading tab styles ===== */
#trading-desk-shell {
    max-width: 1380px;
    margin: 20px auto 36px;
    padding: 0;
}
.trading-window {
    background:
        linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.015)),
        var(--trading-card, #373c3f);
    border: 1px solid var(--trading-border, rgba(255,255,255,.14));
    border-radius: 18px;
    box-shadow: 0 24px 70px rgba(0,0,0,.28), 0 2px 8px rgba(0,0,0,.12);
    overflow: hidden;
}
.trading-window-header {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding: 22px 24px 18px;
    background: rgba(var(--theme-panel-rgb, 55, 60, 63), .88);
    border-bottom: 1px solid var(--trading-border, rgba(255,255,255,.14));
    backdrop-filter: blur(18px) saturate(160%);
    -webkit-backdrop-filter: blur(18px) saturate(160%);
}
.trading-window-header h1 {
    margin: 0 0 4px;
    color: var(--trading-text, rgba(255,255,255,.92));
    font-size: clamp(24px, 3vw, 34px);
    line-height: 1.08;
    letter-spacing: 0;
}
.trading-window-header p {
    margin: 0;
    color: var(--trading-secondary, rgba(255,255,255,.68));
    font-size: 14px;
}
.trading-window-badge {
    flex-shrink: 0;
    border: 1px solid rgba(55,199,138,.38);
    border-radius: 999px;
    padding: 7px 12px;
    background: rgba(55,199,138,.12);
    color: var(--trading-green, #37c78a);
    font-size: 12px;
    font-weight: 850;
    text-transform: uppercase;
}
.trading-workspace {
    gap: 0 !important;
}
.trading-control-panel {
    padding: 20px !important;
    border-right: 1px solid var(--trading-border, rgba(255,255,255,.14));
    background: rgba(0,0,0,.08);
}
.trading-main-panel {
    padding: 20px !important;
    min-width: 0;
}
.trading-action-panel {
    margin-top: 12px;
    padding: 16px;
    border: 1px solid var(--trading-amber, #dfab01);
    border-radius: 12px;
    background:
        linear-gradient(135deg, rgba(223,171,1,.12), rgba(28,160,241,.06)),
        var(--trading-card, #373c3f);
    box-shadow: 0 12px 30px rgba(0,0,0,.16);
}
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
#trading-account-summary {
    display: none;
}
@media (max-width: 920px) {
    #trading-desk-shell {
        margin: 12px 0 24px;
    }
    .trading-window {
        border-radius: 14px;
    }
    .trading-window-header {
        align-items: flex-start;
        flex-direction: column;
        padding: 18px;
    }
    .trading-control-panel {
        border-right: 0;
        border-bottom: 1px solid var(--trading-border, rgba(255,255,255,.14));
    }
    .trading-main-panel,
    .trading-control-panel {
        padding: 16px !important;
    }
}
"""
