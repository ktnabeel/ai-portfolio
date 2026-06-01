from base64 import b64encode
from html import escape
from pathlib import Path
from typing import Any

from .config import load_config
from .models import Project


BASE_DIR = Path(__file__).resolve().parents[1]
LOGO_PATH = BASE_DIR / "static" / "neurons_logo_mark.png"
_LOGO_DATA_URI: str | None = None


def _logo_data_uri() -> str:
    global _LOGO_DATA_URI
    if _LOGO_DATA_URI is not None:
        return _LOGO_DATA_URI
    try:
        encoded = b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    except OSError:
        _LOGO_DATA_URI = ""
    else:
        _LOGO_DATA_URI = f"data:image/png;base64,{encoded}"
    return _LOGO_DATA_URI


def _tab_links_from_config(config: dict[str, Any]) -> dict[str, str]:
    """Return project-title → tab-id mapping from config's project_tab_links."""
    return config.get("project_tab_links", {})


def _tab_labels_from_config(config: dict[str, Any]) -> dict[str, str]:
    """Return tab-id → display-label mapping from config's tabs."""
    return config.get("tabs", {})


def _order_projects_for_tabs(projects: list[Project], config: dict[str, Any]) -> list[Project]:
    """Return projects in the same order as the configured app tabs."""
    tab_order = {
        str(tab_id): index
        for index, tab_id in enumerate(config.get("tabs", {}).keys())
    }
    if not tab_order:
        return projects

    tab_links = _tab_links_from_config(config)
    fallback = len(tab_order)
    ordered = sorted(
        enumerate(projects),
        key=lambda pair: (
            tab_order.get(tab_links.get(pair[1].title, ""), fallback + pair[0]),
            pair[0],
        ),
    )
    return [project for _, project in ordered]


