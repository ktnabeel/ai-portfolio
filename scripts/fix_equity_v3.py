"""Fix equity chart code in trading_ui.py - remove inline duplicates from f-string."""
import os

FILE = "portfolio/trading/ui/trading_ui.py"

with open(FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find markers
markers = []
for i, line in enumerate(lines):
    if "Equity performance chart" in line and line.strip().startswith("#"):
        markers.append(i)
        print(f"Marker at line {i+1}")

assert len(markers) == 2, f"Expected 2 markers, got {len(markers)}"

# Find {equity_html} reference
equity_ref = None
for i, line in enumerate(lines):
    if line.strip() == "{equity_html}":
        equity_ref = i
        print(f"equity_html ref at line {i+1}")
        break

assert equity_ref is not None, "equity_html ref not found"

# Find the return f""" for _render_account_summary (~line 347)
return_idx = None
for i, line in enumerate(lines):
    if 'return f"""' in line and 340 < i < 360:
        return_idx = i
        print(f"return f-string at line {i+1}")
        break

assert return_idx is not None, "return f-string not found"

# Remove both duplicate blocks (markers[0] to just before equity_ref)
# Also remove blank lines between
new_lines = lines[:markers[0]] + lines[equity_ref:]

# Equity chart code to insert before return
# Note: Using double-braces {{ }} for literal braces in the f-strings within the code
eq_code = [
    "    # Equity performance chart\n",
    '    equity_html = ""\n',
    "    snapshots = account.equity_snapshots\n",
    "    if len(snapshots) >= 2:\n",
    "        start_equity = snapshots[0].equity if snapshots else 100_000.0\n",
    "        min_e = min(s.equity for s in snapshots)\n",
    "        max_e = max(s.equity for s in snapshots)\n",
    "        range_e = max(max_e - min_e, 1.0)\n",
    "        bar_width_pct = max(1, 100 // max(len(snapshots), 1))\n",
    "        bars_parts = []\n",
    "        for s in snapshots[-40:]:\n",
    "            height_pct = max(4, ((s.equity - min_e) / range_e) * 100)\n",
    "            is_above_start = s.equity >= start_equity\n",
    "            bar_color = GREEN if is_above_start else RED\n",
    "            title_str = f'${s.equity:,.2f} -- {s.label}'\n",
    "            bars_parts.append(\n",
    "                f'<div style=\"flex:1; display:flex; flex-direction:column; align-items:center; min-width:{bar_width_pct}px;\">'\n",
    "                f'<div style=\"width:100%; height:80px; display:flex; align-items:flex-end; justify-content:center;\">'\n",
    "                f'<div title=\"{title_str}\" style=\"width:{max(2, bar_width_pct - 4)}px; height:{height_pct:.0f}%;'\n",
    "                f'background:{bar_color}; border-radius:2px 2px 0 0; min-height:3px; transition:height .3s ease;\"></div>'\n",
    "                f'</div></div>'\n",
    "            )\n",
    "        bars_html = ''.join(bars_parts)\n",
    "        equity_html = (\n",
    '            f\'<div style=\"font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;\">\'\n',
    "            f'[chart] Equity Performance '\n",
    "            f'<span style=\"font-weight:400; color:{SECONDARY}; font-size:0.85em;\">-- {len(snapshots)} snapshots</span>'\n",
    "            f'</div>'\n",
    "            f'<div style=\"background:{BG}; border-radius:8px; padding:14px 10px 8px; margin-bottom:16px; overflow-x:auto;\">'\n",
    "            f'<div style=\"display:flex; align-items:flex-end; gap:1px; height:90px; min-width:200px;\">'\n",
    "            f'{bars_html}'\n",
    "            f'</div>'\n",
    "            f'<div style=\"display:flex; justify-content:space-between; margin-top:6px; font-size:0.68em; color:{SECONDARY};\">'\n",
    "            f'<span>${snapshots[0].equity:,.0f}</span>'\n",
    "            f'<span>{snapshots[0].timestamp.strftime(\"%H:%M\")}</span>'\n",
    "            f'<span>-></span>'\n",
    "            f'<span>{snapshots[-1].timestamp.strftime(\"%H:%M\")}</span>'\n",
    "            f'<span>${snapshots[-1].equity:,.0f}</span>'\n",
    "            f'</div></div>'\n",
    "        )\n",
    "    elif len(snapshots) == 1:\n",
    "        equity_html = (\n",
    "            f'<div style=\"font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;\">'\n",
    "            f'[chart] Equity Performance</div>'\n",
    "            f'<div style=\"background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center;'\n",
    "            f'color:{SECONDARY}; font-style:italic; font-size:0.82em;\">'\n",
    "            f'Starting equity: ${snapshots[0].equity:,.2f} -- more data will appear after your next trade.'\n",
    "            f'</div>'\n",
    "        )\n",
    "    else:\n",
    "        equity_html = (\n",
    "            f'<div style=\"font-weight:700; color:{TEXT}; margin-bottom:10px; font-size:0.92em;\">'\n",
    "            f'[chart] Equity Performance</div>'\n",
    "            f'<div style=\"background:{BG}; border-radius:8px; padding:20px; margin-bottom:16px; text-align:center;'\n",
    "            f'color:{SECONDARY}; font-style:italic; font-size:0.82em;\">'\n",
    "            f'No trades yet -- equity chart will appear after your first trade.'\n",
    "            f'</div>'\n",
    "        )\n",
    "\n",
]

# Find return_idx in new_lines
new_return = None
for i, line in enumerate(new_lines):
    if 'return f"""' in line and 330 < i < 370:
        new_return = i
        break

assert new_return is not None, f"return not found in new_lines (len={len(new_lines)})"

# Insert equity code before return
new_lines = new_lines[:new_return] + eq_code + ["\n"] + new_lines[new_return:]

with open(FILE, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"OK. Removed lines {markers[0]+1} to {equity_ref}. Inserted code at line {new_return+1}.")
print("DONE")
