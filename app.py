from pathlib import Path

import gradio as gr

from portfolio.config import load_config
from portfolio.db import get_projects, init_db, seed_projects
from portfolio.project_templates import PROJECT_TEMPLATES
from portfolio.render import render_page
from portfolio.financial import render_financial_tab, DARK_CSS
from portfolio.claim_processing.render import render_claim_tab, CLAIM_DARK_CSS
from portfolio.movie_recommender import render_movie_tab, MOVIE_CSS
from portfolio.sentiment import render_sentiment_tab, SENTIMENT_CSS
from portfolio.trading.ui import render_trading_tab, TRADING_CSS
from portfolio.trading_agents_manager import render_trading_agents_tab, TRADING_AGENTS_CSS


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portfolio.db"
APP_CSS = """
.gradio-container { max-width: none !important; padding: 0 !important; }
footer { display: none !important; }

/* ===== Tighten Gradio Layout ===== */
.tabs { margin-bottom: 0 !important; }
.tabitem { padding: 0 !important; border: none !important; }
.gr-box { border-radius: 0 !important; border: none !important; }
.gr-padded { padding: 8px !important; }
.gr-form { gap: 8px !important; }

/* ===== Theme variable defaults (mirrors render.py for non-landing tabs) ===== */
:root {
  --theme-bg: #f4f6f4;
  --theme-panel: #ffffff;
  --theme-ink: #121413;
  --theme-muted: #68716d;
  --theme-line: #e1e5e2;
  --theme-green: #12785d;
  --theme-blue: #315f9f;
  --theme-amber: #a86c22;
  --theme-surface: #edf5f1;
  --trading-bg: #f4f6f4;
  --trading-card: #ffffff;
  --trading-border: #e1e5e2;
  --trading-accent: #315f9f;
  --trading-green: #16a34a;
  --trading-red: #dc2626;
  --trading-amber: #a86c22;
  --trading-purple: #7c3aed;
  --trading-teal: #00897b;
  --trading-text: #121413;
  --trading-secondary: #68716d;
  --trading-orange: #ea580c;
  --trading-green-bright: #22c55e;
}
[data-theme="dark"] {
  --theme-bg: #0d1117;
  --theme-panel: #161b22;
  --theme-ink: #c9d1d9;
  --theme-muted: #b0b8c1;
  --theme-line: #30363d;
  --theme-green: #3fb950;
  --theme-blue: #58a6ff;
  --theme-amber: #d2991d;
  --theme-surface: #1c2128;
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
}
"""

PORTFOLIO_NAV_JS = """
element.addEventListener('click', function(event) {
  const link = event.target.closest('[data-tab-target]');
  if (!link) {
    return;
  }
  event.preventDefault();
  const labels = {
    financial: 'Financial Agent',
    trading: 'Trading',
    trading_agents: 'TradingAgents Manager',
    claim: 'Claim Processing',
    movie: 'Movie Recommendations',
    sentiment: 'Sentiment Analyzer'
  };
  const label = labels[link.dataset.tabTarget];
  if (!label) {
    return;
  }
  const tabs = Array.from(document.querySelectorAll('button, [role="tab"]'));
  const target = tabs.find(function(tab) {
    return tab.textContent && tab.textContent.trim().indexOf(label) >= 0;
  });
  if (target) {
    target.click();
    target.scrollIntoView({block: 'nearest', inline: 'nearest'});
  }
});
"""


def build_app() -> gr.Blocks:
    config = load_config()
    init_db(DB_PATH)
    seed_projects(DB_PATH, PROJECT_TEMPLATES)

    with gr.Blocks(
        title=config["site"]["title"],
    ) as demo:
        with gr.Tabs():
            with gr.TabItem("Portfolio"):
                gr.HTML(
                    render_page(get_projects(DB_PATH), mode="gradio", config=config),
                )

            with gr.TabItem("Financial Agent"):
                render_financial_tab()

            with gr.TabItem("Claim Processing"):
                render_claim_tab()

            with gr.TabItem("Movie Recommendations"):
                render_movie_tab()

            with gr.TabItem("Sentiment Analyzer"):
                render_sentiment_tab()

            with gr.TabItem("TradingAgents Manager"):
                render_trading_agents_tab()

            with gr.TabItem("Trading"):
                render_trading_tab()

    return demo


demo = build_app()


if __name__ == "__main__":
    launch_config = load_config()
    demo.launch(
        server_name=launch_config["server"]["host"],
        server_port=launch_config["server"]["port"],
        css=APP_CSS + DARK_CSS + CLAIM_DARK_CSS + MOVIE_CSS + SENTIMENT_CSS + TRADING_CSS + TRADING_AGENTS_CSS,
    )
