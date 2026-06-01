r"""Fix duplicate equity chart code in trading_ui.py.

Problem: The equity chart Python code was inserted INSIDE the f-string template
(literal HTML text) instead of before the return statement (executable Python).

Also the code was duplicated.
"""

import re

path = "portfolio/trading/ui/trading_ui.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# The equity chart code block (find the first occurrence inside the f-string)
# It starts with:     # ── Equity performance chart ────────────────────────────────────
# And ends with the else block closing:         </div>'''
# Then there's a second duplicate right after.

equity_block_start = "    # \u2500\u2500 Equity performance chart \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"

# Find all occurrences
occurrences = [m.start() for m in re.finditer(re.escape(equity_block_start), content)]
print(f"Found {len(occurrences)} occurrence(s) of equity chart comment")

if len(occurrences) < 2:
    print("ERROR: Expected at least 2 occurrences (both inside f-string)")
    exit(1)

# The equity chart code to insert before the return statement
# We need the complete Python code block (the well-formed version)
# Take the first occurrence and extract the code

# Find the end of the first equity block - it ends before the second occurrence
first_start = occurrences[0]
second_start = occurrences[1]

# The first block goes from first_start to just before second_start
# But we need to find the exact end (after the last ''' closing)

# Actually, let's extract the equity chart code from the first block
# The code should be between the comment marker and the next section

# Extract the code block content - find the "else:" clause that ends with </div>'''
block_text = content[first_start:second_start]

# Find where the first block's code actually ends (before it reverts to f-string HTML)
# Look for the pattern that marks the end of the equity chart code
# The equity code has: elif len(snapshots) == 1: ... else: ... 
# After the else: block, the f-string template continues

# The equity chart code starts with:
#     equity_html = ""
# And ends with the else block closing the equity_html variable assignment

# Let me construct the correct equity chart code to insert before the return
equity_code = r"""
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
            bars_parts.append(f'''\
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; min-width:{bar_width_pct}px;">\
                <div style="width:100%; height:80px; display:flex; align-items:flex-end; justify-content:center;">\
                    <div title="${{s.equity:,.2f}} \u2014 {{s.label}}"\
                        style="width:{{max(2, bar_width_pct - 4)}}px; height:{{height_pct:.0f}}%;\
                        background:{{bar_color}}; border-radius:2px 2px 0 0;\
                        min-height:3px; transition:height .3s ease;"></div>\
                </div>\
            </div>''')\
        equity_html = f'''\
        <div style="font-weight:700; color:{{TEXT}}; margin-bottom:10px; font-size:0.92em;">\
            \U0001f4c8 Equity Performance <span style="font-weight:400; color:{{SECONDARY}}; font-size:0.85em;">\u2014 {{len(snapshots)}} snapshots</span>\
        </div>\
        <div style="background:{{BG}}; border-radius:8px; padding:14px 10px 8px; margin-bottom:16px; overflow-x:auto;">\
            <div style="display:flex; align-items:flex-end; gap:1px; height:90px; min-width:200px;">\
                {{"".join(bars_parts)}}\
            </div>\
            <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.68em; color:{{SECONDARY}};">\
                <span>${{snapshots[0].equity:,.0f}}</span>\
                <span>{{snapshots[0].timestamp.strftime("%H:%M")}}</span>\
                <span>\u2192</span>\
                <span>{{snapshots[-1].timestamp.strftime("%H:%M")}}</span>\
                <span>${{snapshots[-1].equity:,.0f}}</span>\
            </div>\
        </div>'''\
    elif len(snapshots) == 1:
        equity_html = f'''\
        <div style="font-weight:700; color:{{TEXT}}; margin-bottom:10px; font-size:0.92em;">\U0001f4c8 Equity Performance</div>\
        <div style="background:{{BG}}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center; color:{{SECONDARY}}; font-style:italic; font-size:0.82em;">\
            Starting equity: ${{snapshots[0].equity:,.2f}} \u2014 more data will appear after your next trade.\
        </div>'''\
    else:
        equity_html = f'''\
        <div style="font-weight:700; color:{{TEXT}}; margin-bottom:10px; font-size:0.92em;">\U0001f4c8 Equity Performance</div>\
        <div style="background:{{BG}}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center; color:{{SECONDARY}}; font-style:italic; font-size:0.82em;">\
            No trades yet \u2014 equity chart will appear after your first trade.\
        </div>'''\
"""

# Inline the equity code (remove the raw string formatting for Python file)
# The f-strings inside need double braces because they're inside another f-string template
# But here they're standalone Python code, so use single braces
equity_code = equity_code.replace("{{", "{").replace("}}", "}")
# Fix the backslash escapes that were for the raw string
equity_code = equity_code.replace("f'''\\", "f'''")
equity_code = equity_code.replace("</div>'''\\", "</div>'''")

# Now insert equity_code before the return f""" statement inside _render_account_summary
# Find the exact line: '    return f"""\\'
return_pattern = '    return f"""\\\n    <div class="trading-card" style="border-left:4px solid {TEAL}; margin-top:20px;">'

# Insert equity_code right before the return
insertion_point = content.find(return_pattern)
if insertion_point == -1:
    print("ERROR: Could not find return f-string in _render_account_summary")
    exit(1)

print(f"Insertion point for equity code: byte {insertion_point}")

# Insert the equity code before the return
content = content[:insertion_point] + equity_code + "\n" + content[insertion_point:]

# Now remove the duplicate equity chart code from inside the f-string
# Find both occurrences again (they shifted due to insertion)
occurrences_after = [m.start() for m in re.finditer(re.escape(equity_block_start), content)]
print(f"After insertion: {len(occurrences_after)} occurrence(s) of equity chart comment")

if len(occurrences_after) < 2:
    print("ERROR: Expected at least 2 occurrences after insertion")
    exit(1)

# We need to remove the two blocks inside the f-string
# The first block: from the comment to just before the second block
# The second block: from the comment to the end of its else clause

# Find where each block ends
# Block 1 ends before Block 2 starts
block1_start = occurrences_after[0]
block2_start = occurrences_after[1]

# Find the end of block 2 - it ends when the f-string template resumes with:
#         {equity_html}
#         <!-- P&L Breakdown -->
# or similar HTML

# Find the template marker after block 2
after_block2 = content.find("\n\n        {equity_html}", block2_start)
if after_block2 == -1:
    # Try alternative markers
    after_block2 = content.find("\n        {equity_html}", block2_start)

print(f"Block 1 start: {block1_start}, Block 2 start: {block2_start}, After block 2: {after_block2}")

if after_block2 == -1:
    print("ERROR: Could not find template marker after equity blocks")
    exit(1)

# Remove both blocks
# Everything from block1_start to after_block2 (but keep the {equity_html} line)
content = content[:block1_start] + content[after_block2:]

# Now verify there's exactly one {equity_html} reference in the template
equity_refs = content.count("{equity_html}")
print(f"equity_html references in template: {equity_refs}")

# Write the file
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] trading_ui.py fixed - equity chart code moved before return, duplicates removed")
