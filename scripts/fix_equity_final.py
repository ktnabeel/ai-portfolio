"""Fix the equity chart code in trading_ui.py.

Problem: Two duplicate equity chart code blocks are embedded inside the
f-string template literal of _render_account_summary (they're literal HTML
text, not executed Python). The {equity_html} placeholder references an
empty string.

Solution:
1. Remove both duplicate blocks from the f-string
2. Add proper Python equity chart computation before the return statement
3. The {equity_html} placeholder in the f-string will now resolve correctly
"""

import os

FILE = os.path.join(os.path.dirname(__file__), "portfolio", "trading", "ui", "trading_ui.py")

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")

# Find the two "Equity performance chart" comment lines
marker_lines = []
for i, line in enumerate(lines):
    if "Equity performance chart" in line and line.strip().startswith("#"):
        marker_lines.append(i + 1)  # 1-indexed
        print(f"[FOUND] Equity chart marker at line {i+1}: {line.strip()}")

assert len(marker_lines) == 2, f"Expected 2 markers, found {len(marker_lines)}: {marker_lines}"

# Find the "P&L Breakdown: Realised vs Unrealised" comment line (comes after the chart)
pnl_line = None
for i, line in enumerate(lines):
    if "P&L Breakdown: Realised vs Unrealised" in line:
        pnl_line = i + 1
        print(f"[FOUND] P&L Breakdown at line {i+1}")
        break

assert pnl_line is not None, "Could not find P&L Breakdown marker"

# Find the return f""" statement (the one inside _render_account_summary)
return_line = None
for i, line in enumerate(lines):
    if 'return f"""' in line:
        return_line = i + 1
        print(f"[FOUND] return f\"\"\" at line {i+1}")

assert return_line is not None, "Could not find return statement"

# We need to find the correct return statement that belongs to _render_account_summary.
# There are multiple return statements. The one we want is around line 347.
# Let's find the one near line 347.
for i, line in enumerate(lines):
    if 'return f"""' in line and 340 < i + 1 < 360:
        return_line = i + 1
        print(f"[SELECTED] _render_account_summary return f\"\"\" at line {return_line}")
        break

# The equity chart Python code to insert before the return statement
equity_code = """\
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
            bars_parts.append(f'''
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; min-width:{bar_width_pct}px;">
                <div style="width:100%; height:80px; display:flex; align-items:flex-end; justify-content:center;">
                    <div title="${{s.equity:,.2f}} \\u2014 {s.label}"
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
                {{"".join(bars_parts)}}
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
        </div>'''"""

# Now build the new content:
# 1. Lines before return_line (0 to return_line-2, since return_line is 1-indexed and we want the line before)
# 2. Insert equity_code
# 3. Lines from return_line-1 onwards, but skip the two duplicate blocks

# The duplicate blocks span from marker_lines[0]-1 (0-indexed) to just before the P&L line
# First duplicate: marker_lines[0]-1 to just before the second duplicate
# Second duplicate: marker_lines[1]-1 to just before pnl_line

# Actually, both duplicates and the {equity_html} reference between them need to go.
# Let me be precise. The f-string contains:
#   [key metrics section]
#   [first equity chart block - lines marker[0]-1 to marker[1]-2]
#   [second equity chart block - lines marker[1]-1 to ...]
#   {equity_html}
#   [P&L Breakdown section]

# I need to:
# 1. Insert equity_code before the return f"""
# 2. Remove both duplicate blocks from the f-string
# 3. Keep the {equity_html} placeholder

# Find the blank line(s) between the second duplicate end and the P&L section
# The P&L section starts with <!-- P&L Breakdown: Realised vs Unrealised -->
# Let me find that exact line
pnl_comment_line = None
for i, line in enumerate(lines):
    if "<!-- P&L Breakdown: Realised vs Unrealised -->" in line:
        pnl_comment_line = i + 1
        print(f"[FOUND] P&L Breakdown comment at line {i+1}")
        break

assert pnl_comment_line is not None, "Could not find P&L Breakdown comment"

# The first duplicate starts at marker_lines[0]-1 (0-indexed)
# The P&L section starts at pnl_comment_line-1 (0-indexed)
# We want to remove: lines[marker_lines[0]-1 : pnl_comment_line]
# But keep the {equity_html} line

# Let me check what's between the end of the second block and the P&L section
print("\nLines between second block end and P&L section:")
for i in range(marker_lines[1], min(marker_lines[1] + 10, len(lines))):
    print(f"  Line {i}: {lines[i-1][:120]}")

# Actually, looking at the file, the structure is:
#   [first duplicate block]
#   [blank line]
#   [second duplicate block]
#   [blank lines]
#   {equity_html}
#   <!-- P&L Breakdown ... -->
#
# So I need to remove the two duplicate blocks but KEEP the {equity_html} and P&L section.

# The second duplicate block ends with an else clause that matches the first.
# Let me find where the second duplicate block ends by looking for the blank line before {equity_html}

equity_ref_line = None
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == "{equity_html}":
        equity_ref_line = i + 1
        print(f"[FOUND] {equity_html} reference at line {i+1}")
        break

assert equity_ref_line is not None, "Could not find equity_html reference"

# Remove from first duplicate marker (line marker_lines[0]) to equity_ref_line (exclusive)
# That removes both duplicates and keeps {equity_html}

# But wait, we also need to remove the blank lines between the duplicate blocks
# Let me just remove from marker_lines[0]-1 (0-indexed) to equity_ref_line-1 (0-indexed, exclusive)
# i.e., lines[marker_lines[0]-1 : equity_ref_line-1]

print(f"\nRemoving lines {marker_lines[0]} to {equity_ref_line-1} (inclusive)")

# Build new content
new_lines = []
new_lines.extend(lines[:marker_lines[0]-1])  # Everything before first duplicate
new_lines.extend(lines[equity_ref_line-1:])    # Everything from {equity_html} onwards

# Now insert equity_code before the return f""" statement
# Find the return f""" line index in the NEW array
new_return_idx = None
for i, line in enumerate(new_lines):
    if 'return f"""' in line and 330 < i < 370:
        new_return_idx = i
        print(f"[NEW] return f\"\"\" at index {i}")
        break

assert new_return_idx is not None, "Could not find return statement in new content"

# Insert equity_code right before the return statement
equity_lines = equity_code.split("\n")
# Add a blank line before the equity code for readability
new_lines = new_lines[:new_return_idx] + [""] + equity_lines + [""] + new_lines[new_return_idx:]

# Write the result
result = "\n".join(new_lines)
with open(FILE, "w", encoding="utf-8") as f:
    f.write(result)

print("\n[DONE] Equity chart fix applied successfully")
print(f"  - Removed duplicate blocks at lines {marker_lines[0]}-{equity_ref_line-1}")
print(f"  - Inserted equity_code before return f\"\"\" at new index {new_return_idx}")
print(f"  - File written to {FILE}")