_DEFAULT_PROJECT_CONTEXT: dict[str, dict[str, Any]] = {
    "Portfolio Manager": {
        "project_summary": "Production-style multi-agent portfolio manager that turns market data, sentiment, and risk signals into explainable portfolio actions.",
        "problem": "Investment decisions require synthesizing fragmented market, technical, sentiment, and risk context quickly.",
        "architecture": "FastAPI and LangGraph orchestrate specialized agents for security analysis, sentiment, regime, decisioning, execution, and portfolio management.",
        "ai_application": "LLM agents produce structured analysis and a final Buy/Sell/Hold recommendation with confidence and rationale.",
        "impact": "Shows ability to design agentic workflows, API boundaries, and explainable decision support for finance users.",
        "proof_points": ["LangGraph orchestration", "FastAPI service surface", "Real-time yfinance data", "Structured portfolio rationale"],
    },
    "Trading Desk": {
        "project_summary": "Options trading workbench combining quantitative pricing, market context, and agent-assisted trade review.",
        "problem": "Options decisions need pricing math, market awareness, risk review, and a clear human approval path.",
        "architecture": "LangGraph coordinates market, risk, regime, decision, and execution components with a Gradio control surface.",
        "ai_application": "Agents analyze risk-reward and produce tradeable recommendations while keeping execution human-reviewed.",
        "impact": "Demonstrates applied AI for regulated decision workflows where automation must remain auditable.",
        "proof_points": ["Black-Scholes pricing", "Paper-trade execution", "MCP server integration", "Approval workflow"],
    },
    "Claim Processing": {
        "project_summary": "Insurance claim intake assistant that extracts facts, flags fraud indicators, scores severity, and routes next steps.",
        "problem": "Claims teams spend time converting unstructured incident text into repeatable triage decisions.",
        "architecture": "A deterministic NLP and rules pipeline extracts claim fields, applies red-flag checks, classifies severity, and recommends routing.",
        "ai_application": "The system applies AI-style document understanding patterns with explainable rules suitable for operational review.",
        "impact": "Highlights automation design for insurance workflows where speed, consistency, and auditability matter.",
        "proof_points": ["Free-text extraction", "Fraud red flags", "Severity classification", "Batch processing"],
    },
    "Insurance Underwriting Agent": {
        "project_summary": "Underwriting assistant that reads applications, evaluates multidimensional risk, and returns structured policy decisions.",
        "problem": "Underwriters need consistent extraction, risk factor discovery, and clear reasoning from incomplete application text.",
        "architecture": "A four-dimension risk engine evaluates health, occupation, lifestyle, and financial signals, then builds policy context.",
        "ai_application": "Agentic reasoning converts unstructured applicant details into risk scores, decisions, and auditable recommendations.",
        "impact": "Shows domain modeling, decision logic, and explainability for high-stakes insurance workflows.",
        "proof_points": ["40+ risk rules", "Risk score 0-100", "Policy context builder", "Batch underwriting"],
    },
    "Product Review Sentiment Analyzer": {
        "project_summary": "Customer feedback analytics tool that turns product reviews into sentiment, keywords, and product-level summaries.",
        "problem": "Teams need to understand review patterns at scale without manually reading every customer comment.",
        "architecture": "Review ingestion, sentiment classification, aggregation, keyword extraction, and visualization are packaged in a Gradio app.",
        "ai_application": "NLP classification and summarization patterns convert unstructured reviews into structured product insights.",
        "impact": "Demonstrates practical NLP for product, support, and operations teams.",
        "proof_points": ["Per-review sentiment", "Product rollups", "Keyword extraction", "Visual distributions"],
    },
    "Resume Matcher": {
        "project_summary": "NVIDIA-backed resume screening assistant that compares a candidate resume against a target role and returns fit guidance.",
        "problem": "Job seekers need fast, specific feedback on whether their resume reflects the actual requirements in a job description.",
        "architecture": "Gradio handles file upload and job text input, local parsers extract resume text, and an NVIDIA-hosted chat model returns structured scoring.",
        "ai_application": "The LLM evaluates requirement coverage, identifies weak or missing evidence, and recommends concrete resume edits.",
        "impact": "Shows practical AI for recruiting workflows where output needs to be explainable and immediately actionable.",
        "proof_points": ["Resume upload", "NVIDIA API scoring", "Gap analysis", "Targeted edit pointers"],
    },
    "Finance Planning": {
        "project_summary": "Financial planning assistant for portfolio analysis, budgeting scenarios, and goal-oriented decision support.",
        "problem": "Personal and portfolio finance decisions require combining goals, market context, and risk into clear next actions.",
        "architecture": "Financial analysis modules collect market data, compute signals, and present recommendations through an interactive UI.",
        "ai_application": "Agent-style analysis blends technical, fundamental, sentiment, and risk signals for planning guidance.",
        "impact": "Shows how AI workflows can support finance users with transparent, scenario-driven outputs.",
        "proof_points": ["Budget scenarios", "Goal tracking", "Market data", "Risk scoring"],
    },
    "Movie Recommendations": {
        "project_summary": "Recommendation app that translates natural-language preferences into personalized movie suggestions.",
        "problem": "Users express taste in messy language, while recommenders need structured signals and ranked outputs.",
        "architecture": "A hybrid recommender combines preference parsing, embeddings, collaborative filtering, and TMDB metadata.",
        "ai_application": "NLP-style parsing extracts taste signals and blends them with ML recommenders for ranked suggestions.",
        "impact": "Demonstrates recommendation systems, ensemble modeling, and user-centered AI interaction.",
        "proof_points": ["Two-tower embeddings", "SVD filtering", "Preference parser", "TMDB integration"],
    },
}


