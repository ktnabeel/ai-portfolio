import json
from html import escape
from typing import Any

from .config import load_config
from .models import Project

def _tab_links_from_config(config: dict[str, Any]) -> dict[str, str]:
    """Return project-title → tab-id mapping from config's project_tab_links."""
    return config.get("project_tab_links", {})


def _tab_labels_from_config(config: dict[str, Any]) -> dict[str, str]:
    """Return tab-id → display-label mapping from config's tabs."""
    return config.get("tabs", {})

# Rich inline detail content for each project — used in static (Vercel) deployment
# to provide self-contained expandable cards with no external links.
_PROJECT_DETAILS: dict[str, str] = {
    "Portfolio Manager": """
<div class="detail-grid">
  <div class="detail-section">
    <h4>Architecture</h4>
    <p>FastAPI service wrapping a LangGraph multi-agent pipeline: Security → Risk/Sentiment → Regime → Decision → Execution → Portfolio Manager. Each agent contributes structured analysis to the final Buy/Sell/Hold rating.</p>
  </div>
  <div class="detail-section">
    <h4>Key Capabilities</h4>
    <ul>
      <li>REST API with FastAPI + Pydantic models (/docs for Swagger UI)</li>
      <li>6-agent orchestrated pipeline (Security, Sentiment, Regime, Decision, Execution, PM)</li>
      <li>Real-time market data via yfinance</li>
      <li>CNN Fear &amp; Greed index sentiment analysis</li>
      <li>Paper-trade execution with simulated broker</li>
      <li>Structured Buy/Sell/Hold portfolio ratings with confidence scores</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>FastAPI, LangGraph, LangChain (GPT-4o), yfinance, Pydantic v2, Uvicorn, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Production-grade portfolio management API that orchestrates specialized LLM agents to analyze stocks across market data, technicals, fundamentals, sentiment, and risk — then synthesizes a structured trading decision with rationale.</p>
  </div>
</div>""",
    "Trading Desk": """
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
    <h4>Architecture</h4>
    <p>Four-dimension risk assessment pipeline: Health → Occupation → Lifestyle → Financial. Each dimension applies rule-based pattern matching to identify risk factors, computes an aggregate risk score (0–100), and drives a structured underwriting decision.</p>
  </div>
  <div class="detail-section">
    <h4>Key Capabilities</h4>
    <ul>
      <li>NLP extraction: applicant name, age, occupation, income, coverage, product type</li>
      <li>40+ risk factor rules across health, occupation, lifestyle, and financial dimensions</li>
      <li>Aggregate risk scoring with severity-weighted calculation (0–100)</li>
      <li>Policy context builder: product matching, premium band, exclusions, riders</li>
      <li>Decision engine: Approve / Decline / Refer / Request Info with chain-of-thought</li>
      <li>Batch processing with summary statistics</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>Python, regex NLP, rule-based inference, risk scoring engine, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Agentic assistant that extracts structured data from free-text applications, evaluates 40+ risk rules across four dimensions, computes severity-weighted risk scores, and generates auditable chain-of-thought recommendations — reducing underwriter cognitive load while maintaining explainability.</p>
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
    <h4>Architecture</h4>
    <p>Multi-agent financial decision pipeline: Market Data → Technical → Fundamental → Sentiment → Risk → Orchestrator. Each agent contributes a specialized signal to portfolio recommendations.</p>
  </div>
  <div class="detail-section">
    <h4>Key Capabilities</h4>
    <ul>
      <li>Budget analysis and scenario modeling</li>
      <li>Financial goal tracking with progress visualization</li>
      <li>Multi-agent portfolio decision system</li>
      <li>Technical & fundamental analysis agents</li>
      <li>Risk assessment and exposure scoring</li>
    </ul>
  </div>
  <div class="detail-section">
    <h4>Stack</h4>
    <p>Python, yfinance, NumPy, Gradio UI</p>
  </div>
  <div class="detail-section">
    <h4>AI Application</h4>
    <p>Orchestrated agent pipeline that analyzes stocks across multiple dimensions — market data, technical indicators, fundamentals, sentiment, and risk — then combines signals into actionable portfolio decisions.</p>
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


def _tab_link(display_label: str, link_label: str, class_name: str = "") -> str:
    """Generate a button that navigates to the matching Gradio tab."""
    class_attr = ' class="' + class_name + '"' if class_name else ""
    js_label = json.dumps(display_label)
    js = (
        "(function(){"
        f"var label={js_label};"
        "var clean=function(s){return (s||'').replace(/\\s+/g,' ').trim();};"
        "var wanted=clean(label);"
        "var tabs=Array.from(document.querySelectorAll('[role=\"tab\"],button'));"
        "var b=tabs.find(function(x){return clean(x.textContent)===wanted;})||"
        "tabs.find(function(x){return clean(x.textContent).indexOf(wanted)>=0;});"
        "if(b){b.click();setTimeout(function(){b.scrollIntoView({block:'nearest',inline:'nearest'});},50);}"
        "})();return false"
    )
    return (
        '<button type="button" onclick="'
        + escape(js)
        + '"'
        + class_attr
        + '>'
        + escape(link_label)
        + "</button>"
    )


def render_page(projects: list[Project], mode: str = "static", config: dict[str, Any] | None = None) -> str:
    config = config or load_config()
    site = config["site"]
    tab_links = _tab_links_from_config(config)
    tab_labels = _tab_labels_from_config(config)
    page = _render_shell(
        _render_project_grid(projects, mode=mode, tab_links=tab_links, tab_labels=tab_labels),
        config,
        mode=mode,
    )

    if mode == "gradio":
        theme_init_js = (
            "<script>(function(){"
            "var t;try{t=localStorage.getItem('theme')}catch(e){};"
            "if(t){document.documentElement.setAttribute('data-theme',t)}"
            "else if(window.matchMedia('(prefers-color-scheme:dark)').matches)"
            "{document.documentElement.setAttribute('data-theme','dark')};"
            "})();</script>"
        )
        return f"<style>{_css()}</style>{theme_init_js}{page}"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(site["meta_description"])}">
  <title>{escape(site["title"])}</title>
  <script>
    (function(){{
      var t;
      try {{ t = localStorage.getItem('theme'); }} catch (e) {{}}
      if (t) {{
        document.documentElement.setAttribute('data-theme', t);
      }} else if (window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches) {{
        document.documentElement.setAttribute('data-theme', 'dark');
      }}
    }})();
  </script>
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
    stats = config.get("stats", [])

    capabilities_html = "\n".join(
        f"<div><strong>{escape(str(item['title']))}</strong><span>{escape(str(item['description']))}</span></div>"
        for item in capabilities
    )

    stats_html = "\n".join(
        f"""<div class="stat-item">
          <span class="stat-value">{escape(str(item['value']))}</span>
          <span class="stat-label">{escape(str(item['label']))}</span>
        </div>"""
        for item in stats
    )

    return f"""
  <main class="portfolio-page">
    <section class="workspace">
      <header class="top-bar">
        <div>
          <span class="status-dot"></span>
          {escape(site["status_label"])}
          <span class="top-bar-sep"></span>
          <a href="{escape(site["linkedin_url"])}" target="_blank" rel="noreferrer" class="top-bar-contact">Contact</a>
          <button class="theme-toggle" onclick="(function(){{var h=document.documentElement;var t=h.getAttribute('data-theme')==='dark'?'light':'dark';h.setAttribute('data-theme',t);try{{localStorage.setItem('theme',t)}}catch(e){{}}}})();" aria-label="Toggle dark/light theme" title="Toggle theme">
            <span class="theme-icon-light">☀️</span>
            <span class="theme-icon-dark">🌙</span>
          </button>
        </div>
      </header>

      <section class="intro">
        <p class="eyebrow">{escape(site["intro_kicker"])}</p>
        <h2>{escape(site["intro_headline"])}</h2>
        <p>{escape(site["intro_copy"])}</p>
      </section>

      <section class="stats-strip" aria-label="Key stats">
        {stats_html}
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


def _render_project_grid(
    projects: list[Project],
    mode: str,
    tab_links: dict[str, str] | None = None,
    tab_labels: dict[str, str] | None = None,
) -> str:
    if not projects:
        return """
        <div class="empty-state">
          <h3>Real project entries are ready to be added.</h3>
          <p>This portfolio is intentionally empty until real AI projects are added.</p>
        </div>
"""

    cards = "\n".join(
        _render_project_card(index, project, mode=mode, tab_links=tab_links, tab_labels=tab_labels)
        for index, project in enumerate(projects, start=1)
    )
    return f'<div class="project-list">{cards}</div>'


def _render_project_card(
    index: int,
    project: Project,
    mode: str,
    tab_links: dict[str, str] | None = None,
    tab_labels: dict[str, str] | None = None,
) -> str:
    if tab_links is None:
        tab_links = {}
    if tab_labels is None:
        tab_labels = {}
    tags = "".join(f"<span>{escape(tag)}</span>" for tag in project.tags)
    links = []
    if project.github_url:
        links.append(f'<a href="{escape(project.github_url)}" target="_blank" rel="noreferrer" class="card-link card-link-github">GitHub</a>')
    if project.demo_url:
        links.append(f'<a href="{escape(project.demo_url)}" target="_blank" rel="noreferrer" class="card-link card-link-external">Demo</a>')

    # In-app tab navigation for all Built projects with a mapped tab (gradio mode).
    tab_id = tab_links.get(project.title)
    if mode == "gradio" and project.status == "Built" and tab_id:
        display_label = tab_labels.get(tab_id, tab_id)
        links.append(_tab_link(display_label, "Open", "card-link card-link-demo"))

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
  --theme-bg: #eef3f8;
  --theme-panel: #ffffff;
  --theme-ink: #101828;
  --theme-muted: #667085;
  --theme-line: #d9e2ec;
  --theme-green: #0f8f6e;
  --theme-blue: #2563eb;
  --theme-amber: #b7791f;
  --theme-surface: #f8fafc;
  --theme-tag-bg: #eaf2ff;
  --theme-tag-text: #1d4ed8;
  --theme-shadow: rgba(16,24,40,.08);
  --theme-shadow-hover: rgba(16,24,40,.18);
  --theme-card-hover-border: rgba(37,99,235,.35);
  --theme-status-glow: rgba(15,143,110,.16);
  --theme-green-hover: #0b7057;
  --theme-blue-hover: #1d4ed8;
  --theme-panel-rgb: 255, 255, 255;
}

