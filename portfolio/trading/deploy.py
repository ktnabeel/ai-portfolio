"""Shared deployment helpers for the lean Trading Agent app."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from html import escape
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from market_story import (
    build_security_decision,
    fetch_sentiment_snapshot,
    render_sentiment_panel,
    render_technical_panel,
    sentiment_snapshot_from_dict,
    technical_snapshot_from_dict,
)

from .mcp.broker import close_position, get_account, reset_account
from .mcp.trading_server import MCPTradingServer


APP_TITLE = "AI Engineer Deployment"

LEAN_CSS = """
html, body {
  margin: 0;
  min-height: 100%;
  background:
    radial-gradient(circle at top left, rgba(37,99,235,.08), transparent 32%),
    radial-gradient(circle at top right, rgba(15,118,110,.06), transparent 24%),
    linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
  color: #101828;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
footer { display: none !important; }
.deploy-shell {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 18px 40px;
}
.deploy-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: end;
  padding: 22px 24px;
  margin-bottom: 18px;
  background: rgba(255,255,255,.88);
  border: 1px solid rgba(16,24,40,.08);
  border-radius: 18px;
  box-shadow: 0 20px 56px rgba(16,24,40,.08);
  backdrop-filter: blur(18px) saturate(160%);
}
.deploy-hero h1 {
  margin: 0 0 6px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.04;
  color: #101828;
}
.deploy-hero p {
  margin: 0;
  max-width: 80ch;
  color: #667085;
}
.deploy-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(37,99,235,.18);
  background: rgba(37,99,235,.08);
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.deploy-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 18px;
}
.deploy-panel {
  padding: 18px;
  background: rgba(255,255,255,.92);
  border: 1px solid rgba(16,24,40,.08);
  border-radius: 18px;
  box-shadow: 0 18px 44px rgba(16,24,40,.08);
}
.deploy-panel h2,
.deploy-panel h3 {
  margin-top: 0;
  color: #101828;
}
.market-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 18px;
}
.market-panel {
  min-height: 100%;
}
.market-score {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-size: 34px;
  line-height: 1;
  font-weight: 900;
  color: #101828;
}
.market-score span {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #667085;
}
.sentiment-mini-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.sentiment-mini-kpi, .tech-metric {
  border: 1px solid rgba(16,24,40,.06);
  border-radius: 16px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
}
.sentiment-mini-kpi .label, .tech-metric .label {
  display:block;
  font-size: 11px;
  color: #667085;
  text-transform: uppercase;
  letter-spacing: .08em;
  margin-bottom: 4px;
}
.sentiment-mini-kpi .value, .tech-metric .value {
  font-size: 16px;
  font-weight: 900;
  color: #101828;
}
.driver-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.driver-card {
  border-radius: 16px;
  border: 1px solid rgba(16,24,40,.06);
  padding: 12px 13px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  box-shadow: 0 10px 24px rgba(16,24,40,.04);
}
.driver-title {
  font-weight: 900;
  color: #101828;
  margin-bottom: 4px;
  line-height: 1.25;
}
.driver-summary {
  font-size: 13px;
  font-weight: 700;
  color: #101828;
  line-height: 1.45;
  margin-bottom: 4px;
}
.driver-detail {
  font-size: 13px;
  color: #667085;
  line-height: 1.5;
}
.tech-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.tech-chip-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.tech-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  border-radius: 999px;
  background: rgba(37,99,235,.08);
  color: #2563eb;
  border: 1px solid rgba(37,99,235,.14);
  font-size: 12px;
  font-weight: 800;
}
.decision-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(37,99,235,.18);
  background: rgba(37,99,235,.08);
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.reason-list {
  margin: 0;
  padding-left: 18px;
  color: #101828;
  line-height: 1.55;
}
.pipeline-shell {
  margin-bottom: 18px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(16,24,40,.08);
  background: linear-gradient(180deg, rgba(255,255,255,.94), rgba(248,250,252,.96));
  box-shadow: 0 18px 44px rgba(16,24,40,.06);
}
.pipeline-head {
  margin-bottom: 14px;
}
.pipeline-head .eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(37,99,235,.08);
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.pipeline-title {
  margin-top: 10px;
  font-size: clamp(20px, 2.4vw, 28px);
  line-height: 1.1;
  letter-spacing: -0.03em;
  font-weight: 900;
  color: #101828;
}
.pipeline-copy {
  margin-top: 8px;
  color: #667085;
  line-height: 1.5;
}
.pipeline-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.pipeline-card {
  border-radius: 16px;
  padding: 14px;
  border: 1px solid rgba(16,24,40,.10);
  background: #ffffff;
  box-shadow: 0 10px 26px rgba(16,24,40,.05);
  display: grid;
  gap: 8px;
  min-height: 160px;
}
.pipeline-icon {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 900;
  background: rgba(37,99,235,.08);
  color: #2563eb;
}
.pipeline-icon[data-accent="teal"] { background: rgba(15,118,110,.08); color: #0f766e; }
.pipeline-icon[data-accent="amber"] { background: rgba(180,83,9,.08); color: #b45309; }
.pipeline-icon[data-accent="violet"] { background: rgba(124,58,237,.08); color: #7c3aed; }
.pipeline-icon[data-accent="green"] { background: rgba(5,150,105,.08); color: #059669; }
.pipeline-icon[data-accent="slate"] { background: rgba(51,65,85,.08); color: #334155; }
.pipeline-name {
  font-size: 16px;
  font-weight: 900;
  color: #101828;
  line-height: 1.1;
}
.pipeline-summary {
  font-size: 13px;
  font-weight: 700;
  color: #101828;
  line-height: 1.4;
}
.pipeline-detail {
  font-size: 13px;
  color: #667085;
  line-height: 1.5;
}
.pipeline-status {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #667085;
}
.pipeline-legend {
  display:flex;
  flex-wrap:wrap;
  gap: 16px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(16,24,40,.08);
  color: #667085;
  font-size: 12px;
}
.pipeline-legend span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  display: inline-block;
}
.legend-dot.complete { background: #0f766e; }
.legend-dot.running { background: #2563eb; }
.legend-dot.review { background: #b45309; }
.legend-dot.pending { background: #94a3b8; }
.trace-expander {
  border-radius: 14px;
  border: 1px solid rgba(16,24,40,.08);
  padding: 12px 12px 10px;
  background: linear-gradient(180deg, #fff, #f8fafc);
  box-shadow: 0 10px 24px rgba(16,24,40,.04);
}
.trace-expander summary {
  cursor: pointer;
  list-style: none;
  font-weight: 900;
  color: #101828;
}
.trace-expander summary::-webkit-details-marker {
  display: none;
}
.trace-expander .trace-copy {
  margin-top: 8px;
  color: #667085;
  line-height: 1.5;
  font-size: 13px;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0 18px;
}
.workflow-card {
  padding: 12px 12px 11px;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  border: 1px solid rgba(16,24,40,.06);
  box-shadow: 0 10px 24px rgba(16,24,40,.04);
}
.workflow-card .topline {
  display:flex;
  align-items:center;
  gap:8px;
  margin-bottom:6px;
}
.workflow-card .bubble {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display:flex;
  align-items:center;
  justify-content:center;
  background: rgba(37,99,235,.08);
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}
.workflow-card .label {
  display:block;
  color: #101828;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: none;
  margin-bottom: 0;
}
.workflow-card .value {
  font-size: 12px;
  font-weight: 500;
  color: #667085;
  line-height: 1.4;
}
.agent-card {
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid rgba(16,24,40,.06);
}
.agent-card .label {
  display: block;
  color: #667085;
  font-size: 11px;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.agent-card .value {
  font-size: 15px;
  font-weight: 800;
  color: #101828;
}
.deploy-kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0;
}
.deploy-kpi {
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid rgba(16,24,40,.06);
}
.deploy-kpi .label {
  display: block;
  color: #667085;
  font-size: 11px;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.deploy-kpi .value {
  font-size: 18px;
  font-weight: 800;
  color: #101828;
}
.deploy-form {
  display: grid;
  gap: 10px;
}
.deploy-form input,
.deploy-form select,
.deploy-form button,
.deploy-form textarea {
  width: 100%;
  box-sizing: border-box;
  border-radius: 12px;
  border: 1px solid rgba(16,24,40,.10);
  background: #ffffff;
  color: #101828;
  padding: 10px 12px;
}
.deploy-form button {
  cursor: pointer;
  font-weight: 800;
  background: linear-gradient(135deg, rgba(37,99,235,.92), rgba(13,148,136,.92));
  color: #ffffff;
  border-color: transparent;
}
.deploy-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.deploy-table th,
.deploy-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(16,24,40,.08);
  vertical-align: top;
  text-align: left;
}
.deploy-table th {
  color: #667085;
  font-size: 11px;
  letter-spacing: .05em;
  text-transform: uppercase;
}
@media (max-width: 960px) {
  .market-grid {
    grid-template-columns: 1fr;
  }
  .deploy-grid, .deploy-hero {
    grid-template-columns: 1fr;
  }
}
"""


def runtime_mode() -> str:
    mode = os.getenv("TRADING_DEPLOY_RUNTIME", "").strip().lower()
    if mode in {"gradio", "fastapi"}:
        return mode
    return "fastapi" if os.getenv("VERCEL") else "gradio"


def _money(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}${value:,.2f}"


def render_market_context_html(symbol: str = "AAPL") -> str:
    sentiment = fetch_sentiment_snapshot()
    decision = build_security_decision(symbol, sentiment)
    return f"""
    <div class="market-grid">
      {render_sentiment_panel(sentiment)}
      {render_technical_panel(decision)}
    </div>
    """


def render_agent_overview_html() -> str:
    return """
    <div class="pipeline-shell">
      <div class="pipeline-head">
        <div class="eyebrow">Agent Pipeline Flow</div>
        <div class="pipeline-title">LangGraph orchestration with visible decision traces</div>
        <div class="pipeline-copy">The interface prioritizes agent reasoning, deep dives, and human review. Execution stays present, but it is visually secondary to the decision chain.</div>
      </div>
      <div class="pipeline-grid">
        <article class="pipeline-card">
          <div class="pipeline-icon" data-accent="blue">🔎</div>
          <div class="pipeline-name">Security Agent</div>
          <div class="pipeline-summary">Validate and sanitize the target.</div>
          <div class="pipeline-detail">Checks input hygiene, policy guardrails, and target readiness before the rest of the workflow proceeds.</div>
          <details class="trace-expander">
            <summary>Deep dive</summary>
            <div class="trace-copy">Rejects malformed symbols early and keeps the review surface clean.</div>
          </details>
          <div class="pipeline-status">Complete</div>
        </article>
        <article class="pipeline-card">
          <div class="pipeline-icon" data-accent="teal">🧭</div>
          <div class="pipeline-name">Risk &amp; Sentiment</div>
          <div class="pipeline-summary">Blend signal tone, noise, and news.</div>
          <div class="pipeline-detail">Combines lightweight sentiment and recent context to form a usable directional read.</div>
          <details class="trace-expander">
            <summary>Deep dive</summary>
            <div class="trace-copy">The agent compresses multiple context clues into one concise score.</div>
          </details>
          <div class="pipeline-status">Complete</div>
        </article>
        <article class="pipeline-card">
          <div class="pipeline-icon" data-accent="amber">🔁</div>
          <div class="pipeline-name">Regime Detection</div>
          <div class="pipeline-summary">Classify the market context.</div>
          <div class="pipeline-detail">Filters the setup through a bull, bear, or neutral gate so the recommendation stays grounded.</div>
          <details class="trace-expander">
            <summary>Deep dive</summary>
            <div class="trace-copy">This is where the workflow decides whether the environment supports a trade at all.</div>
          </details>
          <div class="pipeline-status">Complete</div>
        </article>
        <article class="pipeline-card">
          <div class="pipeline-icon" data-accent="violet">📊</div>
          <div class="pipeline-name">Options Chain</div>
          <div class="pipeline-summary">Surface the nearby contract map.</div>
          <div class="pipeline-detail">Puts the actionable range in view before any decision is drafted or approved.</div>
          <details class="trace-expander">
            <summary>Deep dive</summary>
            <div class="trace-copy">Useful for seeing where the workflow would route if the target passes review.</div>
          </details>
          <div class="pipeline-status">Complete</div>
        </article>
        <article class="pipeline-card">
          <div class="pipeline-icon" data-accent="green">🎯</div>
          <div class="pipeline-name">Decision Agent</div>
          <div class="pipeline-summary">Choose buy or sell and explain why.</div>
          <div class="pipeline-detail">Produces the recommendation that human review can approve, reject, or route onward.</div>
          <details class="trace-expander">
            <summary>Deep dive</summary>
            <div class="trace-copy">This is the step users inspect before they ever reach execution.</div>
          </details>
          <div class="pipeline-status">Running</div>
        </article>
        <article class="pipeline-card">
          <div class="pipeline-icon" data-accent="slate">💸</div>
          <div class="pipeline-name">Execution Agent</div>
          <div class="pipeline-summary">Route the simulated paper trade.</div>
          <div class="pipeline-detail">Keeps the broker action visible but secondary to the reasoning and approval flow.</div>
          <details class="trace-expander">
            <summary>Deep dive</summary>
            <div class="trace-copy">The final route only happens after human approval is captured.</div>
          </details>
          <div class="pipeline-status">Pending</div>
        </article>
      </div>
      <div class="pipeline-legend">
        <span><i class="legend-dot complete"></i>Complete</span>
        <span><i class="legend-dot running"></i>Running</span>
        <span><i class="legend-dot review"></i>Awaiting approval</span>
        <span><i class="legend-dot pending"></i>Pending</span>
      </div>
    </div>
    """


def render_market_story_html(symbol: str = "AAPL") -> str:
    return render_market_context_html(symbol)


def account_snapshot() -> dict[str, Any]:
    account = get_account()
    return {
        "cash": round(account.cash, 2),
        "total_equity": round(account.total_equity, 2),
        "total_pnl": round(account.total_pnl, 2),
        "realized_pnl": round(account.realized_pnl, 2),
        "unrealized_pnl": round(account.unrealized_pnl, 2),
        "total_commission": round(account.total_commission, 2),
        "position_count": len(account.positions),
        "order_count": len(account.order_history),
        "positions": [
            {
                "position_id": p.position_id,
                "symbol": p.symbol,
                "strategy": p.strategy,
                "option_type": p.option_type,
                "strike": p.strike,
                "expiration": p.expiration,
                "quantity": p.quantity,
                "entry_price": round(p.entry_price, 2),
                "market_value": round(p.market_value, 2),
                "unrealized_pnl": round(p.unrealized_pnl, 2),
            }
            for p in account.positions
        ],
        "order_history": [
            {
                "order_id": o.order_id,
                "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                "filled_price": round(o.filled_price, 2) if o.filled_price is not None else None,
                "filled_quantity": o.filled_quantity,
                "commission": round(o.commission, 2),
                "total_cost": round(o.total_cost, 2) if o.total_cost is not None else None,
                "timestamp": o.timestamp.isoformat() if o.timestamp else None,
                "notes": o.notes,
            }
            for o in reversed(account.order_history[-15:])
        ],
        "rejections": [
            {
                "rejection_id": r.rejection_id,
                "symbol": r.symbol,
                "strategy": r.strategy,
                "reason": r.reason,
                "rejected_at": r.rejected_at.isoformat(),
                "notes": r.notes,
            }
            for r in reversed(account.rejection_history[-15:])
        ],
    }


def render_account_summary_html() -> str:
    account = get_account()
    positions_rows = ""
    for pos in account.positions:
        positions_rows += f"""
        <tr>
            <td>{escape(pos.symbol)}</td>
            <td>{escape(pos.strategy)}</td>
            <td>{escape(pos.option_type)}</td>
            <td>${pos.strike:,.2f}</td>
            <td>{escape(pos.expiration[:10] if pos.expiration else "-")}</td>
            <td>{pos.quantity}</td>
            <td>${pos.entry_price:,.2f}</td>
            <td style="color:{'#7ff0ba' if pos.unrealized_pnl >= 0 else '#ff8e80'}">{_money(pos.unrealized_pnl)}</td>
        </tr>
        """

    if not positions_rows:
        positions_rows = '<tr><td colspan="8" style="color:rgba(255,255,255,.6); font-style:italic;">No open positions.</td></tr>'

    orders_rows = ""
    for order in account.order_history[-10:][::-1]:
        orders_rows += f"""
        <tr>
            <td>{escape(order.order_id)}</td>
            <td>{escape(order.status.value if hasattr(order.status, "value") else str(order.status))}</td>
            <td>{order.filled_quantity}</td>
            <td>{'' if order.filled_price is None else f'${order.filled_price:,.2f}'}</td>
            <td>{'' if order.total_cost is None else f'${order.total_cost:,.2f}'}</td>
            <td>{escape(order.notes or '')}</td>
        </tr>
        """
    if not orders_rows:
        orders_rows = '<tr><td colspan="6" style="color:rgba(255,255,255,.6); font-style:italic;">No orders yet.</td></tr>'

    rejections_rows = ""
    for rejection in account.rejection_history[-10:][::-1]:
        rejections_rows += f"""
        <tr>
            <td>{escape(rejection.rejected_at.strftime("%m/%d %H:%M"))}</td>
            <td>{escape(rejection.symbol)}</td>
            <td>{escape(rejection.strategy)}</td>
            <td>{escape(rejection.reason)}</td>
        </tr>
        """
    if not rejections_rows:
        rejections_rows = '<tr><td colspan="4" style="color:rgba(255,255,255,.6); font-style:italic;">No rejections yet.</td></tr>'

    return f"""
    <div class="deploy-panel">
      <h2>System Snapshot</h2>
      <div class="deploy-kpi-grid">
        <div class="deploy-kpi"><span class="label">Cash</span><span class="value">{_money(account.cash)}</span></div>
        <div class="deploy-kpi"><span class="label">Total Equity</span><span class="value">{_money(account.total_equity)}</span></div>
        <div class="deploy-kpi"><span class="label">Total P&amp;L</span><span class="value">{_money(account.total_pnl)}</span></div>
        <div class="deploy-kpi"><span class="label">Positions</span><span class="value">{len(account.positions)}</span></div>
      </div>

      <h3>Active Runs</h3>
      <div style="overflow:auto; margin-bottom:18px;">
        <table class="deploy-table">
          <thead>
            <tr><th>Target</th><th>Plan</th><th>Variant</th><th>Ref</th><th>Date</th><th>Count</th><th>Entry</th><th>Delta</th></tr>
          </thead>
          <tbody>{positions_rows}</tbody>
        </table>
      </div>

      <h3>Recent Actions</h3>
      <div style="overflow:auto; margin-bottom:18px;">
        <table class="deploy-table">
          <thead>
            <tr><th>Action</th><th>Status</th><th>Qty</th><th>Fill</th><th>Total</th><th>Notes</th></tr>
          </thead>
          <tbody>{orders_rows}</tbody>
        </table>
      </div>

      <h3>Recent Rejections</h3>
      <div style="overflow:auto;">
        <table class="deploy-table">
          <thead>
            <tr><th>Time</th><th>Symbol</th><th>Strategy</th><th>Reason</th></tr>
          </thead>
          <tbody>{rejections_rows}</tbody>
        </table>
      </div>
    </div>
    """


def render_home_html() -> str:
    account_html = render_account_summary_html()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{APP_TITLE}</title>
  <style>{LEAN_CSS}</style>
</head>
<body>
  <div class="deploy-shell">
    <section class="deploy-hero">
      <div>
        <div class="deploy-pill">AI Engineer</div>
        <h1>Agent decisions first. Execution second.</h1>
        <p>A clean workflow showing how the agents reason, how each trace expands, and how human review gates any simulated broker action.</p>
      </div>
      <div class="deploy-pill">{runtime_mode()}</div>
    </section>

    <div class="deploy-grid">
      <section class="deploy-panel">
        <h2>Workflow</h2>
        {render_agent_overview_html()}
        <h3>Live Market Context</h3>
        <p style="margin-top:-6px; color:#667085; line-height:1.5;">CNN Fear &amp; Greed and the chart read update here so the approval step has a visible market backstop.</p>
        {render_market_context_html()}
        <h3>Human Review</h3>
        <p style="margin-top:-6px; color:#667085; line-height:1.5;">Use the controls below only after you inspect the agent trace rail. The execution controls remain small on purpose.</p>
        <form class="deploy-form" method="post" action="/api/place-order">
          <input name="symbol" placeholder="Target, e.g. AAPL" value="AAPL" />
          <select name="strategy">
            <option>Plan A</option>
            <option>Plan B</option>
            <option>Plan C</option>
            <option>No Run</option>
          </select>
          <input name="option_type" placeholder="Variant, e.g. call" value="call" />
          <input name="strike" placeholder="Reference" type="number" step="0.01" value="150" />
          <input name="expiration" placeholder="Run date YYYY-MM-DD" value="" />
          <input name="quantity" placeholder="Count" type="number" step="1" value="1" />
          <input name="limit_price" placeholder="Threshold" type="number" step="0.01" value="" />
          <button type="submit">Run Simulation</button>
        </form>

        <div style="margin-top:18px;">
          <form class="deploy-form" method="post" action="/api/reset">
            <button type="submit" style="background: rgba(255,255,255,.08);">Reset State</button>
          </form>
        </div>

        <div style="margin-top:18px;">
          <form class="deploy-form" method="post" action="/api/close">
            <input name="position_id" placeholder="Run ID to resolve" />
            <input name="exit_price" placeholder="Exit value (optional)" type="number" step="0.01" />
            <button type="submit" style="background: rgba(255,255,255,.08);">Resolve Run</button>
          </form>
        </div>
      </section>
      <section>
        {account_html}
      </section>
    </div>
  </div>
</body>
</html>"""


def _mcp_server() -> MCPTradingServer:
    return MCPTradingServer()


def place_order_via_mcp(
    symbol: str,
    strategy: str,
    option_type: str = "",
    strike: float | None = None,
    expiration: str = "",
    quantity: int = 1,
    limit_price: float | None = None,
) -> dict[str, Any]:
    server = _mcp_server()
    response = server.call_tool("place_option_order", {
        "symbol": symbol,
        "strategy": strategy,
        "option_type": option_type,
        "strike": strike,
        "expiration": expiration,
        "quantity": quantity,
        "limit_price": limit_price,
    })
    if response.success:
        return response.data
    return {"success": False, "error": response.error}


def reset_via_mcp() -> dict[str, Any]:
    server = _mcp_server()
    response = server.call_tool("reset_account", {})
    return response.data if response.success else {"success": False, "error": response.error}


def close_via_mcp(position_id: str, exit_price: float | None = None) -> dict[str, Any]:
    server = _mcp_server()
    response = server.call_tool("close_position", {
        "position_id": position_id,
        "exit_price": exit_price,
    })
    return response.data if response.success else {"success": False, "error": response.error}


def _blank_to_none(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def build_gradio_app():
    import gradio as gr

    def _refresh_account() -> tuple[str, str]:
        return render_account_summary_html(), ""

    def _place_order(
        symbol: str,
        strategy: str,
        option_type: str,
        strike: str,
        expiration: str,
        quantity: int,
        limit_price: str,
    ) -> tuple[str, str]:
        result = place_order_via_mcp(
            symbol.strip().upper(),
            strategy,
            option_type.strip().lower(),
            _blank_to_none(strike),
            expiration.strip(),
            quantity,
            _blank_to_none(limit_price),
        )
        if not result.get("success", True):
            return (
                render_account_summary_html(),
                f"<div style='color:#ff8e80;'>Order failed: {escape(str(result.get('error', 'Unknown error')))}</div>",
            )
        return (
            render_account_summary_html(),
            f"<div style='color:#7ff0ba;'>Order submitted: {escape(str(result.get('status', 'OK')))}</div>",
        )

    def _reset() -> tuple[str, str]:
        reset_via_mcp()
        return render_account_summary_html(), "<div style='color:#7ff0ba;'>Account reset.</div>"

    def _close(position_id: str, exit_price: str) -> tuple[str, str]:
        pid = position_id.strip()
        if not pid:
            return render_account_summary_html(), "<div style='color:#ff8e80;'>Position ID is required.</div>"
        result = close_via_mcp(pid, _blank_to_none(exit_price))
        if not result.get("success", True):
            return (
                render_account_summary_html(),
                f"<div style='color:#ff8e80;'>Close failed: {escape(str(result.get('error', 'Unknown error')))}</div>",
            )
        return (
            render_account_summary_html(),
            f"<div style='color:#7ff0ba;'>Position closed: {escape(str(result.get('trade_id', 'OK')))}</div>",
        )

    with gr.Blocks(title=APP_TITLE, css=LEAN_CSS, theme=gr.themes.Soft()) as demo:
        with gr.Column(elem_id="deploy-root", elem_classes=["deploy-shell"]):
            gr.HTML(
                f"""
                <section class="deploy-hero">
                  <div>
                    <div class="deploy-pill">AI Engineer</div>
                    <h1>Agent decisions first. Execution second.</h1>
                    <p>A light-theme workflow that keeps the agent reasoning visible and the execution controls intentionally secondary.</p>
                  </div>
                  <div class="deploy-pill">{runtime_mode()}</div>
                </section>
                """
            )

            with gr.Row():
                with gr.Column(scale=1, min_width=340):
                    gr.Markdown("### Workflow")
                    symbol = gr.Textbox(label="Target", value="AAPL")
                    gr.HTML(render_agent_overview_html())

                    gr.Markdown("### Live Market Context")
                    market_output = gr.HTML(render_market_context_html())
                    refresh_market_btn = gr.Button("Refresh Market Story")

                    gr.Markdown("### Human Review")
                    strategy = gr.Dropdown(["Plan A", "Plan B", "Plan C", "No Run"], value="Plan A", label="Plan")
                    option_type = gr.Dropdown(["call", "put"], value="call", label="Variant")
                    strike = gr.Textbox(label="Reference", value="150")
                    expiration = gr.Textbox(label="Run Date", placeholder="YYYY-MM-DD")
                    quantity = gr.Number(label="Count", value=1, precision=0)
                    limit_price = gr.Textbox(label="Threshold", placeholder="Optional")
                    place_btn = gr.Button("Run Simulation", variant="primary")

                    gr.Markdown("### Resolve")
                    position_id = gr.Textbox(label="Run ID", placeholder="RUN-...")
                    exit_price = gr.Textbox(label="Exit Value", placeholder="Optional")
                    close_btn = gr.Button("Resolve Run")

                    reset_btn = gr.Button("Reset State")
                    action_status = gr.HTML("")

                with gr.Column(scale=2, min_width=500):
                    account_output = gr.HTML(render_account_summary_html())
                    refresh_btn = gr.Button("Refresh State")

            place_btn.click(
                fn=_place_order,
                inputs=[symbol, strategy, option_type, strike, expiration, quantity, limit_price],
                outputs=[account_output, action_status],
            )
            refresh_market_btn.click(
                fn=render_market_context_html,
                inputs=[symbol],
                outputs=[market_output],
            )
            close_btn.click(
                fn=_close,
                inputs=[position_id, exit_price],
                outputs=[account_output, action_status],
            )
            reset_btn.click(
                fn=_reset,
                inputs=[],
                outputs=[account_output, action_status],
            )
            refresh_btn.click(
                fn=_refresh_account,
                inputs=[],
                outputs=[account_output, action_status],
            )
    return demo


def create_fastapi_app() -> FastAPI:
    app = FastAPI(
        title=APP_TITLE,
        description="Lean Trading Agent deployment with MCP-backed simulated broker actions.",
        version="0.1.0",
    )

    @app.get("/", response_class=HTMLResponse)
    async def index(_: Request) -> HTMLResponse:
        return HTMLResponse(render_home_html())

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "healthy",
            "runtime": "fastapi",
            "mode": runtime_mode(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/account")
    async def api_account() -> dict[str, Any]:
        return account_snapshot()

    @app.get("/api/orders")
    async def api_orders(limit: int = 15) -> dict[str, Any]:
        snapshot = account_snapshot()
        orders = snapshot["order_history"][:limit]
        return {"orders": orders, "total_orders": len(snapshot["order_history"])}

    @app.post("/api/place-order", response_model=None)
    async def api_place_order(
        symbol: str = Form(default="AAPL"),
        strategy: str = Form(default="Call"),
        option_type: str = Form(default="call"),
        strike: str | None = Form(default=""),
        expiration: str = Form(default=""),
        quantity: int = Form(default=1),
        limit_price: str | None = Form(default=""),
    ) -> HTMLResponse | JSONResponse:
        result = place_order_via_mcp(
            symbol,
            strategy,
            option_type,
            _blank_to_none(strike),
            expiration,
            quantity,
            _blank_to_none(limit_price),
        )
        if not result.get("success", True):
            return JSONResponse(status_code=400, content=result)
        return HTMLResponse(render_home_html())

    @app.post("/api/reset")
    async def api_reset() -> HTMLResponse:
        reset_via_mcp()
        return HTMLResponse(render_home_html())

    @app.post("/api/close", response_model=None)
    async def api_close(
        position_id: str = Form(default=""),
        exit_price: str | None = Form(default=""),
    ) -> HTMLResponse | JSONResponse:
        if not position_id.strip():
            return JSONResponse(status_code=400, content={"success": False, "error": "position_id is required"})
        result = close_via_mcp(position_id.strip(), _blank_to_none(exit_price))
        if not result.get("success", True):
            return JSONResponse(status_code=400, content=result)
        return HTMLResponse(render_home_html())

    return app


def build_runtime_app() -> tuple[str, Any]:
    mode = runtime_mode()
    if mode == "fastapi":
        return mode, create_fastapi_app()
    return mode, build_gradio_app()
