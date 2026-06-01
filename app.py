from pathlib import Path

import gradio as gr

from portfolio.config import load_config
from portfolio.db import get_projects, init_db, seed_projects
from portfolio.project_templates import get_project_templates
from portfolio.render import gradio_tab_switch_js, render_page
from portfolio.financial import render_financial_tab, DARK_CSS
from portfolio.claim_processing.render import render_claim_tab, CLAIM_DARK_CSS
from portfolio.movie_recommender import render_movie_tab, MOVIE_CSS
from portfolio.sentiment import render_sentiment_tab, SENTIMENT_CSS
from portfolio.trading.ui import render_trading_tab, TRADING_CSS
from portfolio.trading_agents_manager import render_trading_agents_tab, TRADING_AGENTS_CSS
from portfolio.underwriting.render import render_underwriting_tab, UNDERWRITING_CSS
from portfolio.resume_matcher import render_resume_matcher_tab, RESUME_MATCHER_CSS


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portfolio.db"
APP_CSS = """
.gradio-container { max-width: none !important; padding: 0 !important; }
footer { display: none !important; }
body, .gradio-container {
  background: var(--theme-bg) !important;
  color: var(--theme-ink) !important;
}
html[data-theme="dark"] body,
html[data-theme="dark"] .gradio-container {
  background: var(--theme-bg) !important;
}
html[data-theme="dark"] .gradio-container,
html[data-theme="dark"] .gradio-container h1,
html[data-theme="dark"] .gradio-container h2,
html[data-theme="dark"] .gradio-container h3,
html[data-theme="dark"] .gradio-container h4,
html[data-theme="dark"] .gradio-container h5,
html[data-theme="dark"] .gradio-container h6,
html[data-theme="dark"] .gradio-container label,
html[data-theme="dark"] .gradio-container th,
html[data-theme="dark"] .gradio-container td {
  color: var(--theme-ink);
}
html[data-theme="dark"] .gradio-container input,
html[data-theme="dark"] .gradio-container textarea,
html[data-theme="dark"] .gradio-container select {
  background: var(--theme-surface) !important;
  color: var(--theme-ink) !important;
  border-color: var(--theme-line) !important;
}
html[data-theme="dark"] .gradio-container input::placeholder,
html[data-theme="dark"] .gradio-container textarea::placeholder {
  color: var(--theme-muted) !important;
}

/* ===== Tighten Gradio Layout ===== */
.tabs { margin-bottom: 0 !important; }
.tabitem { padding: 0 !important; border: none !important; }
.gr-box { border-radius: 0 !important; border: none !important; }
.gr-padded { padding: 8px !important; }
.gr-form { gap: 8px !important; }
.tab-nav, .tabs > .tab-nav {
  display: flex !important;
  flex-wrap: wrap !important;
  justify-content: flex-start !important;
  gap: 2px !important;
  overflow: visible !important;
  background: rgba(var(--theme-panel-rgb), .82) !important;
  border-bottom: 1px solid var(--theme-line) !important;
  backdrop-filter: blur(18px) saturate(160%);
}
.tab-nav button,
.tabs > .tab-nav button {
  flex: 0 1 auto !important;
  max-width: none !important;
  white-space: nowrap !important;
  font-size: 10px !important;
  font-weight: 600 !important;
  padding: 5px 8px !important;
}
button, .gr-button {
  border-radius: 10px !important;
  font-weight: 600 !important;
}
input, textarea, select, .wrap, .container, .block {
  border-color: var(--theme-line) !important;
}
.modern-app-shell,
.app-floating-window,
#financial-tab,
#claim-tab,
#underwriting-tab,
#sentiment-tab,
#movie-tab,
#resume-matcher-tab,
#trading-desk-shell {
  max-width: 1380px;
  margin: 18px auto 34px;
}
.app-floating-window {
  padding: 20px !important;
  background: var(--theme-panel) !important;
  border: 1px solid var(--theme-line) !important;
  border-radius: 18px !important;
  box-shadow: 0 24px 70px var(--theme-shadow) !important;
}
.app-window-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}
.app-window-header h1 {
  margin: 0 0 4px;
  color: var(--theme-ink);
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.08;
}
.app-window-header p {
  margin: 0;
  color: var(--theme-muted);
}
.app-window-badge {
  flex-shrink: 0;
  border: 1px solid rgba(15,143,110,.35);
  border-radius: 999px;
  padding: 7px 12px;
  background: rgba(15,143,110,.1);
  color: var(--theme-green);
  font-size: 12px;
  font-weight: 850;
  text-transform: uppercase;
}
.metric-card,
.claim-metric-card,
.uw-metric-card,
.sent-card,
.sent-col,
.sent-verdict,
.sent-compare-summary,
.ta-card,
.trading-card,
#movie-tab .stat-item,
#movie-tab .pref-section {
  border-radius: 14px !important;
  box-shadow: 0 16px 40px var(--theme-shadow) !important;
}
.metric-card:hover,
.claim-metric-card:hover,
.uw-metric-card:hover,
.sent-card:hover,
.ta-card:hover,
.trading-card:hover {
  box-shadow: 0 24px 58px var(--theme-shadow-hover) !important;
}

/* ===== Theme variable defaults (mirrors render.py for non-landing tabs) ===== */
:root {
  --theme-bg: #eef3f8;
  --theme-panel: #ffffff;
  --theme-ink: #101828;
  --theme-muted: #667085;
  --theme-line: #d9e2ec;
  --theme-line-rgb: 217,226,236;
  --theme-green: #0f8f6e;
  --theme-blue: #2563eb;
  --theme-amber: #b7791f;
  --theme-surface: #f8fafc;
  --theme-tag-bg: #eaf2ff;
  --theme-tag-text: #1d4ed8;
  --theme-red: #dc2626;
  --theme-orange: #ea580c;
  --theme-shadow: rgba(16,24,40,.08);
  --theme-shadow-hover: rgba(16,24,40,.18);
  --theme-panel-rgb: 255,255,255;
  --trading-bg: #eef3f8;
  --trading-card: #ffffff;
  --trading-border: #d9e2ec;
  --trading-accent: #2563eb;
  --trading-green: #0f8f6e;
  --trading-red: #dc2626;
  --trading-amber: #b7791f;
  --trading-purple: #7c3aed;
  --trading-teal: #00897b;
  --trading-text: #101828;
  --trading-secondary: #667085;
  --trading-orange: #ea580c;
  --trading-green-bright: #22c55e;
}
[data-theme="dark"] {
  --theme-bg: #081527;
  --theme-panel: #0f2038;
  --theme-ink: #f7fbff;
  --theme-muted: rgba(226,235,249,.86);
  --theme-line: rgba(166,190,226,.34);
  --theme-line-rgb: 166,190,226;
  --theme-green: #55d6a5;
  --theme-blue: #7cb7ff;
  --theme-amber: #ffd166;
  --theme-surface: #173153;
  --theme-tag-bg: #18385f;
  --theme-tag-text: #f2f7ff;
  --theme-red: #ff7369;
  --theme-orange: #ff9a56;
  --theme-shadow: rgba(0,0,0,.32);
  --theme-shadow-hover: rgba(0,0,0,.48);
  --theme-panel-rgb: 15,32,56;
  --theme-page-top: #0b1b33;
  --theme-page-bottom: #10233f;
  --trading-bg: #081527;
  --trading-card: #0f2038;
  --trading-border: rgba(166,190,226,.34);
  --trading-accent: #7cb7ff;
  --trading-green: #55d6a5;
  --trading-red: #ff7369;
  --trading-amber: #ffd166;
  --trading-purple: #b58cff;
  --trading-teal: #36d1c4;
  --trading-text: #f7fbff;
  --trading-secondary: rgba(226,235,249,.86);
  --trading-orange: #ff9a56;
  --trading-green-bright: #7ae8bf;
}
"""

