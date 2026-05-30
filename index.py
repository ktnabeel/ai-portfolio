"""Vercel FastAPI entrypoint for the workflow demo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape
from uuid import uuid4

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse


APP_TITLE = "Workflow Lab"
STAGES = ("analyze", "approve", "execute", "done")
PIPELINE_STEPS = (
    ("Security Agent", "Validate the target and policy gate.", "🔎", "blue"),
    ("Risk & Sentiment", "Fuse mood, news, and noise into one read.", "🧭", "teal"),
    ("Regime Detection", "Classify the market context.", "🔁", "amber"),
    ("Options Chain", "Fetch the contract landscape.", "📊", "violet"),
    ("Decision Agent", "Select buy or sell and explain the thesis.", "🎯", "green"),
    ("Execution Agent", "Route the simulated trade after review.", "💸", "slate"),
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
    analysis_id: str = field(default_factory=lambda: f"ANL-{uuid4().hex[:8].upper()}")
    approval_note: str = ""
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
                "analysis_id": self.analysis_id,
                "approval_note": self.approval_note,
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
            analysis_id=raw.get("analysis_id", f"ANL-{uuid4().hex[:8].upper()}"),
            approval_note=raw.get("approval_note", ""),
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
    side, confidence, thesis = _decision_for(symbol)
    score = sum(ord(c) for c in symbol)
    signal = "positive" if score % 3 == 0 else "mixed" if score % 3 == 1 else "negative"
    regime = "risk-on" if score % 4 in {0, 1} else "defensive"
    traces = [
        TraceCard(
            title="Security Agent",
            status="complete",
            summary=f"Validated {symbol} as a reviewable target.",
            detail="The security gate checked symbol hygiene, policy constraints, and source sanity.",
            accent="blue",
        ),
        TraceCard(
            title="Risk & Sentiment",
            status="complete",
            summary=f"Signal read: {signal}.",
            detail="The sentiment read stitched together synthetic news, momentum tone, and risk pressure.",
            accent="teal",
        ),
        TraceCard(
            title="Regime Detection",
            status="complete",
            summary=f"Macro context is {regime}.",
            detail="The regime agent filtered the setup through a simple bull, bear, or neutral gate.",
            accent="amber",
        ),
        TraceCard(
            title="Options Chain",
            status="complete",
            summary=f"Contract chain available for {symbol}.",
            detail="The chain agent surfaced the contract landscape, spreads, and nearby strikes.",
            accent="violet",
        ),
        TraceCard(
            title="Decision Agent",
            status="complete",
            summary=f"Recommend {side}.",
            detail=f"Confidence {confidence:.0%}. Thesis: {thesis}.",
            accent="green",
        ),
    ]
    return WorkflowState(
        symbol=symbol,
        side=side,
        confidence=confidence,
        thesis=thesis,
        traces=traces,
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


def _fmt_step(stage: str, idx: int, label: str) -> str:
    stages = {"analyze": 0, "approve": 1, "execute": 2, "done": 2}
    current = stages.get(stage, 0)
    cls = "done" if idx < current else "active" if idx == current else "pending"
    badge = "✓" if cls == "done" else str(idx + 1)
    return f"""
    <div class="step {cls}">
      <span class="step-badge">{badge}</span>
      <span class="step-label">{escape(label)}</span>
    </div>"""


def _render_stepper(stage: str) -> str:
    labels = ["Analyze", "Human approval", "Execute"]
    items = "".join(_fmt_step(stage, idx, label) for idx, label in enumerate(labels))
    return f"""
    <div class="stepper">
      {items}
    </div>"""


def _pipeline_status(stage: str, index: int) -> str:
    stage_map = {"analyze": 0, "approve": 4, "execute": 5, "done": 5}
    current = stage_map.get(stage, 0)
    if index < current:
        return "complete"
    if index == current:
        return "running" if stage != "approve" else "awaiting"
    return "pending"


def _pipeline_html(stage: str, state: WorkflowState | None) -> str:
    trace_by_title = {trace.title: trace for trace in (state.traces if state else [])}
    cards = []
    for idx, (title, subtitle, icon, accent) in enumerate(PIPELINE_STEPS):
        trace = trace_by_title.get(title)
        status = _pipeline_status(stage, idx)
        status_label = "Awaiting Approval" if status == "awaiting" else status.replace("_", " ").title()
        summary = trace.summary if trace else subtitle
        detail = trace.detail if trace else subtitle
        cards.append(
            f"""
            <article class="pipeline-card {status}">
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
          <div class="pipeline-title">LangGraph-style orchestration with human review</div>
          <div class="pipeline-copy">The emphasis is on the agents making the call, exposing their traces, and allowing you to inspect each decision before anything executes.</div>
        </div>
      </div>
      <div class="pipeline-grid">
        {''.join(cards)}
      </div>
      <div class="pipeline-legend">
        <span><i class="legend-dot complete"></i>Complete</span>
        <span><i class="legend-dot running"></i>Running</span>
        <span><i class="legend-dot review"></i>Awaiting approval</span>
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
          <div class="hint">The approval gate only appears after the agents produce a recommendation.</div>
        </div>
        """
        return prompt

    decision_callout = f"""
    <div class="decision-banner">
      <div class="decision-kicker">Decision Agent</div>
      <div class="decision-main">{escape(state.side)} recommendation</div>
      <div class="decision-meta">Confidence {state.confidence:.0%} · {escape(state.thesis)}</div>
    </div>
    """
    return f"""
    <div class="panel">
      <div class="panel-head">
        <h2>Decision review</h2>
        <div class="panel-sub">{escape(banner) if banner else 'Review the recommendation before human approval.'}</div>
      </div>
      {decision_callout}
      <form class="workflow-form" method="post" action="/approve">
        <input type="hidden" name="payload" value="{escape(state.to_payload())}" />
        <button type="submit">Open approval screen</button>
      </form>
    <div class="hint">Trace ID {escape(state.analysis_id)} · {escape(state.symbol)} · Deep dive remains visible on the side.</div>
    </div>
    """


def _approval_panel(state: WorkflowState, banner: str = "") -> str:
    return f"""
    <div class="panel">
      <div class="panel-head">
        <h2>Human approval</h2>
        <div class="panel-sub">{escape(banner) if banner else 'Approve the recommendation, add a note, or reject it and rerun analysis.'}</div>
      </div>
      <div class="decision-banner">
        <div class="decision-kicker">Recommendation</div>
        <div class="decision-main">{escape(state.side)} {escape(state.symbol)}</div>
        <div class="decision-meta">Confidence {state.confidence:.0%} · {escape(state.thesis)}</div>
      </div>
      <form class="workflow-form" method="post" action="/execute">
        <input type="hidden" name="payload" value="{escape(state.to_payload())}" />
        <textarea name="approval_note" rows="3" placeholder="Approval note or override rationale"></textarea>
        <div class="button-row">
          <button type="submit" name="approval" value="approve">Approve and continue</button>
          <button type="submit" name="approval" value="reject" class="secondary">Reject</button>
        </div>
      </form>
      <div class="hint">The approval note is captured before execution. The deep-dive rail keeps the agent reasoning visible.</div>
    </div>
    """


def _execution_panel(state: WorkflowState, banner: str = "") -> str:
    order_rows = _orders_rows()
    position_rows = _positions_rows()
    if state.order_id:
        order_banner = f"""
        <div class="decision-banner success">
          <div class="decision-kicker">Execution complete</div>
          <div class="decision-main">{escape(state.side)} routed</div>
          <div class="decision-meta">{escape(state.execution_note)}</div>
        </div>
        """
    else:
        order_banner = """
        <div class="decision-banner">
          <div class="decision-kicker">Execution screen</div>
          <div class="decision-main">Ready to execute</div>
          <div class="decision-meta">Human approval has been captured.</div>
        </div>
        """
    execute_form = """
    <form class="workflow-form" method="post" action="/execute">
      <input type="hidden" name="payload" value="{payload}" />
      <input type="hidden" name="approval_note" value="{note}" />
      <button type="submit">Execute trade</button>
    </form>
    """.format(payload=escape(state.to_payload()), note=escape(state.approval_note))
    restart_form = """
    <form class="workflow-form" method="get" action="/">
      <button type="submit" class="secondary">Analyze another target</button>
    </form>
    """
    return f"""
    <div class="panel">
      <div class="panel-head">
        <h2>Execute</h2>
        <div class="panel-sub">{escape(banner) if banner else 'Execute only after approval; the trace rail stays visible for review.'}</div>
      </div>
      {order_banner}
      {execute_form if not state.order_id else restart_form}
      <div class="hint">Order ID {escape(state.order_id or 'pending')} · Approval: {escape(state.approval_note or 'none')}</div>
    </div>
    <section class="panel">
      <div class="panel-head">
        <h2>System Snapshot</h2>
        <div class="panel-sub">Current state after execution</div>
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
          <tbody>{position_rows}</tbody>
        </table>
      </div>
      <h3>Recent Actions</h3>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Action</th><th>Target</th><th>Side</th><th>Status</th><th>Cash Flow</th></tr></thead>
          <tbody>{order_rows}</tbody>
        </table>
      </div>
    </section>
    """


def _render_shell(stage: str, state: WorkflowState | None = None, banner: str = "") -> str:
    pipeline = _pipeline_html(stage, state)
    content = {
        "analyze": _analysis_panel(state, banner),
        "approve": _approval_panel(state, banner) if state else _analysis_panel(None, banner),
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
    .hero {{
      display:flex; align-items:flex-end; justify-content:space-between; gap:18px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 22px 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px) saturate(160%);
      margin-bottom: 18px;
    }}
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
    .stepper {{
      display:grid;
      grid-template-columns: repeat(3, minmax(0,1fr));
      gap: 10px;
      margin-bottom: 18px;
    }}
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
      grid-template-columns: repeat(3, minmax(0, 1fr));
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
    .legend-dot.pending {{ background: #94a3b8; }}
    .workspace {{
      display:grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(340px, .8fr);
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
    .footer-actions {{
      display:flex;
      gap: 10px;
      margin-top: 16px;
      flex-wrap: wrap;
    }}
    @media (max-width: 1080px) {{
      .workspace {{ grid-template-columns: 1fr; }}
      .stepper {{ grid-template-columns: 1fr; }}
      .hero {{ flex-direction: column; align-items:flex-start; }}
      .hero-right {{ align-items:flex-start; text-align:left; }}
    }}
  </style>
</head>
<body>
    <div class="shell">
    <header class="hero">
      <div>
        <div class="eyebrow">AI Engineer · Workflow Lab</div>
        <h1>Agent decisions first. Execution second.</h1>
        <p>A light, workflow-first interface built to show agent reasoning, human review, and deep dives before any simulated trade is routed.</p>
      </div>
      <div class="hero-right">
        <div class="pill">Light theme</div>
        <div class="pill">Pipeline exploration</div>
      </div>
    </header>

    {_render_stepper(stage)}
    {pipeline}

    <main class="workspace">
      <section>
        {content}
      </section>
      <aside class="panel">
        <div class="panel-head">
          <div>
            <h2>Agent Deep Dive</h2>
            <div class="panel-sub">Open each agent to inspect the rationale, not just the outcome.</div>
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
    return HTMLResponse(_render_shell("approve", state, banner="Analysis complete. Review the traces and decide whether to proceed."))


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
        return HTMLResponse(
            _render_shell(
                "analyze",
                state,
                banner="The trade was rejected by the human reviewer. Re-run analysis to try another target.",
            )
        )

    return HTMLResponse(
        _render_shell(
            "execute",
            state,
            banner="Approval captured. The next screen executes the trade.",
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
