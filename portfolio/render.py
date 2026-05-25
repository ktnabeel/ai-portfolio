from html import escape
from typing import Any

from .config import load_config
from .models import Project

# Map project titles to Gradio tab IDs for contextual in-app navigation.
_TAB_LINKS: dict[str, str] = {
    "Trading Agents": "trading",
    "Claim Processing": "claim",
    "Movie Recommendations": "movie",
    "Product Review Sentiment Analyzer": "sentiment",
}

# Rich inline detail content for each project — used in static (Vercel) deployment
# to provide self-contained expandable cards with no external links.
_PROJECT_DETAILS: dict[str, str] = {
    "Trading Agents": """
<div class="detail-grid">
  <div class="detail-section">
    <h4>Architecture</h4>
    <p>Multi-agent LangGraph pipeline: Security &rarr; Risk/Sentiment &rarr; Regime &rarr; Decision &rarr; Execution. Each agent contributes a specialized signal to the final trading decision.</p>
  </div>
  <div class="detail-section">
    <h4>Key Capabilities</h4>
    <ul>
      <li>Black-Scholes options pricing engine</li>
      <li>MCP paper-trading server for safe simulation</li>
      <li>Real-time market data via yfinance</li>
      <li>CNN Fear &amp; Greed index scraper</li>
      <li>Financial news sentiment scraping</li>
      <li>Polygon.io options chain integration</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>LangGraph, LangChain (GPT-4o reasoning), yfinance, BeautifulSoup4, NumPy/SciPy, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>LLM agents analyze market regimes, assess risk-reward profiles, and generate structured trading decisions — all orchestrated through a state graph with human-in-the-loop review.</p>
  </div>
</div>""",
    "Claim Processing": """
<div class="detail-grid">
  <div class="detail-section">
    <h4>Architecture</h4>
    <p>Pipeline: Extract &rarr; Fraud Detection &rarr; Severity Classification &rarr; Routing. Free-text claims are parsed into structured data, analyzed for red flags, and automatically routed.</p>
  </div>
  <div class="detail-section">
    <h4>Key Capabilities</h4>
    <ul>
      <li>NLP extraction: claimant, amount, policy number, incident date</li>
      <li>Pattern-based fraud detection with 10+ red-flag rules</li>
      <li>Severity classification (Low &rarr; Critical) based on claim amount and type</li>
      <li>Routing engine: Approve / Review / Deny / Escalate</li>
      <li>Batch processing with summary statistics</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>Python, regex NLP, rule-based inference, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Automates the manual intake-review-route workflow. Extracts structured data from unstructured text, scores fraud risk heuristically, and recommends routing — reducing adjuster workload.</p>
  </div>
</div>""",
    "Insurance Underwriting Agent": """
<div class="detail-grid">
  <div class="detail-section">
    <h4>Status</h4>
    <p>Template — ready for customization with your underwriting rules and policy data.</p>
  </div>
  <div class="detail-section">
    <h4>Planned Capabilities</h4>
    <ul>
      <li>Risk review automation with configurable rule engine</li>
      <li>Policy context retrieval and comparison</li>
      <li>LLM-powered recommendation generation</li>
      <li>Multi-factor risk scoring</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>Python, LLM agents, underwriting rules, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Agentic assistant that reviews applications against underwriting guidelines, surfaces risk factors, and generates structured recommendations for underwriter review.</p>
  </div>
</div>""",
    "Product Review Sentiment Analyzer": """
<div class="detail-grid">
  <div class="detail-section">
    <h4>Architecture</h4>
    <p>Pipeline: Data Loading &rarr; Sentiment Classification &rarr; Aggregation &rarr; Summarization. Processes product reviews individually and rolls up insights per product.</p>
  </div>
  <div class="detail-section">
    <h4>Key Capabilities</h4>
    <ul>
      <li>Per-review sentiment classification (Positive / Neutral / Negative)</li>
      <li>Product-level aggregation with confidence scoring</li>
      <li>Keyword extraction from review text</li>
      <li>Amazon review dataset integration (sampled)</li>
      <li>Visual sentiment distribution charts</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>Python, scikit-learn, HuggingFace datasets, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Transforms unstructured customer reviews into structured sentiment insights. Useful for product teams tracking feedback trends and identifying pain points at scale.</p>
  </div>
</div>""",
    "Finance Planning": """
<div class="detail-grid">
  <div class="detail-section">
    <h4>Status</h4>
    <p>Template — ready for customization with your financial models and planning workflows.</p>
  </div>
  <div class="detail-section">
    <h4>Planned Capabilities</h4>
    <ul>
      <li>Budget analysis and scenario modeling</li>
      <li>Financial goal tracking with progress visualization</li>
      <li>LLM-powered planning assistant</li>
      <li>Cash flow projections</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>Python, analytics, LLM workflows, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Conversational planning assistant that helps users model financial scenarios, track goals, and get AI-generated recommendations based on their financial data.</p>
  </div>
</div>""",
    "Movie Recommendations": """
<div class="detail-grid">
  <div class="detail-section">
    <h4>Architecture</h4>
    <p>Ensemble recommender: Two-Tower Embeddings + SVD Collaborative Filtering + Popularity baseline. LLM-style preference parser extracts structured tastes from free-text input.</p>
  </div>
  <div class="detail-section">
    <h4>Key Capabilities</h4>
    <ul>
      <li>Two-tower neural model (MovieEmbedder + UserEmbedder)</li>
      <li>SVD matrix factorization for collaborative filtering</li>
      <li>LLM-style preference parsing from natural language</li>
      <li>TMDB API integration with rate limiting and image CDN</li>
      <li>Fallback sample dataset when API key not configured</li>
      <li>Weighted ensemble blending multiple signal sources</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>Python, scikit-learn, NumPy, TMDB API, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Translates natural-language taste descriptions (\"I love dark sci-fi like Blade Runner\") into structured embeddings, then blends content-based and collaborative signals for personalized recommendations.</p>
  </div>
</div>""",
}