/* ===== Dark Theme ===== */
[data-theme="dark"] {
  color-scheme: dark;
  --theme-bg: #2f3437;
  --theme-panel: #373c3f;
  --theme-ink: rgba(255,255,255,.92);
  --theme-muted: rgba(255,255,255,.68);
  --theme-line: rgba(255,255,255,.14);
  --theme-green: #37c78a;
  --theme-blue: #1ca0f1;
  --theme-amber: #dfab01;
  --theme-surface: #454b4e;
  --theme-tag-bg: #454b4e;
  --theme-tag-text: rgba(255,255,255,.86);
  --theme-shadow: rgba(0,0,0,.28);
  --theme-shadow-hover: rgba(0,0,0,.45);
  --theme-card-hover-border: rgba(28,160,241,.52);
  --theme-status-glow: rgba(55,199,138,.22);
  --theme-green-hover: #4ee39f;
  --theme-blue-hover: #60bdf5;
  --theme-panel-rgb: 55, 60, 63;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 100px; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 16% 0%, rgba(37,99,235,.12), transparent 34%),
    linear-gradient(180deg, #f8fbff 0%, var(--theme-bg) 48%, #e8eef6 100%);
  color: var(--theme-ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  transition: background-color .3s ease, color .3s ease;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
[data-theme="dark"] body {
  background:
    radial-gradient(circle at 16% 0%, rgba(28,160,241,.12), transparent 34%),
    linear-gradient(180deg, #252a2d 0%, var(--theme-bg) 54%, #272d30 100%);
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
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  padding: 18px;
}
.top-bar {
  position: sticky;
  top: 10px;
  z-index: 100;
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: nowrap;
  gap: 12px;
  border: 1px solid var(--theme-line);
  border-radius: 16px;
  padding: 0 16px;
  background: rgba(var(--theme-panel-rgb), 0.82);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: 0 16px 44px var(--theme-shadow), 0 1px 2px rgba(16,24,40,.06);
  transition: box-shadow .35s ease, background .35s ease, border-color .35s ease, transform .35s ease;
}
.top-bar div {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  gap: 7px;
  color: var(--theme-muted);
  font-size: 13px;
  font-weight: 800;
}
.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--theme-green);
  box-shadow: 0 0 0 5px var(--theme-status-glow);
}
.top-bar-sep {
  display: inline-block;
  width: 1px;
  height: 18px;
  background: var(--theme-line);
  margin: 0 1px;
  flex-shrink: 0;
}
.top-bar-contact {
  color: var(--theme-blue) !important;
  font-weight: 850;
  text-decoration: none;
  transition: color .18s ease;
}
.top-bar-contact:hover {
  color: var(--theme-blue-hover) !important;
}


/* ===== Theme Toggle ===== */
.theme-toggle {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
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
  padding: 48px 8px 30px;
  max-width: 980px;
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

/* ===== Stats Strip ===== */
.stats-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--theme-line);
  border-radius: 14px;
  padding: 16px 20px;
  background: rgba(var(--theme-panel-rgb), .9);
  box-shadow: 0 14px 34px var(--theme-shadow);
  transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
}
.stat-item:hover {
  transform: translateY(-3px);
  border-color: var(--theme-card-hover-border);
  box-shadow: 0 8px 24px var(--theme-shadow-hover);
}
.stat-value {
  font-size: 28px;
  font-weight: 950;
  color: var(--theme-green);
  line-height: 1.1;
}
.stat-label {
  font-size: 12px;
  font-weight: 750;
  color: var(--theme-muted);
  text-transform: uppercase;
  letter-spacing: .03em;
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
  border-radius: 14px;
  padding: 18px;
  background: rgba(var(--theme-panel-rgb), .9);
  box-shadow: 0 14px 34px var(--theme-shadow);
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
  gap: 14px;
}
.project-card {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  gap: 22px;
  align-items: center;
  border: 1px solid var(--theme-line);
  border-radius: 16px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.82), rgba(255,255,255,.96)),
    var(--theme-panel);
  box-shadow: 0 18px 42px var(--theme-shadow);
  transition: border-color .25s ease, transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease;
}
.project-card:hover {
  transform: translateY(-5px);
  border-color: var(--theme-card-hover-border);
  box-shadow: 0 26px 64px var(--theme-shadow-hover);
}
.project-number {
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(37,99,235,.12), rgba(15,143,110,.12));
  color: var(--theme-blue);
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
  padding: 6px 10px;
  background: var(--theme-tag-bg);
  color: var(--theme-tag-text);
  font-size: 12px;
  font-weight: 750;
}
.project-links {
  min-width: 128px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  color: var(--theme-blue);
  font-size: 14px;
  flex-wrap: wrap;
}

/* ===== Card action links ===== */
.card-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 10px;
  padding: 7px 14px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 750;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  transition: all .2s ease;
}
.card-link-github {
  border: 1px solid var(--theme-line);
  background: var(--theme-surface);
  color: var(--theme-ink);
}
.card-link-github:hover {
  border-color: var(--theme-blue);
  background: var(--theme-blue);
  color: #fff;
}
.card-link-external {
  border: 1px solid var(--theme-line);
  background: var(--theme-surface);
  color: var(--theme-amber);
}
.card-link-external:hover {
  border-color: var(--theme-amber);
  background: var(--theme-amber);
  color: #fff;
}
.card-link-demo {
  border: 1px solid var(--theme-green);
  background: var(--theme-green);
  color: #fff;
}
.card-link-demo:hover {
  background: var(--theme-green-hover);
  border-color: var(--theme-green-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(18,120,93,.25);
}

.muted { color: var(--theme-muted); font-weight: 750; }

/* ===== Expandable project card details ===== */
.expand-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--theme-line);
  border-radius: 10px;
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
