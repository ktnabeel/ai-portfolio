"""Vercel FastAPI entrypoint for the mini deployment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from uuid import uuid4

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse


APP_TITLE = "AI Engineer Deployment"


@dataclass
class Order:
    order_id: str
    symbol: str
    strategy: str
    status: str
    filled_price: float | None = None
    filled_quantity: int = 0
    total_cost: float | None = None
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Position:
    position_id: str
    symbol: str
    strategy: str
    option_type: str
    strike: float
    expiration: str
    quantity: int
    entry_price: float

    @property
    def market_value(self) -> float:
        return self.entry_price * self.quantity * 100

    @property
    def unrealized_pnl(self) -> float:
        return 0.0


@dataclass
class Account:
    cash: float = 100_000.0
    positions: list[Position] = field(default_factory=list)
    order_history: list[Order] = field(default_factory=list)
    total_commission: float = 0.0
    realized_pnl: float = 0.0

    @property
    def total_equity(self) -> float:
        return self.cash + sum(p.market_value for p in self.positions)

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions)

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl - self.total_commission


_ACCOUNT = Account()


def _money(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}${value:,.2f}"


def _render_page() -> str:
    account = _ACCOUNT
    positions = "".join(
        f"<tr><td>{escape(p.symbol)}</td><td>{escape(p.strategy)}</td><td>{escape(p.option_type)}</td><td>${p.strike:,.2f}</td><td>{escape(p.expiration or '-')}</td><td>{p.quantity}</td><td>${p.entry_price:,.2f}</td><td>{_money(p.unrealized_pnl)}</td></tr>"
        for p in account.positions
    ) or '<tr><td colspan="8" class="muted">No open positions.</td></tr>'
    orders = "".join(
        f"<tr><td>{escape(o.order_id)}</td><td>{escape(o.symbol)}</td><td>{escape(o.strategy)}</td><td>{escape(o.status)}</td><td>{'' if o.total_cost is None else f'${o.total_cost:,.2f}'}</td><td>{escape(o.notes)}</td></tr>"
        for o in reversed(account.order_history[-8:])
    ) or '<tr><td colspan="6" class="muted">No orders yet.</td></tr>'
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
      --border: rgba(16,24,40,.08);
      --ink: #101828;
      --muted: #667085;
      --primary: #2563eb;
      --secondary: #0f766e;
      --shadow: 0 20px 56px rgba(16,24,40,.08);
    }}
    html, body {{
      margin: 0; min-height: 100%;
      background:
        radial-gradient(circle at top left, rgba(37,99,235,.08), transparent 32%),
        radial-gradient(circle at top right, rgba(15,118,110,.06), transparent 24%),
        linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .shell {{ max-width: 1280px; margin: 0 auto; padding: 24px 18px 40px; }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px) saturate(160%);
    }}
    .hero {{
      display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 18px;
      padding: 22px 24px; margin-bottom: 18px; align-items: end;
    }}
    .pill {{
      display:inline-flex; align-items:center; padding:8px 12px; border-radius:999px;
      border:1px solid rgba(37,99,235,.18); background: rgba(37,99,235,.08); color: var(--primary);
      font-size:11px; font-weight:800; letter-spacing:.08em; text-transform:uppercase;
    }}
    h1 {{ margin: 0 0 6px; font-size: clamp(30px, 4vw, 46px); line-height: 1.02; }}
    p {{ margin: 0; color: var(--muted); max-width: 78ch; }}
    .grid {{ display:grid; grid-template-columns: minmax(320px, 380px) minmax(0,1fr); gap: 18px; }}
    .panel {{ padding: 18px; }}
    .panel h2, .panel h3 {{ margin-top: 0; }}
    .mini-grid {{
      display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:10px; margin:14px 0 18px;
    }}
    .card {{
      padding: 12px 14px; border-radius:14px; background:#f8fafc; border:1px solid rgba(16,24,40,.06);
    }}
    .label {{ display:block; color: var(--muted); font-size:11px; letter-spacing:.06em; text-transform:uppercase; margin-bottom:4px; }}
    .value {{ font-size: 15px; font-weight: 800; color: var(--ink); }}
    .kpis {{ display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:10px; margin:14px 0; }}
    .kpi {{ padding: 12px 14px; border-radius:14px; background:#f8fafc; border:1px solid rgba(16,24,40,.06); }}
    .kpi .value {{ font-size: 18px; }}
    form {{ display:grid; gap:10px; }}
    input, select, button {{
      width:100%; box-sizing:border-box; border-radius:12px; border:1px solid rgba(16,24,40,.10);
      background:#fff; color:var(--ink); padding:10px 12px; font: inherit;
    }}
    button {{ cursor:pointer; font-weight:800; background:linear-gradient(135deg, rgba(37,99,235,.92), rgba(13,148,136,.92)); color:#fff; border-color: transparent; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th, td {{ padding:8px 10px; border-bottom:1px solid rgba(16,24,40,.08); text-align:left; vertical-align:top; }}
    th {{ color: var(--muted); font-size:11px; letter-spacing:.05em; text-transform:uppercase; }}
    .muted {{ color: var(--muted); font-style: italic; }}
    .hint {{ padding:12px 14px; border-radius:14px; background:rgba(37,99,235,.06); border:1px solid rgba(37,99,235,.14); color:var(--ink); margin-top: 14px; }}
    @media (max-width: 980px) {{ .hero, .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div>
        <div class="pill">AI Engineer</div>
        <h1>Multi-agent AI systems</h1>
        <p>Agent workflow, simulated execution.</p>
      </div>
      <div class="pill">light theme</div>
    </section>
    <div class="grid">
      <section class="panel">
        <h2>Multi-Agent System</h2>
        <div class="mini-grid">
          <div class="card"><span class="label">Security Agent</span><span class="value">Identity & validation</span></div>
          <div class="card"><span class="label">Sentiment Agent</span><span class="value">News & market mood</span></div>
          <div class="card"><span class="label">Regime Agent</span><span class="value">Bull / Bear / Neutral</span></div>
          <div class="card"><span class="label">Decision Agent</span><span class="value">Strategy selection</span></div>
          <div class="card"><span class="label">Execution Agent</span><span class="value">Simulated broker</span></div>
          <div class="card"><span class="label">Portfolio Agent</span><span class="value">Final recommendation</span></div>
        </div>
        <h3>Execution Console</h3>
        <form method="post" action="/api/place-order">
          <input name="symbol" value="AAPL" placeholder="Symbol" />
          <select name="strategy">
            <option>Call</option>
            <option>Put</option>
            <option>Strangle</option>
            <option>No Trade</option>
          </select>
          <input name="option_type" value="call" placeholder="Option type" />
          <input name="strike" value="150" placeholder="Strike" />
          <input name="expiration" placeholder="Expiration YYYY-MM-DD" />
          <input name="quantity" value="1" type="number" step="1" />
          <input name="limit_price" placeholder="Limit price" />
          <button type="submit">Place Paper Order</button>
        </form>
        <div style="margin-top:16px">
          <form method="post" action="/api/reset">
            <button type="submit" style="background: rgba(255,255,255,.9); color: var(--ink); border:1px solid rgba(16,24,40,.10);">Reset Simulation</button>
          </form>
        </div>
        <div style="margin-top:16px">
          <form method="post" action="/api/close">
            <input name="position_id" placeholder="Position ID" />
            <input name="exit_price" placeholder="Exit price (optional)" />
            <button type="submit" style="background: rgba(255,255,255,.9); color: var(--ink); border:1px solid rgba(16,24,40,.10);">Close Position</button>
          </form>
        </div>
        <div class="hint">Positioning: AI engineer building multi-agent systems.</div>
      </section>
      <section class="panel">
        <h2>Account Snapshot</h2>
        <div class="kpis">
          <div class="kpi"><span class="label">Cash</span><span class="value">{_money(account.cash)}</span></div>
          <div class="kpi"><span class="label">Total Equity</span><span class="value">{_money(account.total_equity)}</span></div>
          <div class="kpi"><span class="label">Total P&L</span><span class="value">{_money(account.total_pnl)}</span></div>
          <div class="kpi"><span class="label">Positions</span><span class="value">{len(account.positions)}</span></div>
        </div>
        <h3>Open Positions</h3>
        <div style="overflow:auto; margin-bottom:18px;">
          <table>
            <thead><tr><th>Symbol</th><th>Strategy</th><th>Type</th><th>Strike</th><th>Expiry</th><th>Qty</th><th>Entry</th><th>P&L</th></tr></thead>
            <tbody>{positions}</tbody>
          </table>
        </div>
        <h3>Recent Orders</h3>
        <div style="overflow:auto;">
          <table>
            <thead><tr><th>Order</th><th>Symbol</th><th>Strategy</th><th>Status</th><th>Total</th><th>Notes</th></tr></thead>
            <tbody>{orders}</tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</body>
</html>"""