def _project_details_from_config(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    details = {title: dict(values) for title, values in _DEFAULT_PROJECT_CONTEXT.items()}
    for item in config.get("projects", []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        project_detail = details.get(title, {}).copy()
        for key in (
            "project_summary",
            "problem",
            "architecture",
            "ai_application",
            "impact",
            "proof_points",
        ):
            if key in item:
                project_detail[key] = item[key]
        if project_detail:
            details[title] = project_detail
    return details

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


def _tab_link(tab_id: str, display_label: str, link_label: str, class_name: str = "") -> str:
    """Generate a button handled by the Gradio tab-switch delegation script."""
    class_attr = ' class="' + class_name + '"' if class_name else ""
    return (
        '<button type="button"'
        + class_attr
        + ' data-tab-target="'
        + escape(tab_id, quote=True)
        + '" data-tab-label="'
        + escape(display_label, quote=True)
        + '"'
        + '>'
        + escape(link_label)
        + "</button>"
    )


def gradio_tab_switch_js() -> str:
    return """
(function() {
  if (window.__portfolioTabSwitchBound) return;
  window.__portfolioTabSwitchBound = true;

  function clean(value) {
    return (value || '').replace(/\\s+/g, ' ').trim();
  }

  function findTab(label) {
    var wanted = clean(label);
    if (!wanted) return null;
    var tabs = Array.from(document.querySelectorAll('[role="tab"]'));
    var exact = tabs.find(function(tab) {
      return clean(tab.textContent) === wanted;
    });
    if (exact) return exact;
    return tabs.find(function(tab) {
      return clean(tab.textContent).indexOf(wanted) >= 0;
    }) || null;
  }

  document.addEventListener('click', function(event) {
    var trigger = event.target.closest('[data-tab-target]');
    if (!trigger) return;
    event.preventDefault();
    event.stopPropagation();

    var label = trigger.getAttribute('data-tab-label') || trigger.getAttribute('data-tab-target');
    var tab = findTab(label);
    if (!tab) return;

    tab.click();
    setTimeout(function() {
      tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
    }, 80);
  });
})();
"""


def _gradio_tab_switch_script() -> str:
    return f"<script>{gradio_tab_switch_js()}</script>"


def render_page(projects: list[Project], mode: str = "static", config: dict[str, Any] | None = None) -> str:
    config = config or load_config()
    site = config["site"]
    tab_links = _tab_links_from_config(config)
    tab_labels = _tab_labels_from_config(config)
    project_details = _project_details_from_config(config)
    ordered_projects = _order_projects_for_tabs(projects, config)
    page = _render_shell(
        _render_project_grid(
            ordered_projects,
            mode=mode,
            tab_links=tab_links,
            tab_labels=tab_labels,
            project_details=project_details,
        ),
        config,
        mode=mode,
    )

    if mode == "gradio":
        theme_init_js = (
            "<script>(function(){"
            "document.documentElement.setAttribute('data-theme','light');"
            "try{localStorage.removeItem('theme')}catch(e){};"
            "})();</script>"
        )
        return f"<style>{_css()}</style>{theme_init_js}{page}{_gradio_tab_switch_script()}"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(site["meta_description"])}">
  <title>{escape(site["title"])}</title>
  <script>
    (function(){{
      document.documentElement.setAttribute('data-theme', 'light');
      try {{ localStorage.removeItem('theme'); }} catch (e) {{}}
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
    proof_items = config.get("proof_strip", [])
    logo_src = _logo_data_uri()
    brand_logo = (
        f'<img class="brand-logo" src="{logo_src}" alt="" aria-hidden="true">'
        if logo_src
        else f'<span class="brand-mark">{escape(str(site.get("brand_mark", "N")))}</span>'
    )

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
    proof_html = "\n".join(
        f"""<div class="proof-item">
          <span class="proof-marker {marker['class']}" aria-label="{escape(marker['label'])}" title="{escape(marker['label'])}">{marker['icon']}</span>
          <strong>{escape(str(item.get('label', item.get('title', 'Proof'))))}</strong>
          <span>{escape(str(item.get('value', item.get('description', ''))))}</span>
        </div>"""
        for item in proof_items
        if isinstance(item, dict)
        for marker in [_proof_marker_for(str(item.get('label', item.get('title', 'Proof'))))]
    )
    proof_section = (
        f"""
      <section class="proof-strip" aria-label="Engineering proof">
        {proof_html}
      </section>"""
        if proof_html
        else ""
    )

    return f"""
  <main class="portfolio-page" id="top">
    <section class="workspace">
      <header class="top-bar">
        <a href="#top" class="brand-lockup" aria-label="{escape(site["brand"])} home">
          {brand_logo}
          <span class="brand-copy">
            <strong>{escape(site["brand"])}</strong>
            <span>{escape(site["kicker"])}</span>
          </span>
        </a>
        <div class="top-bar-left">
          <span class="status-dot"></span>
          {escape(site["status_label"])}
          <span class="top-bar-sep"></span>
          <a href="{escape(site["linkedin_url"])}" target="_blank" rel="noreferrer" class="top-bar-contact">Contact</a>
        </div>
        <div class="top-bar-right">
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
      {proof_section}

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
    <div class="landing-footer">
      <span>{escape(site.get("copyright", "© neurons.fyi"))}</span>
    </div>
  </main>"""


def _render_project_grid(
    projects: list[Project],
    mode: str,
    tab_links: dict[str, str] | None = None,
    tab_labels: dict[str, str] | None = None,
    project_details: dict[str, dict[str, Any]] | None = None,
) -> str:
    if not projects:
        return """
        <div class="empty-state">
          <h3>Real project entries are ready to be added.</h3>
          <p>This portfolio is intentionally empty until real AI projects are added.</p>
        </div>
    """

    cards = "\n".join(
        _render_project_card(
            index,
            project,
            mode=mode,
            tab_links=tab_links,
            tab_labels=tab_labels,
            details=(project_details or {}).get(project.title),
        )
        for index, project in enumerate(projects, start=1)
    )
    return f'<div class="project-list">{cards}</div>'


def _proof_marker_for(label: str) -> dict[str, str]:
    normalized = label.lower()
    if "architecture" in normalized:
        return {"icon": "⛓", "class": "proof-marker-architecture", "label": "Agent architecture"}
    if "production" in normalized:
        return {"icon": "🚀", "class": "proof-marker-production", "label": "Production wiring"}
    if "reliability" in normalized:
        return {"icon": "🛡", "class": "proof-marker-reliability", "label": "Reliability"}
    if "domain" in normalized:
        return {"icon": "🌐", "class": "proof-marker-domain", "label": "Domain range"}
    return {"icon": "•", "class": "proof-marker-generic", "label": label}


def _render_project_card(
    index: int,
    project: Project,
    mode: str,
    tab_links: dict[str, str] | None = None,
    tab_labels: dict[str, str] | None = None,
    details: dict[str, Any] | None = None,
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
        links.append(_tab_link(tab_id, display_label, "Open", "card-link card-link-demo"))

    # Static deployment: expandable inline details instead of external links.
    expand_html = ""
    if mode == "static":
        static_details = _PROJECT_DETAILS.get(project.title, "")
        if static_details:
            expand_html = f"""
          <div class="project-expand" id="expand-{index}">
            {static_details}
          </div>"""
            links.append(
                f'<button class="expand-toggle" onclick="toggleExpand({index})"'
                f' aria-expanded="false" aria-controls="expand-{index}">'
                f'Details</button>'
            )
        elif not project.github_url and not project.demo_url:
            links.append('<span class="muted">Links coming soon</span>')

    link_html = "".join(links) or '<span class="muted">Links coming soon</span>'
    insight_html = _render_project_insight(details)

    return f"""
        <article class="project-card" id="card-{index}" tabindex="0">
          <div class="project-glow" aria-hidden="true"></div>
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
          {insight_html}
          <div class="project-links">{link_html}</div>
          {expand_html}
        </article>
"""


def _render_project_insight(details: dict[str, Any] | None) -> str:
    if not details:
        return ""

    proof_points = details.get("proof_points", [])
    if isinstance(proof_points, str):
        proof_values = [item.strip() for item in proof_points.split(",") if item.strip()]
    elif proof_points:
        proof_values = [str(item).strip() for item in proof_points if str(item).strip()]
    else:
        proof_values = []
    proof_html = "".join(f"<li>{escape(item)}</li>" for item in proof_values[:4])

    return f"""
          <aside class="project-insight" aria-label="Project context">
            <p class="insight-kicker">Project context</p>
            <p class="insight-summary">{escape(str(details.get("project_summary", "")))}</p>
            <div class="insight-grid">
              <div>
                <span>Problem</span>
                <p>{escape(str(details.get("problem", "")))}</p>
              </div>
              <div>
                <span>Architecture</span>
                <p>{escape(str(details.get("architecture", "")))}</p>
              </div>
              <div>
                <span>AI role</span>
                <p>{escape(str(details.get("ai_application", "")))}</p>
              </div>
              <div>
                <span>Impact</span>
                <p>{escape(str(details.get("impact", "")))}</p>
              </div>
            </div>
            <ul class="insight-proof">{proof_html}</ul>
          </aside>"""


def _css() -> str:
    return """
/* ===== Light Theme (default) ===== */
:root {
  color-scheme: light;
  --theme-bg: #ffffff;
  --theme-panel: #ffffff;
  --theme-ink: #101828;
  --theme-muted: #667085;
  --theme-line: #d9e2ec;
  --theme-line-rgb: 217, 226, 236;
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
  --theme-page-top: #f7fbff;
  --theme-page-bottom: #eef7f3;
}

/* ===== Dark Theme ===== */
[data-theme="dark"] {
  color-scheme: dark;
  --theme-bg: #081527;
  --theme-panel: #0f2038;
  --theme-ink: #f7fbff;
  --theme-muted: rgba(226,235,249,.86);
  --theme-line: rgba(166,190,226,.34);
  --theme-line-rgb: 166, 190, 226;
  --theme-green: #55d6a5;
  --theme-blue: #7cb7ff;
  --theme-amber: #ffd166;
  --theme-surface: #173153;
  --theme-tag-bg: #18385f;
  --theme-tag-text: #f2f7ff;
  --theme-shadow: rgba(0,0,0,.32);
  --theme-shadow-hover: rgba(0,0,0,.48);
  --theme-card-hover-border: rgba(124,183,255,.52);
  --theme-status-glow: rgba(85,214,165,.22);
  --theme-green-hover: #7ae8bf;
  --theme-blue-hover: #a8d0ff;
  --theme-panel-rgb: 15, 32, 56;
  --theme-page-top: #0b1b33;
  --theme-page-bottom: #10233f;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 100px; }
body {
  margin: 0;
  background:
    linear-gradient(180deg, var(--theme-page-top) 0%, var(--theme-bg) 44%, var(--theme-page-bottom) 100%);
  color: var(--theme-ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  transition: background-color .3s ease, color .3s ease;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}
[data-theme="dark"] body {
  background: var(--theme-bg);
}
a { color: inherit; }

.portfolio-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
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
  flex: 1;
  margin: 0 auto;
  padding: 18px 20px 28px;
}
.top-bar {
  position: sticky;
  top: 6px;
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
  background: rgba(var(--theme-panel-rgb), 0.92);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: 0 16px 44px var(--theme-shadow), 0 1px 2px rgba(16,24,40,.06);
  transition: box-shadow .35s ease, background .35s ease, border-color .35s ease, transform .35s ease;
}
.brand-lockup {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: var(--theme-ink);
  text-decoration: none;
  flex-shrink: 0;
}
.brand-logo,
.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  flex-shrink: 0;
}
.brand-logo {
  object-fit: cover;
  box-shadow: 0 8px 18px rgba(16,24,40,.12);
}
.brand-mark {
  display: grid;
  place-items: center;
  background: var(--theme-ink);
  color: var(--theme-panel);
  font-weight: 950;
}
.brand-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.brand-copy strong {
  font-size: 14px;
  line-height: 1.1;
}
.brand-copy span {
  color: var(--theme-muted);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.2;
}
.top-bar-left,
.top-bar-right {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  gap: 7px;
  color: var(--theme-muted);
  font-size: 13px;
  font-weight: 500;
}
.top-bar-left {
  min-width: 0;
  flex-wrap: wrap;
}
.top-bar-right {
  margin-left: auto;
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
  font-weight: 600;
  text-decoration: none;
  transition: color .18s ease;
}
.top-bar-contact:hover {
  color: var(--theme-blue-hover) !important;
}

.intro {
  padding: 44px 8px 26px;
  max-width: 980px;
}
.intro h2 {
  margin-bottom: 18px;
  font-size: clamp(36px, 5vw, 64px);
  line-height: .95;
  letter-spacing: 0;
}
.intro p:not(.eyebrow) {
  max-width: 720px;
  color: var(--theme-muted);
  font-size: 17px;
  line-height: 1.65;
}

/* ===== Stats Strip ===== */
.stats-strip {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.stats-strip::before {
  content: "";
  position: absolute;
  inset: -24px -12px -10px;
  z-index: -1;
  background:
    radial-gradient(50% 60% at 12% 30%, rgba(29, 102, 247, .18), transparent 72%),
    radial-gradient(44% 52% at 85% 35%, rgba(17, 163, 120, .16), transparent 78%);
  pointer-events: none;
}
.stat-item {
  min-width: 0;
  min-height: 96px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 2px;
  border: 1px solid rgba(var(--theme-line-rgb), .75);
  border-radius: 14px;
  padding: 15px 14px;
  background:
    linear-gradient(160deg, rgba(var(--theme-panel-rgb), .92), rgba(var(--theme-panel-rgb), .8)),
    var(--theme-panel);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.18),
    0 24px 44px rgba(11, 25, 50, .14);
  backdrop-filter: blur(12px) saturate(135%);
  -webkit-backdrop-filter: blur(12px) saturate(135%);
  transition: transform .28s cubic-bezier(.22,1,.36,1), box-shadow .28s ease, border-color .26s ease;
}
.stat-item:hover {
  transform: translateY(-6px) scale(1.01);
  border-color: rgba(28, 160, 241, .45);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.2),
    0 28px 54px rgba(12, 26, 50, .22);
}
.stat-value {
  max-width: 100%;
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 950;
  color: var(--theme-ink);
  line-height: 1.1;
  text-align: center;
  overflow-wrap: anywhere;
}
.stat-label {
  font-size: 12px;
  font-weight: 750;
  color: var(--theme-muted);
  text-transform: uppercase;
  letter-spacing: 0;
  text-align: center;
}

.proof-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 20px;
}
.proof-item {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  column-gap: 12px;
  row-gap: 5px;
  align-items: start;
  border: 1px solid rgba(28, 160, 241, .22);
  border-radius: 16px;
  padding: 14px;
  background:
    linear-gradient(145deg, rgba(37,99,235,.12), rgba(15,143,110,.09)),
    rgba(var(--theme-panel-rgb), .92);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.16),
    0 14px 34px var(--theme-shadow);
  transition: transform .24s cubic-bezier(.22,1,.36,1), box-shadow .24s ease, border-color .24s ease;
}
.proof-item:hover {
  transform: translateY(-4px);
  border-color: rgba(28, 160, 241, .38);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.18),
    0 22px 42px rgba(12, 31, 58, .2);
}
.proof-marker {
  grid-row: span 2;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 900;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.24),
    0 10px 18px rgba(15,23,42,.10);
}
.proof-marker-architecture {
  background: linear-gradient(160deg, rgba(37,99,235,.18), rgba(15,23,42,.92));
  color: #8ac0ff;
  border: 1px solid rgba(138,192,255,.28);
}
.proof-marker-production {
  background: linear-gradient(160deg, rgba(255,122,24,.18), rgba(42,29,8,.92));
  color: #ffbc80;
  border: 1px solid rgba(255,188,128,.28);
}
.proof-marker-reliability {
  background: linear-gradient(160deg, rgba(15,143,110,.18), rgba(6,35,31,.92));
  color: #7fe2c0;
  border: 1px solid rgba(127,226,192,.28);
}
.proof-marker-domain {
  background: linear-gradient(160deg, rgba(124,183,255,.18), rgba(10,24,44,.92));
  color: #c6e0ff;
  border: 1px solid rgba(198,224,255,.28);
}
.proof-marker-generic {
  background: linear-gradient(160deg, rgba(37,99,235,.14), rgba(15,23,42,.86));
  color: #d6e6ff;
  border: 1px solid rgba(214,230,255,.22);
}
.proof-item strong {
  min-width: 0;
  color: var(--theme-ink);
  font-size: 15px;
  line-height: 1.25;
}
.proof-item span:last-child {
  min-width: 0;
  color: var(--theme-muted);
  font-size: 13px;
  line-height: 1.4;
}

.capability-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 34px;
}
.capability-strip div {
  min-height: 96px;
  border: 1px solid rgba(var(--theme-line-rgb), .78);
  border-radius: 14px;
  padding: 18px;
  background:
    linear-gradient(165deg, rgba(var(--theme-panel-rgb), .94), rgba(var(--theme-panel-rgb), .82)),
    var(--theme-panel);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.16),
    0 18px 38px rgba(15,23,42,.15);
  transition: transform .28s cubic-bezier(.22,1,.36,1), box-shadow .28s ease, border-color .28s ease;
}
.capability-strip div:hover {
  transform: translateY(-6px);
  border-color: rgba(15,143,110,.4);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.2),
    0 26px 46px rgba(15,23,42,.22);
}
.capability-strip strong,
.capability-strip span {
  display: block;
}
.capability-strip strong {
  margin-bottom: 8px;
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: 0;
}
.capability-strip span {
  color: var(--theme-muted);
  font-size: 16px;
  line-height: 1.45;
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
  perspective: 1400px;
}
.project-card {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  border: 1px solid var(--theme-line);
  border-radius: 16px;
  padding: 14px;
  background:
    linear-gradient(180deg, rgba(var(--theme-panel-rgb), .92), rgba(var(--theme-panel-rgb), .99)),
    var(--theme-panel);
  box-shadow: 0 14px 34px var(--theme-shadow);
  transform-style: preserve-3d;
  outline: none;
  transition: border-color .25s ease, transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease, background .25s ease;
}
.project-card:hover {
  transform: translateY(-6px) rotateX(1deg) rotateY(-.6deg);
  border-color: var(--theme-card-hover-border);
  box-shadow: 0 24px 64px var(--theme-shadow-hover), 0 2px 0 rgba(var(--theme-panel-rgb),.55) inset;
}
.project-card:focus-within,
.project-card:focus {
  border-color: var(--theme-blue);
  box-shadow: 0 0 0 4px rgba(37,99,235,.14), 0 32px 90px var(--theme-shadow-hover);
}
.project-glow {
  position: absolute;
  inset: -45% auto auto -18%;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(37,99,235,.18), rgba(15,143,110,.08) 42%, transparent 70%);
  opacity: .58;
  pointer-events: none;
  transform: translateZ(-1px);
  transition: opacity .25s ease, transform .25s ease;
  z-index: -1;
}
.project-card:hover .project-glow,
.project-card:focus-within .project-glow,
.project-card:focus .project-glow {
  opacity: .9;
  transform: translate3d(10px, 8px, -1px) scale(1.08);
}
.project-number {
  position: relative;
  z-index: 2;
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(37,99,235,.12), rgba(15,143,110,.12));
  color: var(--theme-blue);
  font-size: 12px;
  font-weight: 950;
}
.project-main {
  position: relative;
  z-index: 2;
  min-width: 0;
}
.project-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.project-meta span {
  display: inline-flex;
  border: 1px solid var(--theme-line);
  border-radius: 999px;
  padding: 4px 8px;
  color: var(--theme-muted);
  font-size: 11px;
  font-weight: 760;
}
.project-card h3 {
  margin-bottom: 6px;
  font-size: 18px;
  line-height: 1.18;
}
.project-card p {
  max-width: 780px;
  margin-bottom: 10px;
  color: var(--theme-muted);
  font-size: 13px;
  line-height: 1.5;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag-row span {
  border-radius: 999px;
  padding: 5px 8px;
  background: var(--theme-tag-bg);
  color: var(--theme-tag-text);
  font-size: 11px;
  font-weight: 750;
}
.project-links {
  position: relative;
  z-index: 8;
  min-width: 112px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  color: var(--theme-blue);
  font-size: 13px;
  flex-wrap: wrap;
}
.project-insight {
  grid-column: 2 / 4;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 0;
  margin-top: -8px;
  border: 1px solid var(--theme-line);
  border-radius: 14px;
  padding: 0 12px;
  background:
    linear-gradient(135deg, rgba(var(--theme-panel-rgb), .98), rgba(var(--theme-panel-rgb), .92)),
    var(--theme-panel);
  box-shadow: 0 20px 50px rgba(15,23,42,.12);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
  transform: translateY(-8px);
  transition: max-height .35s ease, margin-top .25s ease, opacity .22s ease, padding .25s ease, transform .25s cubic-bezier(.34,1.56,.64,1);
  z-index: 3;
}
.project-card:hover .project-insight,
.project-card:focus-within .project-insight,
.project-card:focus .project-insight {
  max-height: 680px;
  margin-top: 0;
  padding: 12px;
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}
.insight-kicker {
  margin: 0;
  color: var(--theme-green);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .04em;
  text-transform: uppercase;
}
.insight-summary {
  max-width: none;
  margin: 0;
  color: var(--theme-ink);
  font-size: 13px;
  font-weight: 780;
  line-height: 1.45;
}
.insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.insight-grid div {
  border: 1px solid var(--theme-line);
  border-radius: 10px;
  padding: 8px;
  background: var(--theme-surface);
}
.insight-grid span {
  display: block;
  margin-bottom: 4px;
  color: var(--theme-blue);
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
}
.insight-grid p {
  max-width: none;
  margin: 0;
  color: var(--theme-muted);
  font-size: 11px;
  line-height: 1.42;
}
.insight-proof {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.insight-proof li {
  border-radius: 999px;
  padding: 5px 8px;
  background: rgba(15,143,110,.1);
  color: var(--theme-green);
  font-size: 11px;
  font-weight: 800;
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
[data-theme="dark"] .card-link-demo,
[data-theme="dark"] .card-link-demo:hover,
[data-theme="dark"] .card-link-external:hover {
  color: #061426;
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

.landing-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 20px 8px 10px;
  color: var(--theme-muted);
  font-size: 12px;
}

@media (max-width: 980px) {
  .workspace {
    padding: 14px 14px 22px;
  }
  .proof-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .capability-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .project-insight {
    grid-column: 1 / -1;
    width: 100%;
    margin-top: 4px;
    max-height: none;
    padding: 14px;
    opacity: 1;
    pointer-events: auto;
    transform: none;
    box-shadow: 0 14px 34px var(--theme-shadow);
  }
  .project-card:hover .project-insight,
  .project-card:focus-within .project-insight,
  .project-card:focus .project-insight {
    transform: none;
  }
}
@media (max-width: 720px) {
  .workspace {
    padding: 10px 10px 16px;
  }
  .top-bar {
    align-items: center;
    flex-direction: row;
    flex-wrap: wrap;
    height: auto;
    min-height: 0;
    padding: 10px 12px;
    gap: 10px;
  }
  .brand-lockup {
    flex: 1 1 auto;
  }
  .brand-logo,
  .brand-mark {
    width: 32px;
    height: 32px;
    border-radius: 9px;
  }
  .brand-copy span {
    display: none;
  }
  .top-bar-left,
  .top-bar-right {
    margin-bottom: 0;
  }
  .top-bar-left {
    order: 3;
    width: 100%;
    flex: 1;
    flex-wrap: wrap;
    justify-content: space-between;
    font-size: 0;
    line-height: 1.35;
  }
  .top-bar-left::before {
    content: "AI/ML Engineer";
    color: var(--theme-muted);
    font-size: 12px;
    font-weight: 760;
  }
  .top-bar-left .status-dot,
  .top-bar-left .top-bar-sep {
    display: none;
  }
  .top-bar-contact {
    font-size: 12px;
  }
  .top-bar-right {
    width: auto;
    justify-content: flex-end;
    margin-left: auto;
  }
  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .intro {
    padding: 30px 0 20px;
  }
  .intro h2 {
    font-size: clamp(30px, 10vw, 42px);
    line-height: 1.03;
    margin-bottom: 14px;
  }
  .intro p:not(.eyebrow) {
    font-size: 15px;
    line-height: 1.55;
  }
  .stats-strip {
    gap: 8px;
    margin-bottom: 10px;
  }
  .stat-item {
    min-height: 76px;
    border-radius: 12px;
    padding: 12px 8px;
  }
  .stat-value {
    font-size: clamp(19px, 6vw, 24px);
  }
  .stat-label {
    font-size: 10px;
  }
  .proof-strip {
    grid-template-columns: 1fr;
    gap: 8px;
    margin-bottom: 14px;
  }
  .proof-item {
    padding: 11px;
  }
  .capability-strip {
    grid-template-columns: 1fr;
    gap: 8px;
    margin-bottom: 24px;
  }
  .capability-strip div {
    min-height: 0;
    padding: 14px;
  }
  .project-card {
    grid-template-columns: 40px minmax(0, 1fr);
    align-items: start;
    gap: 12px;
    padding: 14px;
    border-radius: 14px;
    transform: none;
  }
  .project-card:hover {
    transform: translateY(-3px);
  }
  .project-links {
    grid-column: 1 / -1;
    min-width: 0;
    justify-content: flex-start;
    margin-top: 4px;
  }
  .project-insight {
    grid-column: 1 / -1;
    padding: 12px;
  }
  .project-number {
    width: 38px;
    height: 38px;
    border-radius: 10px;
  }
  .project-card h3 {
    font-size: 17px;
  }
  .project-card p {
    font-size: 12px;
    line-height: 1.45;
  }
  .insight-grid {
    grid-template-columns: 1fr;
  }
  .landing-footer {
    padding: 18px 2px 8px;
    font-size: 11px;
  }
}
"""
