"""Replace _render_account_summary in trading_ui.py with the new P&L tracking version."""
import re

with open("portfolio/trading/ui/trading_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the start and end of _render_account_summary
start_marker = "def _render_account_summary() -> str:"
end_marker = "def _render_flow_diagram("

start_idx = content.index(start_marker)
end_idx = content.index(end_marker, start_idx)

new_function = r'''def _render_account_summary() -> str:
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

        <div style="display:flex; gap:8px; margin-top:12px; justify-content:flex-end;">
            <button onclick="document.querySelector('#reset-account-btn').click()"
                style="background:{BORDER}; color:{SECONDARY}; border:none; border-radius:6px;
                padding:6px 14px; cursor:pointer; font-size:0.82em;">
                🔄 Reset Account
            </button>
        </div>
    </div>"""


'''

new_content = content[:start_idx] + new_function + "\n" + content[end_idx:]

with open("portfolio/trading/ui/trading_ui.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Replacement successful!")
