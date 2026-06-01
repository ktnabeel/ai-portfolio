"""Align static/style.css dark theme with render.py _css() pineconnector-inspired scheme."""
from pathlib import Path

css_path = Path("static/style.css")
content = css_path.read_text(encoding="utf-8")

# The dark theme block to replace
old_dark_block = """[data-theme="dark"] {
  color-scheme: dark;
  --theme-bg: #0d1117;
  --theme-panel: #161b22;
  --theme-ink: #c9d1d9;
  --theme-muted: #b0b8c1;
  --theme-line: #30363d;
  --theme-green: #3fb950;
  --theme-blue: #58a6ff;
  --theme-amber: #d2991d;
  --theme-surface: #1c2128;
  --theme-tag-bg: #21262d;
  --theme-tag-text: #e6edf3;
  --theme-shadow: rgba(0,0,0,.20);
  --theme-shadow-hover: rgba(0,0,0,.35);
  --theme-card-hover-border: rgba(63,185,80,.35);
  --theme-status-glow: rgba(63,185,80,.12);
  --theme-green-hover: #2ea844;
  --theme-blue-hover: #79b8ff;
  --theme-panel-rgb: 22, 27, 34;
  --theme-red: #f85149;
  --theme-orange: #f0883e;
  /* Trading variables */
  --trading-bg: #0a0e17;
  --trading-card: #141b26;
  --trading-border: #1e2d40;
  --trading-accent: #4da6ff;
  --trading-green: #00c853;
  --trading-red: #ff3d3d;
  --trading-amber: #ffab00;
  --trading-purple: #b388ff;
  --trading-teal: #00bfa5;
  --trading-text: #e8edf2;
  --trading-secondary: #8b95a5;
  --trading-orange: #ff6d3d;
  --trading-green-bright: #00e676;
}"""

# New pineconnector-aligned dark theme block (matching render.py _css())
new_dark_block = """[data-theme="dark"] {
  color-scheme: dark;
  --theme-bg: #0d1117;
  --theme-panel: #161b22;
  --theme-ink: #e6edf3;
  --theme-muted: #7d8590;
  --theme-line: #30363d;
  --theme-green: #3fb950;
  --theme-blue: #58a6ff;
  --theme-amber: #d2991d;
  --theme-surface: #21262d;
  --theme-tag-bg: #21262d;
  --theme-tag-text: #c9d1d9;
  --theme-shadow: rgba(0,0,0,.40);
  --theme-shadow-hover: rgba(0,0,0,.60);
  --theme-card-hover-border: rgba(63,185,80,.45);
  --theme-status-glow: rgba(63,185,80,.2);
  --theme-green-hover: #4fdc63;
  --theme-blue-hover: #79b8ff;
  --theme-panel-rgb: 22, 27, 34;
  --theme-red: #f85149;
  --theme-orange: #f0883e;
  /* Trading variables */
  --trading-bg: #0a0e17;
  --trading-card: #141b26;
  --trading-border: #1e2d40;
  --trading-accent: #4da6ff;
  --trading-green: #00c853;
  --trading-red: #ff3d3d;
  --trading-amber: #ffab00;
  --trading-purple: #b388ff;
  --trading-teal: #00bfa5;
  --trading-text: #e8edf2;
  --trading-secondary: #8b95a5;
  --trading-orange: #ff6d3d;
  --trading-green-bright: #00e676;
}"""

if old_dark_block in content:
    content = content.replace(old_dark_block, new_dark_block)
    css_path.write_text(content, encoding="utf-8")
    print("[OK] static/style.css dark theme aligned with pineconnector-inspired scheme")
else:
    # Try with different whitespace
    print("[FAIL] Exact dark theme block not found - trying line-by-line update")
    # Fall back to updating individual variables
    lines = content.split('\n')
    in_dark = False
    new_lines = []
    for line in lines:
        if line.strip() == '[data-theme="dark"] {':
            in_dark = True
        elif in_dark and line.strip() == '}':
            in_dark = False
        elif in_dark:
            if '--theme-ink:' in line and '#c9d1d9' in line:
                line = line.replace('#c9d1d9', '#e6edf3')
            elif '--theme-muted:' in line and '#b0b8c1' in line:
                line = line.replace('#b0b8c1', '#7d8590')
            elif '--theme-surface:' in line and '#1c2128' in line:
                line = line.replace('#1c2128', '#21262d')
            elif '--theme-tag-text:' in line and '#e6edf3' in line and '--theme-ink' not in line:
                line = line.replace('#e6edf3', '#c9d1d9')
            elif '--theme-shadow:' in line and '.20' in line:
                line = line.replace('.20)', '.40)')
            elif '--theme-shadow-hover:' in line and '.35' in line:
                line = line.replace('.35)', '.60)')
            elif '--theme-card-hover-border:' in line and '.35)' in line:
                line = line.replace('.35)', '.45)')
            elif '--theme-status-glow:' in line and '.12)' in line:
                line = line.replace('.12)', '.2)')
            elif '--theme-green-hover:' in line and '#2ea844' in line:
                line = line.replace('#2ea844', '#4fdc63')
        new_lines.append(line)
    css_path.write_text('\n'.join(new_lines), encoding="utf-8")
    print("[OK] static/style.css dark theme updated via line-by-line fallback")

# Also align render.py _css() muted color to pineconnector's #7d8590
render_path = Path("portfolio/render.py")
render_content = render_path.read_text(encoding="utf-8")
if '  --theme-muted: #68716d;' in render_content:
    render_content = render_content.replace('  --theme-muted: #68716d;', '  --theme-muted: #7d8590;')
    render_path.write_text(render_content, encoding="utf-8")
    print("[OK] render.py _css() --theme-muted aligned to #7d8590")
else:
    print("[SKIP] render.py already has updated muted color or not found")