def _tab_link(target: str, label: str, class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return f'<a href="#" data-tab-target="{escape(target)}"{class_attr}>{escape(label)}</a>'


def render_page(projects: list[Project], mode: str = "static", config: dict[str, Any] | None = None) -> str:
    config = config or load_config()
    site = config["site"]
    page = _render_shell(_render_project_grid(projects, mode=mode), config, mode=mode)
    nav_js = """
    (function() {
      const initNav = function() {
        document.addEventListener('click', function(event) {
          const link = event.target.closest('[data-tab-target]');
          if (!link) return;
          event.preventDefault();
          const labels = {
            financial: 'Financial Agent',
            trading: 'Trading',
            claim: 'Claim Processing',
            movie: 'Movie Recommendations',
            sentiment: 'Sentiment Analyzer'
          };
          const label = labels[link.dataset.tabTarget];
          if (!label) return;
          const tabs = Array.from(document.querySelectorAll('button, [role="tab"]'));
          const target = tabs.find(function(tab) {
            return tab.textContent && tab.textContent.trim().indexOf(label) >= 0;
          });
          if (target) {
            target.click();
            target.scrollIntoView({block: 'nearest', inline: 'nearest'});
          }
        });
      };
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNav);
      } else {
        initNav();
      }
    })();
    """

    if mode == "gradio":
        return f"<style>{_css()}</style><script>(function(){{var t;try{{t=localStorage.getItem('theme')}}catch(e){{}}if(t)document.documentElement.setAttribute('data-theme',t);else if(window.matchMedia('(prefers-color-scheme:dark)').matches)document.documentElement.setAttribute('data-theme','dark');}})(); {nav_js}</script>{page}"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(site["meta_description"])}">
  <title>{escape(site["title"])}</title>
  <style>{_css()}</style>
