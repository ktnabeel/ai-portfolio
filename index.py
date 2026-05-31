"""Vercel FastAPI entrypoint for the workflow demo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape
from uuid import uuid4

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse

from market_story import (
    build_security_decision,
    fetch_sentiment_snapshot,
    sentiment_snapshot_from_dict,
    technical_snapshot_from_dict,
    render_sentiment_panel,
    render_technical_panel,
)


APP_TITLE = "Workflow Lab"
STAGES = ("analyze", "review", "execute", "done")
PIPELINE_STEPS = (
    ("Security Agent", "Validate the target and technical setup.", "S", "blue"),
    ("Risk & Sentiment", "Fuse CNN Fear & Greed and risk context.", "R", "teal"),
    ("Regime Detection", "Classify EMA 8/21, range, and volume.", "G", "amber"),
    ("Options Chain", "Keep the contract landscape available.", "O", "violet"),
    ("Decision Agent", "Select buy or sell and explain the thesis.", "D", "green"),
    ("Execution Agent", "Route the simulated trade after review.", "E", "slate"),
)


@dataclass(slots=True)
class TraceCard:
    title: str
    status: str
    summary: str
    detail: str
    accent: str = "blue"


@dataclass(slots=True)
class Order:
    order_id: str
    symbol: str
    side: str
    status: str
    fill_price: float | None = None
    quantity: int = 0
    cash_flow: float = 0.0
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(slots=True)
class Position:
    position_id: str
    symbol: str
    side: str
    quantity: int
    entry_price: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def signed_value(self) -> float:
        direction = 1.0 if self.side == "BUY" else -1.0
        return direction * self.entry_price * self.quantity * 100

    @property
    def pnl(self) -> float:
        return 0.0


@dataclass(slots=True)
class Account:
    cash: float = 100_000.0
    positions: list[Position] = field(default_factory=list)
    order_history: list[Order] = field(default_factory=list)
    realized_pnl: float = 0.0
    total_commission: float = 0.0

    @property
    def total_equity(self) -> float:
        return self.cash + sum(p.signed_value for p in self.positions)

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.pnl for p in self.positions)

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl - self.total_commission


@dataclass(slots=True)
class WorkflowState:
    symbol: str
    side: str
    confidence: float
    thesis: str
    traces: list[TraceCard]
    sentiment: dict[str, object] = field(default_factory=dict)
    technical: dict[str, object] = field(default_factory=dict)
    analysis_id: str = field(default_factory=lambda: f"ANL-{uuid4().hex[:8].upper()}")
    approval_note: str = ""
    review_status: str = ""
    order_id: str = ""
    order_status: str = ""
    execution_note: str = ""

    def to_payload(self) -> str:
        return json.dumps(
            {
                "symbol": self.symbol,
                "side": self.side,
                "confidence": self.confidence,
                "thesis": self.thesis,
                "traces": [asdict(t) for t in self.traces],
                "sentiment": self.sentiment,
                "technical": self.technical,
                "analysis_id": self.analysis_id,
                "approval_note": self.approval_note,
                "review_status": self.review_status,
                "order_id": self.order_id,
                "order_status": self.order_status,
                "execution_note": self.execution_note,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_payload(cls, payload: str) -> "WorkflowState":
        raw = json.loads(payload)
        traces = [TraceCard(**t) for t in raw.get("traces", [])]
        return cls(
            symbol=raw.get("symbol", "AAPL"),
            side=raw.get("side", "BUY"),
            confidence=float(raw.get("confidence", 0.0)),
            thesis=raw.get("thesis", ""),
            traces=traces,
            sentiment=dict(raw.get("sentiment", {})),
            technical=dict(raw.get("technical", {})),
            analysis_id=raw.get("analysis_id", f"ANL-{uuid4().hex[:8].upper()}"),
            approval_note=raw.get("approval_note", ""),
            review_status=raw.get("review_status", ""),
            order_id=raw.get("order_id", ""),
            order_status=raw.get("order_status", ""),
            execution_note=raw.get("execution_note", ""),
        )


_ACCOUNT = Account()


def _money(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}${value:,.2f}"


def _clean_symbol(symbol: str) -> str:
    cleaned = "".join(ch for ch in symbol.upper().strip() if ch.isalnum() or ch in {".", "-"})
    return cleaned[:8] or "AAPL"


def _decision_for(symbol: str) -> tuple[str, float, str]:
    score = sum(ord(c) for c in symbol)
    side = "BUY" if score % 2 == 0 else "SELL"
    confidence = 0.74 + ((score % 17) / 100)
    thesis = "Momentum and context are aligned" if side == "BUY" else "Risk/reversion setup is stronger"
    return side, round(min(confidence, 0.93), 2), thesis


def _build_analysis(symbol: str) -> WorkflowState:
    symbol = _clean_symbol(symbol)
    decision = build_security_decision(symbol)
    sentiment = decision.sentiment.to_dict() if decision.sentiment else {}
    technical = decision.technical.to_dict() if decision.technical else {}
    sentiment_zone = sentiment.get("zone", "Neutral")
    technical_signal = technical.get("signal", "Mixed / sideways")
    traces = [
        TraceCard(
            title="Security Agent",
            status="complete",
            summary=decision.reasons[0] if decision.reasons else f"Validated {symbol} as a reviewable target.",
            detail=decision.rationale,
            accent="blue",
        ),
        TraceCard(
            title="Risk & Sentiment",
            status="complete",
            summary=f"CNN Fear & Greed: {sentiment.get('value', 50)}/100 ({sentiment_zone}).",
            detail=_sentiment_trace_detail(sentiment),
            accent="teal",
        ),
        TraceCard(
            title="Regime Detection",
            status="complete",
            summary=f"Technical regime: {technical_signal}.",
            detail=_technical_trace_detail(technical),
            accent="amber",
        ),
        TraceCard(
            title="Options Chain",
            status="complete",
            summary=f"Decision side: {decision.side} with hybrid confirmation.",
            detail="The workflow keeps the options leg visible, but the current page focuses on the signal that leads to approval.",
            accent="violet",
        ),
        TraceCard(
            title="Decision Agent",
            status="complete",
            summary=f"Recommend {decision.side}.",
            detail=(
                f"Confidence {decision.confidence:.0%}. Thesis: {decision.thesis}. "
                f"EMA 8/21 and breakout rationale: {decision.rationale}"
            ),
            accent="green",
        ),
    ]
    return WorkflowState(
        symbol=symbol,
        side=decision.side,
        confidence=decision.confidence,
        thesis=decision.thesis,
        traces=traces,
        sentiment=sentiment,
        technical=technical,
    )


def _estimate_fill(symbol: str, side: str) -> float:
    seed = sum(ord(c) for c in symbol)
    base = 3.15 if side == "BUY" else 3.05
    return round(base + ((seed % 9) * 0.11), 2)


def _execute_trade(state: WorkflowState) -> WorkflowState:
    fill = _estimate_fill(state.symbol, state.side)
    order_id = f"ORD-{uuid4().hex[:8].upper()}"
    qty = 1
    flow = round(fill * qty * 100 + 0.65, 2)
    cash_flow = -flow if state.side == "BUY" else flow
    position = Position(
        position_id=f"POS-{uuid4().hex[:8].upper()}",
        symbol=state.symbol,
        side=state.side,
        quantity=qty,
        entry_price=fill,
    )
    _ACCOUNT.cash += cash_flow
    _ACCOUNT.total_commission += 0.65
    _ACCOUNT.positions.append(position)
    _ACCOUNT.order_history.append(
        Order(
            order_id=order_id,
            symbol=state.symbol,
            side=state.side,
            status="Filled",
            fill_price=fill,
            quantity=qty,
            cash_flow=cash_flow,
            notes=f"{state.side} executed via simulated broker.",
        )
    )
    state.order_id = order_id
    state.order_status = "Filled"
    state.execution_note = f"{state.side} routed at ${fill:.2f} with trade ID {order_id}."
    state.traces = [
        *state.traces,
        TraceCard(
            title="Execution Agent",
            status="complete",
            summary=f"{state.side} routed successfully.",
            detail=f"Filled at ${fill:.2f} with a simulated cash flow of {_money(cash_flow)}.",
            accent="green",
        ),
        TraceCard(
            title="Ledger",
            status="complete",
            summary=f"Account updated. Cash now {_money(_ACCOUNT.cash)}.",
            detail=f"Position {position.position_id} added to the stateful ledger.",
            accent="blue",
        ),
    ]
    return state


def _sentiment_trace_detail(sentiment: dict[str, object]) -> str:
    if not sentiment:
        return "CNN Fear & Greed unavailable; the agent uses a neutral fallback."
    comparisons = [
        ("previous close", sentiment.get("previous_close")),
        ("one week ago", sentiment.get("one_week_ago")),
        ("one month ago", sentiment.get("one_month_ago")),
        ("one year ago", sentiment.get("one_year_ago")),
    ]
    comparison_text = ", ".join(f"{label}: {value}" for label, value in comparisons if value is not None)
    drivers = []
    for driver in sentiment.get("drivers", []) or []:
        if isinstance(driver, dict):
            drivers.append(f"{driver.get('title', 'Driver')}: {driver.get('summary', '')} {driver.get('detail', '')}".strip())
    driver_text = " | Drivers: " + " ; ".join(drivers) if drivers else ""
    return (
        f"CNN Fear & Greed score {sentiment.get('value', 50)}/100 in the {sentiment.get('zone', 'Neutral')} zone. "
        f"{sentiment.get('description', '')} Comparisons: {comparison_text or 'not available'}.{driver_text}"
    )


def _technical_trace_detail(technical: dict[str, object]) -> str:
    if not technical:
        return "EMA 8/21 and breakout data unavailable; the agent holds a neutral technical read."
    flags = []
    if technical.get("bullish_stack"):
        flags.append("price is above EMA 8 and EMA 21")
    if technical.get("bearish_stack"):
        flags.append("price is below EMA 8 and EMA 21")
    if technical.get("breakout_up"):
        flags.append("breakout above the 20-day high")
    if technical.get("breakdown"):
        flags.append("breakdown below the 20-day low")
    if technical.get("volume_surge"):
        flags.append("volume confirmation is present")
    return (
        f"EMA 8/21: EMA 8 ${float(technical.get('ema_8', 0.0)):.2f}, "
        f"EMA 21 ${float(technical.get('ema_21', 0.0)):.2f}, current price ${float(technical.get('current_price', 0.0)):.2f}. "
        f"Breakout rationale: {technical.get('summary', 'No range summary available')} "
        f"Signals: {', '.join(flags) if flags else 'mixed trend with no confirmed breakout'}."
    )


def _pipeline_status(stage: str, index: int, title: str, state: WorkflowState | None) -> str:
    if state is None:
        return "running" if index == 0 else "pending"
    if title == "Execution Agent":
        if state.order_id:
            return "complete"
        if state.review_status == "approved":
            return "running"
        return "pending"
    return "complete"


def _pipeline_html(stage: str, state: WorkflowState | None) -> str:
    trace_by_title = {trace.title: trace for trace in (state.traces if state else [])}
    steps = list(PIPELINE_STEPS)
    if state is not None:
        steps.insert(5, ("Human Review", "Approve or reject the recommendation.", "H", "amber"))
    cards = []
    for idx, (title, subtitle, icon, accent) in enumerate(steps):
        trace = trace_by_title.get(title)
        status = "pending"
        summary = trace.summary if trace else subtitle
        detail = trace.detail if trace else subtitle
        if title == "Human Review":
            if state.review_status == "approved":
                status, summary, detail = "complete", "Approved", state.approval_note or "Human review approved the recommendation."
            elif state.review_status == "rejected":
                status, summary, detail = "rejected", "Rejected", state.approval_note or "Human review rejected the recommendation."
            else:
                status, summary, detail = "awaiting", "Awaiting Approval", "Human review is required before the Execution Agent can expand."
        else:
            status = _pipeline_status(stage, idx, title, state)
        status_label = {
            "awaiting": "Awaiting Approval",
            "rejected": "Rejected",
        }.get(status, status.replace("_", " ").title())
        cards.append(
            f"""
            <article class="pipeline-card {status}" id="node-{idx}">
              <div class="pipeline-icon" data-accent="{accent}">{icon}</div>
              <div class="pipeline-name">{escape(title)}</div>
              <div class="pipeline-summary">{escape(summary)}</div>
              <div class="pipeline-detail">{escape(detail)}</div>
              <div class="pipeline-status">{escape(status_label)}</div>
            </article>
            """
        )
    return f"""
    <section class="pipeline-shell">
      <div class="pipeline-head">
        <div>
          <div class="eyebrow">Agent Pipeline Flow</div>
          <div class="pipeline-title">Inspectable agent graph</div>
        </div>
      </div>
      <div class="pipeline-grid">
        {''.join(cards)}
      </div>
      <div class="pipeline-legend">
        <span><i class="legend-dot complete"></i>Complete</span>
        <span><i class="legend-dot running"></i>Running</span>
        <span><i class="legend-dot review"></i>Awaiting approval</span>
        <span><i class="legend-dot rejected"></i>Rejected</span>
        <span><i class="legend-dot pending"></i>Pending</span>
      </div>
    </section>
    """


def _trace_cards(traces: list[TraceCard]) -> str:
    palette = {
        "blue": ("#2563eb", "#eff6ff"),
        "teal": ("#0f766e", "#ecfdf5"),
        "amber": ("#b45309", "#fffbeb"),
        "violet": ("#7c3aed", "#f5f3ff"),
        "green": ("#059669", "#ecfdf3"),
        "slate": ("#475569", "#f8fafc"),
    }
    if not traces:
        return """
        <div class="trace-empty">
          <div class="trace-empty-kicker">Deep dive</div>
          <div class="trace-empty-title">Run analysis to inspect each agent.</div>
          <div class="trace-empty-copy">Security, sentiment, regime, options, decision, and execution traces will expand here.</div>
        </div>"""
    blocks = []
    for trace in traces:
        color, bg = palette.get(trace.accent, ("#2563eb", "#eff6ff"))
        blocks.append(
            f"""
            <details class="trace-card" style="border-color:{color}22; background: linear-gradient(180deg, {bg}, #ffffff);">
              <summary>
                <div class="trace-head">
                  <div class="trace-dot" style="background:{color};"></div>
                  <div>
                    <div class="trace-title">{escape(trace.title)}</div>
                    <div class="trace-status">{escape(trace.status.title())}</div>
                  </div>
                </div>
                <div class="trace-summary">{escape(trace.summary)}</div>
              </summary>
              <div class="trace-detail">{escape(trace.detail)}</div>
              <div class="trace-mini-log">{escape(trace.title)} :: {escape(trace.summary)}</div>
            </details>
            """
        )
    return "".join(blocks)


def _trace_log(traces: list[TraceCard]) -> str:
    if not traces:
        return "<div class='code-line muted'>[trace] waiting for analysis...</div>"
    lines = []
    for idx, trace in enumerate(traces, 1):
        lines.append(
            f"<div class='code-line'><span class='code-tag'>[{idx:02d}]</span> {escape(trace.title)} :: {escape(trace.summary)}</div>"
        )
    return "".join(lines)


def _positions_rows() -> str:
    rows = []
    for p in _ACCOUNT.positions[-8:][::-1]:
        rows.append(
            f"""
            <tr>
              <td>{escape(p.symbol)}</td>
              <td>{escape(p.side)}</td>
              <td>{p.quantity}</td>
              <td>${p.entry_price:.2f}</td>
              <td>{_money(p.signed_value)}</td>
            </tr>"""
        )
    return "".join(rows) or '<tr><td colspan="5" class="muted">No active runs yet.</td></tr>'


def _orders_rows() -> str:
    rows = []
    for o in _ACCOUNT.order_history[-8:][::-1]:
        rows.append(
            f"""
            <tr>
              <td>{escape(o.order_id)}</td>
              <td>{escape(o.symbol)}</td>
              <td>{escape(o.side)}</td>
              <td>{escape(o.status)}</td>
              <td>{_money(o.cash_flow)}</td>
            </tr>"""
        )
    return "".join(rows) or '<tr><td colspan="5" class="muted">No actions yet.</td></tr>'


def _account_snapshot_html() -> str:
    return f"""
    <section class="panel">
      <div class="panel-head">
        <h2>System Snapshot</h2>
        <div class="panel-sub">Stateful broker ledger</div>
      </div>
      <div class="kpis">
        <div class="kpi"><span class="label">Cash</span><span class="value">{_money(_ACCOUNT.cash)}</span></div>
        <div class="kpi"><span class="label">Equity</span><span class="value">{_money(_ACCOUNT.total_equity)}</span></div>
        <div class="kpi"><span class="label">PnL</span><span class="value">{_money(_ACCOUNT.total_pnl)}</span></div>
        <div class="kpi"><span class="label">Positions</span><span class="value">{len(_ACCOUNT.positions)}</span></div>
      </div>
      <h3>Active Runs</h3>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Target</th><th>Side</th><th>Qty</th><th>Entry</th><th>Value</th></tr></thead>
          <tbody>{_positions_rows()}</tbody>
        </table>
      </div>
      <h3>Recent Actions</h3>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Action</th><th>Target</th><th>Side</th><th>Status</th><th>Cash Flow</th></tr></thead>
          <tbody>{_orders_rows()}</tbody>
        </table>
      </div>
    </section>
    """


def _agent_output_html(state: WorkflowState | None, banner: str = "") -> str:
    if state is None:
        return """
        <section class="panel agent-output" id="agent-output">
          <div class="panel-head">
            <div>
              <h2>Agent Output</h2>
              <div class="panel-sub">Select a node after analysis to inspect its inputs, traces, and outputs.</div>
            </div>
          </div>
          <div class="empty-output">
            <div class="empty-icon">A</div>
            <div class="empty-title">Agent outputs will appear here after analysis.</div>
          </div>
        </section>
        """

    trace_by_title = {trace.title: trace for trace in state.traces}
    selected = trace_by_title.get("Execution Agent" if state.order_id else "Decision Agent")
    if selected is None:
        selected = state.traces[-1] if state.traces else TraceCard("Decision Agent", "pending", "Pending", "Waiting for analysis.")

    sentiment = sentiment_snapshot_from_dict(state.sentiment) if state.sentiment else None
    technical = technical_snapshot_from_dict(state.technical) if state.technical else None
    sentiment_html = render_sentiment_panel(sentiment) if sentiment else ""
    technical_html = render_technical_panel(build_security_decision(state.symbol, sentiment, technical)) if sentiment and technical else ""

    review_html = ""
    if not state.review_status:
        review_html = f"""
        <form class="workflow-form compact-form" method="post" action="/approve">
          <input type="hidden" name="payload" value="{escape(state.to_payload())}" />
          <textarea name="approval_note" rows="2" placeholder="Approval note or rejection rationale"></textarea>
          <div class="button-row">
            <button type="submit" name="approval" value="approve">Approve</button>
            <button type="submit" name="approval" value="reject" class="secondary">Reject</button>
          </div>
        </form>
        """
    elif state.review_status == "approved" and not state.order_id:
        review_html = f"""
        <form class="workflow-form compact-form" method="post" action="/execute">
          <input type="hidden" name="payload" value="{escape(state.to_payload())}" />
          <button type="submit">Execute trade</button>
        </form>
        """
    elif state.review_status == "rejected":
        review_html = """
        <form class="workflow-form compact-form" method="get" action="/">
          <button type="submit" class="secondary">Analyze another target</button>
        </form>
        """

    execution_summary = ""
    if state.order_id:
        execution_summary = f"""
        <div class="ledger-summary">
          <div><span>Order</span><strong>{escape(state.order_id)}</strong></div>
          <div><span>Status</span><strong>{escape(state.order_status)}</strong></div>
          <div><span>Ledger</span><strong>{_money(_ACCOUNT.cash)} cash</strong></div>
        </div>
        """

    return f"""
    <section class="panel agent-output" id="agent-output">
      <div class="panel-head">
        <div>
          <h2>Agent Output</h2>
          <div class="panel-sub">{escape(banner) if banner else 'Decision Agent selected by default after analysis.'}</div>
        </div>
      </div>
      <div class="decision-banner">
        <div class="decision-kicker">{escape(selected.title)}</div>
        <div class="decision-main">{escape(state.side)} {escape(state.symbol)}</div>
        <div class="decision-meta">Confidence {state.confidence:.0%} · {escape(state.thesis)}</div>
      </div>
      <div class="trace-selected">
        <h3>Trace Summary</h3>
        <p>{escape(selected.summary)}</p>
        <h3>Raw-ish Trace Details</h3>
        <div class="trace-mini-log">{escape(selected.detail)}</div>
      </div>
      <div class="trace-io">
        <div>
          <h3>Inputs Used</h3>
          <ul class="compact-list">
            <li>Symbol: {escape(state.symbol)}</li>
            <li>CNN Fear &amp; Greed: {escape(str(state.sentiment.get('value', 'n/a')))} / {escape(str(state.sentiment.get('zone', 'n/a')))}</li>
            <li>EMA 8/21 and breakout state from security analysis</li>
          </ul>
        </div>
        <div>
          <h3>Outputs Produced</h3>
          <ul class="compact-list">
            <li>Recommendation: {escape(state.side)}</li>
            <li>Review state: {escape(state.review_status or 'Awaiting Approval')}</li>
            <li>Execution: {escape(state.order_status or 'Pending')}</li>
          </ul>
        </div>
      </div>
      <div class="market-trace-grid">
        {sentiment_html}
        {technical_html}
      </div>
      {review_html}
      {execution_summary}
    </section>
    """


def _market_context_html(state: WorkflowState | None) -> str:
    if state and state.sentiment:
        sentiment = sentiment_snapshot_from_dict(state.sentiment)
    else:
        sentiment = fetch_sentiment_snapshot()

    if state and state.technical:
        technical = technical_snapshot_from_dict(state.technical)
        decision = build_security_decision(state.symbol, sentiment, technical)
        technical_panel = render_technical_panel(decision)
    else:
        technical_panel = """
        <section class="panel market-panel">
          <div class="panel-head">
            <div>
              <h2>Security rationale</h2>
              <div class="panel-sub">Run an analysis to see the EMA and breakout explanation.</div>
            </div>
          </div>
          <div class="hint">The security agent will show whether the stock is above EMA 8 and EMA 21, whether it broke out of the recent range, and how CNN sentiment confirms or conflicts with the chart.</div>
        </section>
        """

    return f"""
    <div class="market-grid">
      {render_sentiment_panel(sentiment)}
      {technical_panel}
    </div>
    """


def _analysis_panel(state: WorkflowState | None, banner: str = "") -> str:
    if state is None:
        prompt = """
        <div class="panel">
          <div class="panel-head">
            <h2>Start an analysis</h2>
            <div class="panel-sub">Enter a target to run the pipeline and expose the agent traces.</div>
          </div>
          <form class="workflow-form" method="post" action="/analyze">
            <input name="symbol" placeholder="Target symbol, e.g. AAPL" value="AAPL" />
            <button type="submit">Run analysis</button>
          </form>
        </div>
        """
        return f"""
        {prompt}
        {_agent_output_html(None, banner)}
        """
    return _agent_output_html(state, banner)


def _approval_panel(state: WorkflowState, banner: str = "") -> str:
    return _agent_output_html(state, banner)


def _execution_panel(state: WorkflowState, banner: str = "") -> str:
    return _agent_output_html(state, banner) + _account_snapshot_html()


def _render_shell(stage: str, state: WorkflowState | None = None, banner: str = "") -> str:
    pipeline = _pipeline_html(stage, state)
    content = {
        "analyze": _analysis_panel(state, banner),
        "review": _approval_panel(state, banner) if state else _analysis_panel(None, banner),
        "execute": _execution_panel(state, banner) if state else _analysis_panel(None, banner),
        "done": _execution_panel(state, banner) if state else _analysis_panel(None, banner),
    }.get(stage, _analysis_panel(state, banner))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{APP_TITLE}</title>
  <style>
    :root {{
      --bg: #f7f9fc;
      --panel: rgba(255,255,255,.92);
      --panel-strong: rgba(255,255,255,.98);
      --border: rgba(16,24,40,.08);
      --ink: #101828;
      --muted: #667085;
      --primary: #2563eb;
      --primary-weak: #eff6ff;
      --teal: #0f766e;
      --teal-weak: #ecfdf5;
      --shadow: 0 20px 56px rgba(16,24,40,.08);
    }}
    html, body {{
      margin: 0; min-height: 100%;
      background:
        radial-gradient(circle at top left, rgba(37,99,235,.08), transparent 30%),
        radial-gradient(circle at top right, rgba(15,118,110,.06), transparent 26%),
        linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .shell {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 22px 18px 36px;
    }}
    .hero {{ display:none; }}
    .eyebrow {{
      display:inline-flex;
      padding: 7px 11px;
      border-radius: 999px;
      background: var(--primary-weak);
      border: 1px solid rgba(37,99,235,.16);
      color: var(--primary);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 10px 0 6px;
      font-size: clamp(28px, 4vw, 44px);
      line-height: 1.03;
      letter-spacing: -0.03em;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 74ch;
      line-height: 1.55;
    }}
    .hero-right {{
      text-align:right;
      color: var(--muted);
      font-size: 13px;
      display:flex;
      flex-direction:column;
      gap: 8px;
      align-items:flex-end;
    }}
    .pill {{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--panel-strong);
      border: 1px solid var(--border);
      font-size: 12px;
      font-weight: 700;
      color: var(--ink);
    }}
    .stepper {{ display:none; }}
    .step {{
      display:flex; align-items:center; gap: 10px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 12px 14px;
      box-shadow: 0 10px 30px rgba(16,24,40,.04);
    }}
    .step-badge {{
      width: 28px; height: 28px; border-radius: 999px;
      display:flex; align-items:center; justify-content:center;
      font-size: 12px; font-weight: 800;
      background: #edf2ff;
      color: #3b82f6;
      border: 1px solid rgba(59,130,246,.12);
    }}
    .step.done .step-badge {{
      background: #ecfdf5;
      color: #0f766e;
      border-color: rgba(15,118,110,.16);
    }}
    .step.active {{
      border-color: rgba(37,99,235,.22);
      box-shadow: 0 14px 34px rgba(37,99,235,.08);
    }}
    .step.active .step-badge {{
      background: #2563eb;
      color: white;
      border-color: transparent;
    }}
    .step-label {{
      font-size: 13px;
      font-weight: 800;
      color: var(--ink);
    }}
    .pipeline-shell {{
      background: rgba(255,255,255,.92);
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 20px;
      margin-bottom: 18px;
    }}
    .pipeline-head {{
      margin-bottom: 16px;
    }}
    .pipeline-title {{
      font-size: clamp(20px, 2.6vw, 28px);
      line-height: 1.1;
      letter-spacing: -0.03em;
      font-weight: 900;
      color: var(--ink);
      margin-top: 10px;
    }}
    .pipeline-copy {{
      margin-top: 8px;
      color: var(--muted);
      line-height: 1.5;
      max-width: 88ch;
    }}
    .pipeline-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .pipeline-card {{
      border-radius: 18px;
      border: 1px solid rgba(16,24,40,.10);
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      padding: 16px 14px;
      min-height: 162px;
      box-shadow: 0 14px 34px rgba(16,24,40,.05);
      display: grid;
      gap: 8px;
      align-content: start;
    }}
    .pipeline-card.running {{
      border-color: rgba(37,99,235,.22);
      box-shadow: 0 16px 36px rgba(37,99,235,.08);
    }}
    .pipeline-card.complete {{
      background: linear-gradient(180deg, #f8fffd, #ffffff);
    }}
    .pipeline-card.awaiting {{
      border-style: dashed;
      background: linear-gradient(180deg, #fffdf8, #ffffff);
    }}
    .pipeline-card.rejected {{
      border-color: rgba(220,38,38,.22);
      background: linear-gradient(180deg, #fef2f2, #ffffff);
    }}
    .pipeline-card.pending {{
      opacity: .86;
    }}
    .pipeline-icon {{
      width: 38px;
      height: 38px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--primary-weak);
      color: var(--primary);
      font-size: 18px;
      font-weight: 900;
      box-shadow: inset 0 0 0 1px rgba(37,99,235,.10);
    }}
    .pipeline-icon[data-accent="teal"] {{
      background: var(--teal-weak);
      color: var(--teal);
      box-shadow: inset 0 0 0 1px rgba(15,118,110,.12);
    }}
    .pipeline-icon[data-accent="amber"] {{
      background: #fff7ed;
      color: #b45309;
      box-shadow: inset 0 0 0 1px rgba(180,83,9,.12);
    }}
    .pipeline-icon[data-accent="violet"] {{
      background: #f5f3ff;
      color: #7c3aed;
      box-shadow: inset 0 0 0 1px rgba(124,58,237,.12);
    }}
    .pipeline-icon[data-accent="green"] {{
      background: #ecfdf3;
      color: #059669;
      box-shadow: inset 0 0 0 1px rgba(5,150,105,.12);
    }}
    .pipeline-icon[data-accent="slate"] {{
      background: #f1f5f9;
      color: #334155;
      box-shadow: inset 0 0 0 1px rgba(51,65,85,.12);
    }}
    .pipeline-name {{
      font-size: 16px;
      font-weight: 900;
      letter-spacing: -0.02em;
      color: var(--ink);
    }}
    .pipeline-summary {{
      font-size: 13px;
      font-weight: 700;
      color: var(--ink);
      line-height: 1.4;
    }}
    .pipeline-detail {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .pipeline-status {{
      margin-top: 2px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .pipeline-legend {{
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
      padding-top: 14px;
      margin-top: 14px;
      border-top: 1px solid rgba(16,24,40,.08);
      color: var(--muted);
      font-size: 13px;
      align-items: center;
    }}
    .pipeline-legend span {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      display: inline-block;
      background: #94a3b8;
    }}
    .legend-dot.complete {{ background: #0f766e; }}
    .legend-dot.running {{ background: #2563eb; }}
    .legend-dot.review {{ background: #b45309; }}
    .legend-dot.rejected {{ background: #dc2626; }}
    .legend-dot.pending {{ background: #94a3b8; }}
    .workspace {{
      display:grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 18px;
      align-items:start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .panel-head {{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap: 12px;
      margin-bottom: 16px;
    }}
    .panel h2, .panel h3 {{
      margin: 0;
      letter-spacing: -0.02em;
    }}
    .panel-sub {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 4px;
      line-height: 1.45;
    }}
    .market-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 18px;
    }}
    .market-panel {{
      min-height: 100%;
    }}
    .market-score {{
      display: inline-flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 2px;
      font-size: 36px;
      line-height: 1;
      font-weight: 900;
      color: var(--ink);
    }}
    .market-score span {{
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .sentiment-mini-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .sentiment-mini-kpi, .tech-metric {{
      border: 1px solid rgba(16,24,40,.06);
      border-radius: 16px;
      padding: 12px 14px;
      background: linear-gradient(180deg, #ffffff, #f8fafc);
    }}
    .sentiment-mini-kpi .label, .tech-metric .label {{
      display:block;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 4px;
    }}
    .sentiment-mini-kpi .value, .tech-metric .value {{
      font-size: 16px;
      font-weight: 900;
      color: var(--ink);
    }}
    .driver-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .driver-card {{
      border-radius: 16px;
      border: 1px solid rgba(16,24,40,.06);
      padding: 12px 13px;
      background: linear-gradient(180deg, #ffffff, #f8fafc);
      box-shadow: 0 10px 24px rgba(16,24,40,.04);
    }}
    .driver-title {{
      font-weight: 900;
      color: var(--ink);
      margin-bottom: 4px;
      line-height: 1.25;
    }}
    .driver-summary {{
      font-size: 13px;
      font-weight: 700;
      color: var(--ink);
      line-height: 1.45;
      margin-bottom: 4px;
    }}
    .driver-detail {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .tech-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .tech-chip-row {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }}
    .tech-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 11px;
      border-radius: 999px;
      background: var(--primary-weak);
      color: var(--primary);
      border: 1px solid rgba(37,99,235,.14);
      font-size: 12px;
      font-weight: 800;
    }}
    .decision-pill {{
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
    }}
    .reason-list {{
      margin: 0;
      padding-left: 18px;
      color: var(--ink);
      line-height: 1.55;
    }}
    .workflow-form {{
      display:grid;
      gap: 10px;
      margin-top: 14px;
    }}
    input, textarea, button {{
      width: 100%;
      box-sizing: border-box;
      border-radius: 14px;
      border: 1px solid rgba(16,24,40,.10);
      background: white;
      color: var(--ink);
      padding: 12px 14px;
      font: inherit;
    }}
    input:focus, textarea:focus {{
      outline: none;
      border-color: rgba(37,99,235,.35);
      box-shadow: 0 0 0 4px rgba(37,99,235,.10);
    }}
    button {{
      cursor: pointer;
      font-weight: 800;
      background: linear-gradient(135deg, rgba(37,99,235,.96), rgba(13,148,136,.96));
      color: white;
      border-color: transparent;
      box-shadow: 0 12px 28px rgba(37,99,235,.14);
    }}
    button.secondary {{
      background: white;
      color: var(--ink);
      border: 1px solid rgba(16,24,40,.10);
      box-shadow: none;
    }}
    .button-row {{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .decision-banner {{
      border-radius: 18px;
      padding: 16px 18px;
      border: 1px solid rgba(37,99,235,.16);
      background: linear-gradient(180deg, rgba(37,99,235,.08), rgba(255,255,255,.88));
      margin-bottom: 16px;
    }}
    .decision-banner.success {{
      border-color: rgba(15,118,110,.16);
      background: linear-gradient(180deg, rgba(15,118,110,.10), rgba(255,255,255,.94));
    }}
    .decision-kicker {{
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .decision-main {{
      font-size: 28px;
      line-height: 1.04;
      font-weight: 900;
      letter-spacing: -0.03em;
      color: var(--ink);
    }}
    .decision-meta {{
      margin-top: 6px;
      color: var(--muted);
      line-height: 1.45;
    }}
    .hint {{
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(37,99,235,.06);
      border: 1px solid rgba(37,99,235,.12);
      color: var(--ink);
      line-height: 1.45;
    }}
    .trace-grid {{
      display:grid;
      gap: 12px;
    }}
    .trace-card {{
      border: 1px solid rgba(16,24,40,.06);
      border-radius: 18px;
      padding: 14px;
      box-shadow: 0 12px 28px rgba(16,24,40,.04);
    }}
    .trace-card summary {{
      list-style: none;
      cursor: pointer;
    }}
    .trace-card summary::-webkit-details-marker {{
      display: none;
    }}
    .trace-head {{
      display:flex; align-items:center; gap: 10px; margin-bottom: 8px;
    }}
    .trace-dot {{
      width: 12px; height: 12px; border-radius: 999px; flex: 0 0 12px;
    }}
    .trace-title {{
      font-size: 14px;
      font-weight: 900;
      color: var(--ink);
    }}
    .trace-status {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .08em;
      font-weight: 700;
    }}
    .trace-summary {{
      font-weight: 700;
      margin-bottom: 4px;
      line-height: 1.45;
    }}
    .trace-detail {{
      color: var(--muted);
      line-height: 1.5;
      font-size: 13px;
    }}
    .trace-mini-log {{
      margin-top: 10px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      color: #475569;
      background: rgba(255,255,255,.74);
      border: 1px solid rgba(16,24,40,.06);
      border-radius: 12px;
      padding: 10px 12px;
    }}
    .trace-log {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 18px;
      padding: 14px;
      overflow: auto;
    }}
    .code-line {{
      padding: 4px 0;
      line-height: 1.5;
    }}
    .code-line.muted {{
      color: rgba(226,232,240,.6);
    }}
    .code-tag {{
      color: #93c5fd;
      margin-right: 6px;
    }}
    .kpis {{
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin: 14px 0 18px;
    }}
    .kpi {{
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid rgba(16,24,40,.06);
      background: linear-gradient(180deg, #ffffff, #f8fafc);
    }}
    .kpi .label {{
      display:block;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 4px;
    }}
    .kpi .value {{
      font-size: 18px;
      font-weight: 900;
      color: var(--ink);
    }}
    .table-wrap {{
      overflow:auto;
      border-radius: 18px;
      border: 1px solid rgba(16,24,40,.06);
      margin-bottom: 14px;
    }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
      font-size: 13px;
    }}
    .data-table th, .data-table td {{
      padding: 10px 12px;
      border-bottom: 1px solid rgba(16,24,40,.06);
      text-align:left;
      vertical-align: top;
    }}
    .data-table th {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .05em;
      font-size: 11px;
      background: #fafbfc;
    }}
    .trace-empty {{
      border: 1px dashed rgba(16,24,40,.16);
      border-radius: 18px;
      padding: 16px;
      background: rgba(255,255,255,.8);
    }}
    .trace-empty-kicker {{
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .trace-empty-title {{
      font-size: 18px;
      font-weight: 900;
      margin-bottom: 4px;
    }}
    .trace-empty-copy {{
      color: var(--muted);
      line-height: 1.5;
    }}
    .agent-output {{
      margin-top: 18px;
    }}
    .empty-output {{
      min-height: 180px;
      display: grid;
      place-items: center;
      text-align: center;
      border: 1px dashed rgba(16,24,40,.16);
      border-radius: 18px;
      background: #ffffff;
      color: var(--muted);
    }}
    .empty-icon {{
      width: 42px;
      height: 42px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 10px;
      background: var(--primary-weak);
      color: var(--primary);
      font-weight: 900;
    }}
    .empty-title {{
      font-weight: 800;
      color: var(--ink);
    }}
    .trace-selected p {{
      margin-top: 6px;
      color: var(--ink);
      line-height: 1.5;
    }}
    .trace-io {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 14px;
    }}
    .compact-list {{
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--ink);
      line-height: 1.55;
    }}
    .market-trace-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }}
    .compact-form {{
      max-width: 560px;
    }}
    .ledger-summary {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .ledger-summary div {{
      border: 1px solid rgba(16,24,40,.08);
      border-radius: 14px;
      padding: 12px;
      background: #fff;
    }}
    .ledger-summary span {{
      display:block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 4px;
    }}
    .footer-actions {{
      display:flex;
      gap: 10px;
      margin-top: 16px;
      flex-wrap: wrap;
    }}
    @media (max-width: 1080px) {{
      .market-grid {{ grid-template-columns: 1fr; }}
      .workspace {{ grid-template-columns: 1fr; }}
      .trace-io, .market-trace-grid, .ledger-summary {{ grid-template-columns: 1fr; }}
      .pipeline-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .stepper {{ grid-template-columns: 1fr; }}
      .hero {{ flex-direction: column; align-items:flex-start; }}
      .hero-right {{ align-items:flex-start; text-align:left; }}
    }}
    @media (max-width: 640px) {{
      .pipeline-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
    <div class="shell">
    {pipeline}

    <main class="workspace">
      <section>
        {content}
      </section>
      <aside class="panel">
        <div class="panel-head">
          <div>
            <h2>All Agent Traces</h2>
            <div class="panel-sub">Each graph node exposes its trace summary and raw-ish details.</div>
          </div>
        </div>
        <div class="trace-grid">
          { _trace_cards(state.traces if state else []) if state else _trace_cards([]) }
        </div>
      </aside>
    </main>
  </div>
</body>
</html>"""