# Tab navigation labels are now driven by config["tabs"] in portfolio.yaml.
# PORTFOLIO_NAV_JS is generated inside render_page() from the same source.

def build_app() -> gr.Blocks:
    config = load_config()
    tabs_config = config.get("tabs", {})
    project_templates = get_project_templates(config)
    init_db(DB_PATH)
    seed_projects(DB_PATH, project_templates)

    with gr.Blocks(
        title=config["site"]["title"],
        js=gradio_tab_switch_js(),
    ) as demo:
        with gr.Tabs():
            with gr.TabItem("Portfolio"):
                gr.HTML(
                    render_page(get_projects(DB_PATH), mode="gradio", config=config),
                )

            with gr.TabItem(tabs_config.get("trading_agents", "Portfolio Manager")):
                render_trading_agents_tab()

            with gr.TabItem(tabs_config.get("trading", "Trading Desk")):
                render_trading_tab()

            with gr.TabItem(tabs_config.get("underwriting", "Insurance Underwriting")):
                render_underwriting_tab()

            with gr.TabItem(tabs_config.get("claim", "Claim Processing")):
                render_claim_tab()

            with gr.TabItem(tabs_config.get("movie", "Movie Recommendations")):
                render_movie_tab()

            with gr.TabItem(tabs_config.get("sentiment", "Sentiment Analyzer")):
                render_sentiment_tab()

            with gr.TabItem(tabs_config.get("resume_matcher", "Resume Matcher")):
                render_resume_matcher_tab()

            with gr.TabItem(tabs_config.get("financial", "Financial Agent")):
                render_financial_tab()

    return demo


demo = build_app()


if __name__ == "__main__":
    launch_config = load_config()
    demo.launch(
        server_name=launch_config["server"]["host"],
        server_port=launch_config["server"]["port"],
        css=APP_CSS + DARK_CSS + CLAIM_DARK_CSS + MOVIE_CSS + SENTIMENT_CSS + UNDERWRITING_CSS + RESUME_MATCHER_CSS + TRADING_CSS + TRADING_AGENTS_CSS,
    )