</head>
<body>
  {page}
  <script>
    function toggleExpand(index) {{
      var card = document.getElementById('card-' + index);
      var btn = card.querySelector('.expand-toggle');
      var isExpanded = card.classList.contains('expanded');
      // Close all other expanded cards
      document.querySelectorAll('.project-card.expanded').forEach(function(c) {{
        if (c !== card) {{
          c.classList.remove('expanded');
          var b = c.querySelector('.expand-toggle');
          if (b) b.setAttribute('aria-expanded', 'false');
        }}
      }});
      if (isExpanded) {{
        card.classList.remove('expanded');
        btn.setAttribute('aria-expanded', 'false');
      }} else {{
        card.classList.add('expanded');
        btn.setAttribute('aria-expanded', 'true');
        // Scroll into view if needed
        setTimeout(function() {{
          card.scrollIntoView({{behavior: 'smooth', block: 'nearest'}});
        }}, 100);
      }}
    }}
  </script>
</body>
</html>"""


def _render_shell(projects_html: str, config: dict[str, Any], mode: str) -> str:
    site = config["site"]
    capabilities = config["capabilities"]
    tab_nav_html = ""
    if mode == "gradio":
        tab_nav_html = "\n          ".join(
            [
                _tab_link("financial", "Financial Agent", "financial-nav-link"),
                _tab_link("trading", "Trading", "trading-nav-link"),
                _tab_link("claim", "Claim Processing", "claim-nav-link"),
                _tab_link("movie", "Movies", "movie-nav-link"),
                _tab_link("sentiment", "Sentiment", "sentiment-nav-link"),
            ]
        )
    capabilities_html = "\n".join(
        f"<div><strong>{escape(str(item['title']))}</strong><span>{escape(str(item['description']))}</span></div>"
        for item in capabilities
    )

    return f"""
  <main class="portfolio-page">
    <section class="workspace">
      <header class="top-bar">
        <div>
          <span class="status-dot"></span>
          {escape(site["status_label"])}
        </div>
        <nav aria-label="Portfolio navigation">
          <a href="#projects">Projects</a>
          {tab_nav_html}
          <a href="{escape(site["linkedin_url"])}" target="_blank" rel="noreferrer">Contact</a>
          <button class="theme-toggle" onclick="(function(){{var h=document.documentElement;var t=h.getAttribute('data-theme')==='dark'?'light':'dark';h.setAttribute('data-theme',t);try{{localStorage.setItem('theme',t)}}catch(e){{}}}})();" aria-label="Toggle dark/light theme" title="Toggle theme">
            <span class="theme-icon-light">☀️</span>
            <span class="theme-icon-dark">🌙</span>
          </button>
        </nav>
      </header>

      <section class="intro">
        <p class="eyebrow">{escape(site["intro_kicker"])}</p>
        <h2>{escape(site["intro_headline"])}</h2>
        <p>{escape(site["intro_copy"])}</p>
      </section>

      <section class="capability-strip" aria-label="Capabilities">
        {capabilities_html}
      </section>

      <section id="projects" class="projects-section">
        <div class="section-heading">
          <p class="eyebrow">{escape(site["project_kicker"])}</p>
          <h2>{escape(site["project_heading"])}</h2>
        </div>
        {projects_html}
      </section>
    </section>
  </main>"""


def _render_project_grid(projects: list[Project], mode: str) -> str:
    if not projects:
        return """
        <div class="empty-state">
          <h3>Real project entries are ready to be added.</h3>
          <p>This portfolio is intentionally empty until real AI projects are added.</p>
        </div>
