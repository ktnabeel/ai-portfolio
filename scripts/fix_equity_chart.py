"""Insert equity performance chart into _render_account_summary and fix theme init JS."""
from pathlib import Path

# ── 1. Insert equity performance chart into trading_ui.py ─────────────
trading_ui_path = Path("portfolio/trading/ui/trading_ui.py")
content = trading_ui_path.read_text(encoding="utf-8")

# Marker: find "P&L Breakdown: Realised vs Unrealised" HTML comment
marker = "        <!-- P&L Breakdown: Realised vs Unrealised -->"
equity_section = """    # ── Equity performance chart ────────────────────────────────────
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
            bars_parts.append(f'''
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; min-width:{bar_width_pct}px;">
                <div style="width:100%; height:80px; display:flex; align-items:flex-end; justify-content:center;">
                    <div title="${s.equity:,.2f} \\u2014 {s.label}"
                        style="width:{max(2, bar_width_pct - 4)}px; height:{height_pct:.0f}%;
                        background:{bar_color}; border-radius:2px 2px 0 0;
                        min-height:3px; transition:height .3s ease;"></div>
                </div>
            </div>''')
        equity_html = f'''
        <div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">
            \\U0001f4c8 Equity Performance <span style="font-weight:400; color:{SECONDARY}; font-size:0.85em;">\\u2014 {len(snapshots)} snapshots</span>
        </div>
        <div style="background:{BG}; border-radius:8px; padding:14px 10px 8px; margin-bottom:16px; overflow-x:auto;">
            <div style="display:flex; align-items:flex-end; gap:1px; height:90px; min-width:200px;">
                {"".join(bars_parts)}
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.68em; color:{SECONDARY};">
                <span>${snapshots[0].equity:,.0f}</span>
                <span>{snapshots[0].timestamp.strftime("%H:%M")}</span>
                <span>\\u2192</span>
                <span>{snapshots[-1].timestamp.strftime("%H:%M")}</span>
                <span>${snapshots[-1].equity:,.0f}</span>
            </div>
        </div>'''
    elif len(snapshots) == 1:
        equity_html = f'''
        <div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">\\U0001f4c8 Equity Performance</div>
        <div style="background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center; color:{SECONDARY}; font-style:italic; font-size:0.82em;">
            Starting equity: ${snapshots[0].equity:,.2f} \\u2014 more data will appear after your next trade.
        </div>'''
    else:
        equity_html = f'''
        <div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">\\U0001f4c8 Equity Performance</div>
        <div style="background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center; color:{SECONDARY}; font-style:italic; font-size:0.82em;">
            No trades yet \\u2014 equity chart will appear after your first trade.
        </div>'''

"""

if marker in content:
    content = content.replace(marker, equity_section + "\n" + marker)
    trading_ui_path.write_text(content, encoding="utf-8")
    print("[OK] Equity chart inserted into trading_ui.py")
else:
    print("[FAIL] Marker not found in trading_ui.py")

# ── Also insert {equity_html} reference into the return f-string ─────
# Find where the P&L Breakdown cards render in the return and add equity_html
content = trading_ui_path.read_text(encoding="utf-8")
# Find the equity chart section ends and the P&L cards begin
pnl_cards_marker = """        <!-- P&L Breakdown: Realised vs Unrealised -->"""
if pnl_cards_marker in content:
    # Add {equity_html} before the P&L cards
    content = content.replace(
        pnl_cards_marker,
        "        {equity_html}\n" + pnl_cards_marker
    )
    trading_ui_path.write_text(content, encoding="utf-8")
    print("[OK] equity_html reference inserted into return f-string")
else:
    print("[FAIL] P&L cards marker not found")

# ── 2. Re-add theme init JS to render.py Gradio mode ──────────────────
render_path = Path("portfolio/render.py")
render_content = render_path.read_text(encoding="utf-8")

old_gradio_return = """    if mode == \"gradio\":
        return f\"<style>{_css()}</style>{page}\""""

new_gradio_return = """    if mode == \"gradio\":
        theme_init_js = (
            \"<script>(function(){\"\n            \"var t;try{t=localStorage.getItem('theme')}catch(e){};\"\n            \"if(t){document.documentElement.setAttribute('data-theme',t)}\"\n            \"else if(window.matchMedia('(prefers-color-scheme:dark)').matches)\"\n            \"{document.documentElement.setAttribute('data-theme','dark')};\"\n            \"})();</script>\"\n        )\n        return f\"<style>{_css()}</style>{theme_init_js}{page}\""""

if old_gradio_return in render_content:
    render_content = render_content.replace(old_gradio_return, new_gradio_return)
    render_path.write_text(render_content, encoding="utf-8")
    print("[OK] Theme init JS re-added to render.py Gradio mode")
else:
    print("[FAIL] Gradio return not found in render.py")

print("\\nAll fix_equity_chart.py operations complete.")
