"""Fix trading_ui.py: move equity chart code before return, remove duplicates inside f-string."""

path = "portfolio/trading/ui/trading_ui.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# The equity chart comment marker (box-drawing chars)
MARKER = "    # \u2500\u2500 Equity performance chart \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"

# Find all occurrences
import re
matches = list(re.finditer(re.escape(MARKER), content))
print(f"Found {len(matches)} occurrences of equity chart comment")

if len(matches) < 2:
    print("ERROR: Need at least 2 occurrences")
    exit(1)

# Find the return statement in _render_account_summary
return_pattern = '    return f"""\\\n    <div class="trading-card" style="border-left:4px solid {TEAL}; margin-top:20px;">'
return_pos = content.find(return_pattern)
print(f"Return statement at byte {return_pos}")

if return_pos == -1:
    print("ERROR: Could not find return statement")
    exit(1)

# The equity chart Python code to insert before the return statement
equity_code = '''
    # ── Equity performance chart ────────────────────────────────────
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
            bars_parts.append(f\'\'\'
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; min-width:{bar_width_pct}px;">
                <div style="width:100%; height:80px; display:flex; align-items:flex-end; justify-content:center;">
                    <div title="${s.equity:,.2f} \\u2014 {s.label}"
                        style="width:{max(2, bar_width_pct - 4)}px; height:{height_pct:.0f}%;
                        background:{bar_color}; border-radius:2px 2px 0 0;
                        min-height:3px; transition:height .3s ease;"></div>
                </div>
            </div>\'\'\')
        equity_html = f\'\'\'
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
        </div>\'\'\'
    elif len(snapshots) == 1:
        equity_html = f\'\'\'
        <div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">\\U0001f4c8 Equity Performance</div>
        <div style="background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center; color:{SECONDARY}; font-style:italic; font-size:0.82em;">
            Starting equity: ${snapshots[0].equity:,.2f} \\u2014 more data will appear after your next trade.
        </div>\'\'\'
    else:
        equity_html = f\'\'\'
        <div style="font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;">\\U0001f4c8 Equity Performance</div>
        <div style="background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center; color:{SECONDARY}; font-style:italic; font-size:0.82em;">
            No trades yet \\u2014 equity chart will appear after your first trade.
        </div>\'\'\'
'''

# Insert equity code before the return statement
content = content[:return_pos] + equity_code + "\n" + content[return_pos:]
print(f"Inserted equity code before return statement")

# Re-scan for markers (positions shifted)
matches2 = list(re.finditer(re.escape(MARKER), content))
print(f"After insertion: {len(matches2)} occurrences of equity chart comment")

if len(matches2) < 3:
    print(f"ERROR: Expected at least 3 occurrences after insertion (1 new + 2 old), got {len(matches2)}")
    exit(1)

# The first occurrence is the one we just added (before return statement)
# The second and third are the duplicates inside the f-string to remove
block1_start = matches2[1].start()  # first duplicate
block2_start = matches2[2].start()  # second duplicate

# Find where to cut: after block2's else clause, the template continues with
#         {equity_html}
#         <!-- P&L Breakdown: Realised vs Unrealised -->
after_marker = "\n\n        {equity_html}"
after_pos = content.find(after_marker, block2_start)

if after_pos == -1:
    # Try without double newline
    after_marker = "\n        {equity_html}"
    after_pos = content.find(after_marker, block2_start)

if after_pos == -1:
    print("ERROR: Could not find {equity_html} template marker after equity blocks")
    exit(1)

print(f"Removing duplicate blocks from byte {block1_start} to {after_pos}")

# Remove the two duplicate blocks (everything from block1_start to after_pos)
content = content[:block1_start] + content[after_pos:]

# Verify
remaining = content.count(MARKER)
print(f"Equity chart markers remaining: {remaining} (should be 1)")

equity_refs = content.count("{equity_html}")
print(f"equity_html references in template: {equity_refs} (should be 1)")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] trading_ui.py fixed successfully")