"""

    cards = "\n".join(_render_project_card(index, project, mode=mode) for index, project in enumerate(projects, start=1))
    return f'<div class="project-list">{cards}</div>'


def _render_project_card(index: int, project: Project, mode: str) -> str:
    tags = "".join(f"<span>{escape(tag)}</span>" for tag in project.tags)
    links = []
    if project.github_url:
        links.append(f'<a href="{escape(project.github_url)}" target="_blank" rel="noreferrer">GitHub</a>')
    if project.demo_url:
        links.append(f'<a href="{escape(project.demo_url)}" target="_blank" rel="noreferrer">Demo</a>')

    # Contextual in-app tab navigation for Built projects inside the Gradio app.
    tab_label = _TAB_LINKS.get(project.title)
    if mode == "gradio" and not project.github_url and not project.demo_url and project.status == "Built" and tab_label:
        links.append(_tab_link(tab_label, "Demo"))

    # Static deployment: expandable inline details instead of external links.
    expand_html = ""
    if mode == "static":
        details = _PROJECT_DETAILS.get(project.title, "")
        if details:
            expand_html = f"""
          <div class="project-expand" id="expand-{index}">
            {details}
          </div>"""
            links.append(
                f'<button class="expand-toggle" onclick="toggleExpand({index})"'
                f' aria-expanded="false" aria-controls="expand-{index}">'
                f'Details</button>'
            )
        elif not project.github_url and not project.demo_url:
            links.append('<span class="muted">Links coming soon</span>')

    link_html = "".join(links) or '<span class="muted">Links coming soon</span>'

    return f"""
        <article class="project-card" id="card-{index}">
          <div class="project-number">{index:02d}</div>
          <div class="project-main">
            <div class="project-meta">
              <span>{escape(project.status)}</span>
              <span>{escape(project.tech_stack)}</span>
            </div>
            <h3>{escape(project.title)}</h3>
            <p>{escape(project.outcome)}</p>
            <div class="tag-row">{tags}</div>
          </div>
          <div class="project-links">{link_html}</div>
          {expand_html}
        </article>
"""


def _css() -> str:
    return """
/* ===== Light Theme (default) ===== */
:root {
  color-scheme: light;
  --theme-bg: #f4f6f4;
  --theme-panel: #ffffff;
  --theme-ink: #121413;
  --theme-muted: #68716d;
  --theme-line: #e1e5e2;
  --theme-green: #12785d;
  --theme-blue: #315f9f;
  --theme-amber: #a86c22;
  --theme-surface: #edf5f1;
  --theme-tag-bg: #f0f3f1;
  --theme-tag-text: #34403b;
  --theme-shadow: rgba(18,20,19,.04);
  --theme-shadow-hover: rgba(18,20,19,.08);
  --theme-card-hover-border: rgba(18,120,93,.35);
  --theme-status-glow: rgba(18,120,93,.12);
  --theme-green-hover: #0d5e48;
  --theme-blue-hover: #1f4270;
  --theme-panel-rgb: 255, 255, 255;
}