def _estimate_fill(symbol: str, strategy: str) -> tuple[float, float]:
    base = 4.75 if strategy == "Strangle" else 3.25 if strategy in {"Call", "Put"} else 0.0
    bump = (sum(ord(c) for c in symbol.upper()) % 7) * 0.12
    fill = round(base + bump, 2)
    total = round(fill * 100 + 0.65, 2)
    return fill, total


app = FastAPI(title=APP_TITLE)


@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(_render_page())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "runtime": "fastapi", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/account")
async def api_account() -> dict[str, object]:
    a = _ACCOUNT
    return {
        "cash": round(a.cash, 2),
        "total_equity": round(a.total_equity, 2),
        "total_pnl": round(a.total_pnl, 2),
        "position_count": len(a.positions),
        "order_count": len(a.order_history),
        "positions": [p.__dict__ | {"market_value": round(p.market_value, 2), "unrealized_pnl": round(p.unrealized_pnl, 2)} for p in a.positions],
        "order_history": [o.__dict__ for o in reversed(a.order_history[-15:])],
    }


@app.post("/api/place-order", response_model=None)
async def api_place_order(
    symbol: str = Form(default="AAPL"),
    strategy: str = Form(default="Call"),
    option_type: str = Form(default="call"),
    strike: str = Form(default="150"),
    expiration: str = Form(default=""),
    quantity: int = Form(default=1),
    limit_price: str = Form(default=""),
) -> HTMLResponse:
    if strategy == "No Trade":
        _ACCOUNT.order_history.append(Order(order_id=f"ORD-{uuid4().hex[:8].upper()}", symbol=symbol.upper(), strategy=strategy, status="No Trade", notes="No trade selected."))
        return HTMLResponse(_render_page())
    fill, total = _estimate_fill(symbol, strategy)
    _ACCOUNT.cash -= total
    pos = Position(
        position_id=f"POS-{uuid4().hex[:8].upper()}",
        symbol=symbol.upper(),
        strategy=strategy,
        option_type=option_type,
        strike=float(strike or 0),
        expiration=expiration,
        quantity=quantity,
        entry_price=fill,
    )
    _ACCOUNT.positions.append(pos)
    _ACCOUNT.total_commission += 0.65
    order = Order(order_id=f"ORD-{uuid4().hex[:8].upper()}", symbol=symbol.upper(), strategy=strategy, status="Filled", filled_price=fill, filled_quantity=quantity, total_cost=total, notes="Paper order filled.")
    _ACCOUNT.order_history.append(order)
    return HTMLResponse(_render_page())


@app.post("/api/reset")
async def api_reset() -> HTMLResponse:
    global _ACCOUNT
    _ACCOUNT = Account()
    return HTMLResponse(_render_page())


@app.post("/api/close", response_model=None)
async def api_close(position_id: str = Form(default=""), exit_price: str = Form(default="")) -> HTMLResponse | JSONResponse:
    pid = position_id.strip()
    if not pid:
        return JSONResponse(status_code=400, content={"success": False, "error": "position_id is required"})
    for idx, pos in enumerate(_ACCOUNT.positions):
        if pos.position_id == pid:
            _ACCOUNT.realized_pnl += 0.0
            _ACCOUNT.positions.pop(idx)
            return HTMLResponse(_render_page())
    return JSONResponse(status_code=404, content={"success": False, "error": "position not found"})