app = FastAPI(title=APP_TITLE)


@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(_render_shell("analyze"))


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(symbol: str = Form(default="AAPL")) -> HTMLResponse:
    state = _build_analysis(symbol)
    return HTMLResponse(_render_shell("review", state, banner="Analysis complete. Decision Agent is selected."))


@app.post("/approve", response_class=HTMLResponse)
async def approve(
    payload: str = Form(default=""),
    approval: str = Form(default="approve"),
    approval_note: str = Form(default=""),
) -> HTMLResponse:
    if not payload.strip():
        return HTMLResponse(_render_shell("analyze", None, banner="Missing workflow state. Run analysis again."))

    state = WorkflowState.from_payload(payload)
    state.approval_note = approval_note.strip()

    if approval.lower() == "reject":
        state.review_status = "rejected"
        return HTMLResponse(
            _render_shell(
                "review",
                state,
                banner="Human Review rejected the recommendation.",
            )
        )

    state.review_status = "approved"
    return HTMLResponse(
        _render_shell(
            "execute",
            state,
            banner="Approval captured. The graph remains active for execution.",
        )
    )


@app.post("/execute", response_class=HTMLResponse)
async def execute(
    payload: str = Form(default=""),
    approval_note: str = Form(default=""),
) -> HTMLResponse:
    if not payload.strip():
        return HTMLResponse(_render_shell("analyze", None, banner="Missing workflow state. Run analysis again."))

    state = WorkflowState.from_payload(payload)
    if approval_note.strip():
        state.approval_note = approval_note.strip()
    if not state.review_status:
        state.review_status = "approved"
    state = _execute_trade(state)

    return HTMLResponse(
        _render_shell(
            "done",
            state,
            banner="Trade executed. Review the traces and the updated ledger.",
        )
    )


@app.get("/api/account")
async def api_account() -> dict[str, object]:
    return {
        "cash": round(_ACCOUNT.cash, 2),
        "total_equity": round(_ACCOUNT.total_equity, 2),
        "total_pnl": round(_ACCOUNT.total_pnl, 2),
        "position_count": len(_ACCOUNT.positions),
        "order_count": len(_ACCOUNT.order_history),
        "positions": [asdict(p) | {"signed_value": round(p.signed_value, 2), "pnl": round(p.pnl, 2)} for p in _ACCOUNT.positions],
        "order_history": [asdict(o) for o in reversed(_ACCOUNT.order_history[-12:])],
    }


@app.post("/api/reset")
async def api_reset() -> dict[str, str]:
    global _ACCOUNT
    _ACCOUNT = Account()
    return {"status": "reset"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "runtime": "fastapi",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