/* ===== Dark Theme ===== */
[data-theme="dark"] {
  color-scheme: dark;
  --theme-bg: #0d1117;
  --theme-panel: #161b22;
  --theme-ink: #e6edf3;
  --theme-muted: #8b949e;
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
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 100px; }
body {
  margin: 0;
  background: var(--theme-bg);
  color: var(--theme-ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  transition: background-color .3s ease, color .3s ease;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
a { color: inherit; }

.portfolio-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr;
}
.eyebrow {
  margin: 0 0 12px;
  color: var(--theme-green);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1, h2, h3, p { margin-top: 0; }

.workspace {
  min-width: 0;
  padding: 16px;
}
.top-bar {
  position: sticky;
  top: 10px;
  z-index: 100;
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border: 1px solid var(--theme-line);
  border-radius: 14px;
  padding: 0 20px;
  background: rgba(var(--theme-panel-rgb), 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: 0 4px 24px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06);
  transition: box-shadow .35s ease, background .35s ease, border-color .35s ease, transform .35s ease;
}
.top-bar div {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: var(--theme-muted);
  font-size: 14px;
  font-weight: 800;
}
.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--theme-green);
  box-shadow: 0 0 0 5px var(--theme-status-glow);
}
.top-bar nav {
  display: flex;
  gap: 16px;
  align-items: center;
  color: var(--theme-ink);
  font-size: 14px;
}
.top-bar nav a.financial-nav-link {
  color: var(--theme-green);
  font-weight: 850;
}
.top-bar nav a.financial-nav-link:hover {
  color: var(--theme-green-hover);
}
.top-bar nav a.claim-nav-link {
  color: var(--theme-blue);
  font-weight: 850;
}
.top-bar nav a.claim-nav-link:hover {
  color: var(--theme-blue-hover);
}
.top-bar nav a.movie-nav-link {
  color: var(--theme-amber);
  font-weight: 850;
}
.top-bar nav a.movie-nav-link:hover {
  color: var(--theme-movie-link-text);
}
.top-bar nav a.sentiment-nav-link {
  color: var(--theme-sentiment-link-text);
  font-weight: 850;
}
.top-bar nav a.sentiment-nav-link:hover {
  color: var(--theme-sentiment-link-text);
}
.top-bar nav a.trading-nav-link {
  color: var(--theme-trading-link-text);
  font-weight: 850;
}
.top-bar nav a.trading-nav-link:hover {
  color: var(--theme-trading-link-text);
}

/* ===== Theme Toggle ===== */
.theme-toggle {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 1px solid var(--theme-line);
  border-radius: 8px;
  background: var(--theme-panel);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  padding: 0;
  transition: border-color .18s ease, background .18s ease;
}
.theme-toggle:hover {
  border-color: var(--theme-green);
  background: var(--theme-surface);
}
.theme-icon-light,
.theme-icon-dark {
  font-size: 18px;
  line-height: 1;
  transition: opacity .25s ease, transform .25s ease;
  position: absolute;
}
.theme-icon-light { opacity: 1; transform: scale(1); }
.theme-icon-dark  { opacity: 0; transform: scale(0.5); }
[data-theme="dark"] .theme-icon-light { opacity: 0; transform: scale(0.5); }
[data-theme="dark"] .theme-icon-dark  { opacity: 1; transform: scale(1); }

.intro {
  padding: 40px 8px 24px;
  max-width: 940px;
}
.intro h2 {
  margin-bottom: 18px;
  font-size: clamp(42px, 6vw, 78px);
  line-height: .95;
  letter-spacing: 0;
}
.intro p:not(.eyebrow) {
  max-width: 720px;
  color: var(--theme-muted);
  font-size: 18px;
  line-height: 1.75;
}
.capability-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 32px;
}
.capability-strip div {
  min-height: 100px;
  border: 1px solid var(--theme-line);
  border-radius: 12px;
  padding: 16px;
  background: var(--theme-panel);
  box-shadow: 0 2px 12px var(--theme-shadow);
  transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
}
.capability-strip div:hover {
  transform: translateY(-4px);
  border-color: var(--theme-card-hover-border);
  box-shadow: 0 12px 32px var(--theme-shadow-hover);
}
.capability-strip strong,
.capability-strip span {
  display: block;
}
.capability-strip strong {
  margin-bottom: 8px;
  font-size: 18px;
}
.capability-strip span {
  color: var(--theme-muted);
}
.projects-section {
  padding-bottom: 40px;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  margin-bottom: 18px;
}
.section-heading h2 {
  margin: 0;
  font-size: 36px;
  line-height: 1.05;
}
.project-list {
  display: grid;
  gap: 12px;
}
.project-card {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  gap: 22px;
  align-items: center;
  border: 1px solid var(--theme-line);
  border-radius: 14px;
  padding: 16px;
  background: var(--theme-panel);
  box-shadow: 0 4px 20px var(--theme-shadow);
  transition: border-color .25s ease, transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease;
}
.project-card:hover {
  transform: translateY(-6px) scale(1.008);
  border-color: var(--theme-card-hover-border);
  box-shadow: 0 20px 48px var(--theme-shadow-hover);
}
.project-number {
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--theme-surface);
  color: var(--theme-green);
  font-weight: 950;
}
.project-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.project-meta span {
  display: inline-flex;
  border: 1px solid var(--theme-line);
  border-radius: 999px;
  padding: 5px 9px;
  color: var(--theme-muted);
  font-size: 12px;
  font-weight: 760;
}
.project-card h3 {
  margin-bottom: 8px;
  font-size: 24px;
  line-height: 1.2;
}
.project-card p {
  max-width: 780px;
  margin-bottom: 14px;
  color: var(--theme-muted);
  line-height: 1.6;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag-row span {
  border-radius: 999px;
  padding: 6px 9px;
  background: var(--theme-tag-bg);
  color: var(--theme-tag-text);
  font-size: 12px;
  font-weight: 750;
}
.project-links {
  min-width: 128px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  color: var(--theme-blue);
  font-size: 14px;
}
.muted { color: var(--theme-muted); font-weight: 750; }

/* ===== Expandable project card details ===== */
.expand-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--theme-line);
  border-radius: 8px;
  padding: 8px 16px;
  background: var(--theme-surface);
  color: var(--theme-green);
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
  white-space: nowrap;
  transition: background .2s ease, border-color .2s ease, color .2s ease, transform .15s ease;
}
.expand-toggle::after {
  content: "▸";
  font-size: 10px;
  transition: transform .3s ease;
}
.expand-toggle:hover {
  background: var(--theme-green);
  border-color: var(--theme-green);
  color: #fff;
}
.expand-toggle:active {
  transform: scale(.95);
}
.project-card.expanded .expand-toggle::after {
  transform: rotate(90deg);
}
.project-expand {
  grid-column: 1 / -1;
  display: grid;
  grid-template-rows: 0fr;
  overflow: hidden;
  transition: grid-template-rows .4s cubic-bezier(.4,0,.2,1), padding .35s ease, border-color .35s ease;
  border-top: 0px solid transparent;
}
.project-card.expanded .project-expand {
  grid-template-rows: 1fr;
  border-top: 1px solid var(--theme-line);
  margin-top: 8px;
  padding-top: 20px;
}
.project-expand > :first-child {
  min-height: 0;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.detail-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 850;
  color: var(--theme-green);
  text-transform: uppercase;
  letter-spacing: .02em;
}
.detail-section p,
.detail-section ul {
  margin: 0;
  color: var(--theme-muted);
  font-size: 14px;
  line-height: 1.6;
}
.detail-section ul {
  padding-left: 18px;
  list-style: "— ";
}
.detail-section ul li {
  margin-bottom: 4px;
}
@media (max-width: 720px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
  .project-card.expanded .project-expand {
    padding-top: 14px;
  }
}

.empty-state {
  border: 1px solid var(--theme-line);
  border-radius: 12px;
  padding: 28px;
  background: var(--theme-panel);
}
.empty-state p {
  color: var(--theme-muted);
}

@media (max-width: 980px) {
  .capability-strip {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 720px) {
  .workspace {
    padding: 12px;
  }
  .top-bar {
    align-items: stretch;
    flex-direction: column;
    height: auto;
    min-height: 0;
    padding: 16px;
    gap: 12px;
  }
  .top-bar div {
    margin-bottom: 0;
  }
  .top-bar nav {
    flex-wrap: wrap;
    gap: 12px;
    justify-content: flex-start;
  }
  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .intro {
    padding: 40px 0 30px;
  }
  .intro h2 {
    font-size: 42px;
  }
  .project-card {
    grid-template-columns: 1fr;
    align-items: start;
    padding: 20px;
  }
  .project-links {
    justify-content: flex-start;
    margin-top: 12px;
  }
}
"""
