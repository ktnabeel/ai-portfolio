"""FastAPI app — self-contained portfolio with all 6 project pages for Vercel deployment.

Reuses all existing business logic from portfolio/ modules.
Each interactive tab is a GET (form) + POST (results) route pair.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from html import escape

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# ── Project root ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]

# ── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(title="Nabeel's AI Project Portfolio")

# ── Static files ────────────────────────────────────────────────────────────
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Template engine ─────────────────────────────────────────────────────────
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.autoescape = True


# ══════════════════════════════════════════════════════════════════════════════
#  Shared helpers
# ══════════════════════════════════════════════════════════════════════════════

def _load_config():
    from portfolio.config import load_config
    return load_config()

def _get_projects():
    from portfolio.db import get_projects, init_db, seed_projects
    from portfolio.project_templates import PROJECT_TEMPLATES
    # Use /tmp/ for Vercel compatibility (read-only filesystem outside /tmp)
    db_path = Path("/tmp/portfolio.db") if "VERCEL" in os.environ else BASE_DIR / "portfolio.db"
    init_db(db_path)
    seed_projects(db_path, PROJECT_TEMPLATES)
    return get_projects(db_path)


# ══════════════════════════════════════════════════════════════════════════════
#  Portfolio landing page
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def portfolio(request: Request):
    from portfolio.render import _PROJECT_DETAILS
    config = _load_config()
    projects = _get_projects()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "config": config,
        "projects": projects,
        "project_details": _PROJECT_DETAILS,
        "active_page": "portfolio",
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Financial Agent
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/financial", response_class=HTMLResponse)
async def financial_form(request: Request):
    return templates.TemplateResponse("financial.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "financial",
        "result_html": None,
    })


@app.post("/financial", response_class=HTMLResponse)
async def financial_analyze(
    request: Request,
    ticker: str = Form(default="AAPL"),
):
    result_html = _run_financial_analysis(ticker)
    return templates.TemplateResponse("financial.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "financial",
        "result_html": result_html,
        "ticker": ticker,
    })


@app.post("/financial/portfolio", response_class=HTMLResponse)
async def financial_portfolio(
    request: Request,
    holdings_text: str = Form(default=""),
):
    result_html = _run_portfolio_analysis(holdings_text)
    return templates.TemplateResponse("financial.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "financial",
        "result_html": result_html,
        "holdings_text": holdings_text,
        "show_portfolio": True,
    })


def _run_financial_analysis(ticker: str) -> str:
    if not ticker or not ticker.strip():
        return '<p class="error-msg">Please enter a stock ticker.</p>'
    from portfolio.financial.orchestrator import DecisionOrchestrator
    orch = DecisionOrchestrator()
    try:
        result = orch.analyze_stock(ticker.strip().upper())
    except Exception as e:
        return f'<p class="error-msg">Error: {escape(str(e))}</p>'

    action_color = {"Buy": "result-buy", "Sell": "result-sell", "Hold": "result-hold"}
    color_cls = action_color.get(result.action.value, "result-hold")

    signal_rows = ""
    for s in result.signals:
        icon = {"Bullish": "🟢", "Bearish": "🔴", "Neutral": "⚪"}
        signal_rows += (
            f'<div class="metric-card">'
            f'<strong>{icon.get(s.signal.value, "")} {escape(s.agent_name)}</strong>: '
            f'{s.signal.value} ({s.confidence:.0%})<br>'
            f'<small>{escape(s.summary)}</small></div>'
        )

    return f"""
    <h2>{escape(result.ticker)} Analysis</h2>
    <div class="metric-card">
        <span class="{color_cls}">{result.action.value}</span>
        &nbsp;| Confidence: {result.confidence:.0%}
        &nbsp;| Risk: {result.risk_level.value}
        &nbsp;| Price: ${result.current_price:.2f}
    </div>
    <h3>Agent Signals</h3>
    {signal_rows}
    """


def _run_portfolio_analysis(holdings_text: str) -> str:
    if not holdings_text or not holdings_text.strip():
        return '<p class="error-msg">Please enter portfolio holdings.</p>'

    from portfolio.financial.orchestrator import DecisionOrchestrator
    from portfolio.financial.models import PortfolioHolding

    holdings = []
    for line in holdings_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        ticker = parts[0].upper() if parts else ""
        shares = float(parts[1]) if len(parts) >= 2 else 1.0
        avg_price = float(parts[2]) if len(parts) >= 3 else None
        if ticker:
            holdings.append(PortfolioHolding(ticker=ticker, shares=shares, avg_price=avg_price))

    if not holdings:
        return '<p class="error-msg">No valid holdings found.</p>'

    orch = DecisionOrchestrator()
    try:
        result = orch.analyze_portfolio(holdings)
    except Exception as e:
        return f'<p class="error-msg">Error: {escape(str(e))}</p>'

    decision_rows = ""
    for d in result.decisions:
        action_color = {"Buy": "result-buy", "Sell": "result-sell", "Hold": "result-hold"}
        color_cls = action_color.get(d.action.value, "result-hold")
        decision_rows += (
            f'<div class="metric-card">'
            f'<strong>{escape(d.ticker)}</strong>: '
            f'<span class="{color_cls}">{d.action.value}</span>'
            f' ({d.confidence:.0%}) | Risk: {d.risk_level.value}'
            f' | ${d.current_price:.2f}</div>'
        )

    risk_color = {"Low": "result-buy", "Moderate": "result-hold", "High": "result-sell", "Critical": "result-sell"}
    risk_cls = risk_color.get(result.portfolio_risk.value, "result-hold")

    return f"""
    <h2>Portfolio Analysis</h2>
    <div class="metric-card">
        <strong>{escape(result.summary)}</strong><br>
        <span class="{risk_cls}">Portfolio Risk: {result.portfolio_risk.value}</span>
    </div>
    <h3>Per-Stock Decisions</h3>
    {decision_rows}
    """


# ══════════════════════════════════════════════════════════════════════════════
#  Claim Processing
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/claims", response_class=HTMLResponse)
async def claims_form(request: Request):
    return templates.TemplateResponse("claims.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "claims",
        "result_html": None,
    })


@app.post("/claims", response_class=HTMLResponse)
async def claims_process(
    request: Request,
    claim_text: str = Form(default=""),
    mode: str = Form(default="single"),
):
    if mode == "batch":
        result_html = _run_batch_claims(claim_text)
    else:
        result_html = _run_single_claim(claim_text)
    return templates.TemplateResponse("claims.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "claims",
        "result_html": result_html,
        "claim_text": claim_text,
        "mode": mode,
    })


def _run_single_claim(claim_text: str) -> str:
    if not claim_text or not claim_text.strip():
        return '<p class="error-msg">Please enter claim details.</p>'
    from portfolio.claim_processing.processor import ClaimProcessor
    processor = ClaimProcessor()
    result = processor.process_claim(claim_text)

    routing_cls = _routing_color(result.routing.value)
    fraud_cls = _fraud_color(result.fraud_risk.value)
    sev_cls = _severity_color(result.severity.value)

    rows = "".join(
        f"<tr><td>{escape(k)}</td><td>{escape(str(v))}</td></tr>"
        for k, v in result.extracted_details.items()
    )

    return f"""
    <h2>Claim Analysis Results</h2>
    <div class="claim-metric-card">
        <span class="{routing_cls}">{result.routing.value}</span>
        &nbsp;| Fraud: <span class="{fraud_cls}">{result.fraud_risk.value}</span> ({result.fraud_confidence:.0%})
        &nbsp;| Severity: <span class="{sev_cls}">{result.severity.value}</span>
    </div>
    <h3>Extracted Details</h3>
    <div class="claim-metric-card">
        <table class="extracted-table">{rows}</table>
    </div>
    <h3>Fraud Assessment</h3>
    <div class="claim-metric-card">
        <strong>Risk: <span class="{fraud_cls}">{result.fraud_risk.value}</span></strong>
        <br><small>{escape(result.fraud_reasoning)}</small>
    </div>
    <h3>Severity Assessment</h3>
    <div class="claim-metric-card">
        <strong>Severity: <span class="{sev_cls}">{result.severity.value}</span></strong>
        <br><small>{escape(result.severity_reasoning)}</small>
    </div>
    <h3>Routing Decision</h3>
    <div class="claim-metric-card">
        <strong>Action: <span class="{routing_cls}">{result.routing.value}</span></strong>
        <br><small>{escape(result.routing_reasoning)}</small>
    </div>
    """


def _run_batch_claims(claims_text: str) -> str:
    if not claims_text or not claims_text.strip():
        return '<p class="error-msg">Please enter claim details.</p>'
    from portfolio.claim_processing.processor import ClaimProcessor
    from portfolio.claim_processing.models import RoutingDecision

    claims = [c.strip() for c in re.split(r"\n\s*\n|---+", claims_text) if c.strip()]
    if not claims:
        return '<p class="error-msg">No claims found.</p>'

    processor = ClaimProcessor()
    rows = ""
    approve = review = deny = escalate = 0

    for i, ct in enumerate(claims, 1):
        result = processor.process_claim(ct)
        routing_cls = _routing_color(result.routing.value)
        fraud_cls = _fraud_color(result.fraud_risk.value)

        if result.routing == RoutingDecision.APPROVE:
            approve += 1
        elif result.routing == RoutingDecision.DENY:
            deny += 1
        elif result.routing == RoutingDecision.ESCALATE:
            escalate += 1
        else:
            review += 1

        amount_str = f"${result.claim.amount:,.2f}" if result.claim.amount else "—"
        claimant = result.claim.claimant or f"Claim #{i}"
        rows += (
            f'<div class="claim-metric-card">'
            f'<strong>{escape(claimant)}</strong> &nbsp;| {result.claim.claim_type.value}'
            f' &nbsp;| {amount_str}'
            f' &nbsp;| Fraud: <span class="{fraud_cls}">{result.fraud_risk.value}</span>'
            f' &nbsp;| <span class="{routing_cls}">{result.routing.value}</span>'
            f'</div>'
        )

    total = len(claims)
    summary = (
        f'<div class="claim-metric-card" style="margin-bottom:16px">'
        f'<strong>Batch Summary ({total} claims)</strong><br>'
        f'<span class="result-approve">Approve: {approve}</span> &nbsp;| '
        f'<span class="result-review">Review: {review}</span> &nbsp;| '
        f'<span class="result-deny">Deny: {deny}</span> &nbsp;| '
        f'<span class="result-escalate">Escalate: {escalate}</span>'
        f'</div>'
    )

    return f"<h2>Batch Claim Processing</h2>{summary}{rows}"


def _routing_color(v: str) -> str:
    return {"Approve": "result-approve", "Deny": "result-deny", "Review": "result-review", "Escalate": "result-escalate"}.get(v, "result-review")

def _fraud_color(v: str) -> str:
    return {"Low": "fraud-low", "Medium": "fraud-medium", "High": "fraud-high"}.get(v, "fraud-low")

def _severity_color(v: str) -> str:
    return {"Low": "severity-low", "Medium": "severity-medium", "High": "severity-high", "Critical": "severity-critical"}.get(v, "severity-low")


# ══════════════════════════════════════════════════════════════════════════════
#  Movie Recommendations
# ══════════════════════════════════════════════════════════════════════════════

_movie_recommender = None

def _get_movie_recommender():
    global _movie_recommender
    if _movie_recommender is not None:
        return _movie_recommender
    from portfolio.movie_recommender.pipeline import MoviePipeline
    from portfolio.movie_recommender.recommender import MovieRecommender
    pipeline = MoviePipeline()
    try:
        movies = pipeline.run(pages=3, enrich=True) if pipeline.client.is_configured else pipeline.run_sample()
    except Exception:
        movies = pipeline.run_sample()
    rec = MovieRecommender()
    rec.index(movies)
    _movie_recommender = rec
    return _movie_recommender


TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

def _tmdb_image_url(path: str, size: str = "w780") -> str:
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/{size}/{path.lstrip('/')}"


@app.get("/movies", response_class=HTMLResponse)
async def movies_form(request: Request):
    return templates.TemplateResponse("movies.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "movies",
        "result_html": None,
    })


@app.post("/movies", response_class=HTMLResponse)
async def movies_search(
    request: Request,
    query: str = Form(default=""),
    top_k: int = Form(default=8),
):
    result_html = _run_movie_recommendations(query, top_k)
    return templates.TemplateResponse("movies.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "movies",
        "result_html": result_html,
        "query": query,
        "top_k": top_k,
    })


def _run_movie_recommendations(query: str, top_k: int) -> str:
    if not query or not query.strip():
        return '<p class="error-msg">Please describe what kind of movies you\'re looking for.</p>'
    try:
        rec = _get_movie_recommender()
        result = rec.recommend(query, top_k=top_k)
    except Exception as e:
        return f'<p class="error-msg">Error: {escape(str(e))}</p>'

    # Preferences
    pref = result.preferences
    chips = ""
    if pref.liked_genres:
        chips += "".join(f'<span class="pref-chip">{escape(g)}</span>' for g in pref.liked_genres[:6])
    if pref.liked_actors:
        chips += "".join(f'<span class="pref-chip">🎭 {escape(a)}</span>' for a in pref.liked_actors[:3])
    if pref.liked_directors:
        chips += "".join(f'<span class="pref-chip">🎬 {escape(d)}</span>' for d in pref.liked_directors[:3])
    if pref.keywords:
        chips += "".join(f'<span class="pref-chip">🏷 {escape(k)}</span>' for k in pref.keywords[:5])
    if pref.mood:
        chips += f'<span class="pref-chip">🎯 Mood: {escape(pref.mood)}</span>'
    if pref.min_rating > 0:
        chips += f'<span class="pref-chip">⭐ ≥{pref.min_rating:.0f}/10</span>'
    if pref.disliked_genres:
        chips += "".join(f'<span class="pref-chip" style="background:#f85149">🚫 {escape(g)}</span>' for g in pref.disliked_genres[:3])
    if not chips:
        chips = '<span class="pref-chip">No preferences detected — showing top picks</span>'

    pref_html = f"""
    <div class="pref-section">
        <div class="pref-title">🧠 Parsed Preferences</div>
        <div class="pref-chips">{chips}</div>
    </div>"""

    # Stats
    stats_html = f"""
    <div class="stats-bar">
        <div class="stat-item"><div class="stat-value">{result.total_movies_indexed}</div><div class="stat-label">Movies Indexed</div></div>
        <div class="stat-item"><div class="stat-value">{len(result.recommendations)}</div><div class="stat-label">Recommendations</div></div>
        <div class="stat-item"><div class="stat-value" style="font-size:14px">{escape(result.method_breakdown)}</div><div class="stat-label">Method</div></div>
    </div>"""

    # Movie cards
    cards = ""
    for i, r in enumerate(result.recommendations):
        m = r.movie
        stars = "★" * max(1, round(m.vote_average / 2))
        director_names = ", ".join(d.name for d in m.directors[:2])
        actor_names = ", ".join(a.name for a in m.actors[:3])
        genres_html = "".join(f'<span class="genre-tag">{escape(g.value)}</span>' for g in m.genres[:4])
        score_pct = int(r.final_score * 100)
        backdrop = _tmdb_image_url(m.backdrop_path) or _tmdb_image_url(m.poster_path)
        has_bg = " has-bg" if backdrop else ""
        bg_div = f'<div class="movie-card-bg" style="background-image:url({escape(backdrop)})"></div>' if backdrop else ""
        overview = escape(m.overview[:200]) + ("..." if len(m.overview) > 200 else "")

        cards += f"""
        <div class="movie-card{has_bg}">
            {bg_div}
            <div class="movie-card-content">
                <div class="movie-title">#{i+1} {escape(m.title)}</div>
                <div class="movie-meta">
                    <span class="badge badge-rating">{stars} {m.vote_average:.1f}</span>
                    <span class="badge badge-year">{m.year}</span>
                    <span class="badge badge-score">Match {score_pct}%</span>
                </div>
                <div class="movie-overview">{overview}</div>
                <div class="score-bar"><div class="score-fill" style="width:{score_pct}%"></div></div>
                <div class="movie-crew"><strong>Content:</strong> {r.content_score:.0%} &nbsp; <strong>Collab:</strong> {r.collaborative_score:.0%}</div>
                <div class="explanation">{escape(r.explanation)}</div>
                {f'<div class="movie-crew" style="margin-top:8px"><strong>Director:</strong> {escape(director_names)}</div>' if director_names else ''}
                {f'<div class="movie-crew"><strong>Cast:</strong> {escape(actor_names)}</div>' if actor_names else ''}
                <div class="movie-genres">{genres_html}</div>
            </div>
        </div>"""

    return f"{pref_html}{stats_html}<div class='movie-grid'>{cards}</div>"


# ══════════════════════════════════════════════════════════════════════════════
#  Sentiment Analyzer
# ══════════════════════════════════════════════════════════════════════════════

from collections import defaultdict

_sentiment_index: dict | None = None
_sentiment_cache: dict = {}
_sentiment_name_to_id: dict = {}
_sentiment_domain_map: dict = {}

def _ensure_sentiment_index():
    global _sentiment_index, _sentiment_domain_map
    if _sentiment_index is not None:
        return
    from portfolio.sentiment.pipeline import get_reviews, get_business_domains
    reviews = get_reviews()
    _sentiment_domain_map = get_business_domains()
    _sentiment_index = defaultdict(list)
    for r in reviews:
        _sentiment_index[r.product_id].append(r)


@app.get("/sentiment", response_class=HTMLResponse)
async def sentiment_form(request: Request):
    _ensure_sentiment_index()
    domains = sorted(set(_sentiment_domain_map.values()))
    all_businesses = sorted(set(
        revs[0].title for revs in _sentiment_index.values() if revs
    ))
    return templates.TemplateResponse("sentiment.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "sentiment",
        "domains": domains,
        "businesses": all_businesses,
        "result_html": None,
    })


@app.post("/sentiment", response_class=HTMLResponse)
async def sentiment_analyze(
    request: Request,
    business_a: str = Form(default=""),
    business_b: str = Form(default=""),
    action: str = Form(default="analyze_a"),
):
    _ensure_sentiment_index()
    domains = sorted(set(_sentiment_domain_map.values()))

    if action == "compare" and business_a and business_b:
        result_html = _run_sentiment_compare(business_a, business_b)
    elif business_a:
        result_html = _run_sentiment_analyze(business_a)
    elif business_b:
        result_html = _run_sentiment_analyze(business_b)
    else:
        result_html = '<p class="error-msg">Please select a business.</p>'

    all_businesses = sorted(set(
        revs[0].title for revs in _sentiment_index.values() if revs
    ))
    return templates.TemplateResponse("sentiment.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "sentiment",
        "domains": domains,
        "businesses": all_businesses,
        "result_html": result_html,
        "selected_a": business_a,
        "selected_b": business_b,
    })


@app.get("/api/sentiment/businesses")
async def sentiment_api_businesses(domain: str = ""):
    """API endpoint for filtering businesses by domain (used by JS dropdown)."""
    _ensure_sentiment_index()
    _sentiment_name_to_id.clear()
    results = []
    for pid, revs in _sentiment_index.items():
        title = revs[0].title if revs else ""
        if not title:
            continue
        if not domain or _sentiment_domain_map.get(pid) == domain:
            _sentiment_name_to_id[title] = pid
            results.append(title)
    return sorted(results)


def _resolve_sentiment(selection: str):
    if not selection:
        return None
    _ensure_sentiment_index()
    if selection not in _sentiment_name_to_id:
        for pid, revs in _sentiment_index.items():
            if revs and revs[0].title == selection:
                _sentiment_name_to_id[selection] = pid
                break
    product_id = _sentiment_name_to_id.get(selection)
    if product_id is None:
        return None
    if product_id not in _sentiment_cache:
        from portfolio.sentiment.analyzer import build_product_sentiment
        reviews = _sentiment_index.get(product_id, [])
        if not reviews:
            return None
        _sentiment_cache[product_id] = build_product_sentiment(reviews)
    return _sentiment_cache[product_id]


def _run_sentiment_analyze(selection: str) -> str:
    ps = _resolve_sentiment(selection)
    if ps is None:
        return f'<p class="error-msg">Business not found: {escape(selection)}</p>'
    card = _render_product_card(ps, max_reviews=10)
    domain = _sentiment_domain_map.get(ps.product_id, "")
    return f"""
    <h2>📊 {escape(ps.product_title)}</h2>
    <h4 class="subtitle">{escape(domain)}</h4>
    {card}
    """


def _run_sentiment_compare(sel_a: str, sel_b: str) -> str:
    if sel_a == sel_b:
        return '<p class="error-msg">Please select two different businesses to compare.</p>'
    ps_a = _resolve_sentiment(sel_a)
    ps_b = _resolve_sentiment(sel_b)
    if ps_a is None or ps_b is None:
        return '<p class="error-msg">Business not found.</p>'

    score_a = ps_a.avg_rating * 20 + ps_a.positive_pct * 40 - ps_a.negative_pct * 30
    score_b = ps_b.avg_rating * 20 + ps_b.positive_pct * 40 - ps_b.negative_pct * 30
    if score_a > score_b:
        winner_html = f'<span class="sent-winner sent-winner-a">🏆 {escape(ps_a.product_title)}</span>'
    elif score_b > score_a:
        winner_html = f'<span class="sent-winner sent-winner-b">🏆 {escape(ps_b.product_title)}</span>'
    else:
        winner_html = '<span class="sent-winner" style="background:rgba(110,118,129,0.2);color:#6e7681">🤝 Too close to call</span>'

    card_a = _render_product_card(ps_a, max_reviews=5)
    card_b = _render_product_card(ps_b, max_reviews=5)

    return f"""
    <div class="sent-compare-summary">
        <strong style="font-size:1.1em">⚖️ Comparison Summary</strong>
        {winner_html}
        <div class="sent-stat-row">
            <div class="sent-stat-item" style="color:#58a6ff"><div class="sent-stat-val">{ps_a.avg_rating:.1f}⭐</div><div class="sent-stat-label">{escape(ps_a.product_title[:20])}</div></div>
            <div class="sent-stat-item"><div class="sent-stat-val" style="color:var(--theme-muted)">vs</div></div>
            <div class="sent-stat-item" style="color:#d2991d"><div class="sent-stat-val">{ps_b.avg_rating:.1f}⭐</div><div class="sent-stat-label">{escape(ps_b.product_title[:20])}</div></div>
        </div>
    </div>
    <div class="sent-compare">
        <div class="sent-col sent-col-a">
            <div class="sent-col-title">📊 {escape(ps_a.product_title)}</div>
            <div class="sent-col-subtitle">{escape(_sentiment_domain_map.get(ps_a.product_id, ''))} | ⭐{ps_a.avg_rating:.1f} | {ps_a.total_reviews} reviews</div>
            {card_a}
        </div>
        <div class="sent-col sent-col-b">
            <div class="sent-col-title">📊 {escape(ps_b.product_title)}</div>
            <div class="sent-col-subtitle">{escape(_sentiment_domain_map.get(ps_b.product_id, ''))} | ⭐{ps_b.avg_rating:.1f} | {ps_b.total_reviews} reviews</div>
            {card_b}
        </div>
    </div>
    """


def _render_product_card(ps, max_reviews: int = 6) -> str:
    from portfolio.sentiment.analyzer import generate_verdict
    verdict = generate_verdict(ps)
    pos_w = ps.positive_pct * 100
    neg_w = ps.negative_pct * 100
    neu_w = ps.neutral_pct * 100

    bar = (
        f'<div class="sent-bar-pos" style="width:{pos_w:.1f}%"></div>'
        f'<div class="sent-bar-neu" style="width:{neu_w:.1f}%"></div>'
        f'<div class="sent-bar-neg" style="width:{neg_w:.1f}%"></div>'
    )

    review_rows = ""
    for s in ps.review_sentiments[:max_reviews]:
        icon = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪"}
        review_rows += (
            f'<div class="review-row">'
            f'<strong>{icon.get(s.label, "")} {s.label}</strong> '
            f'<small>({s.score:.0%} confidence | ⭐{s.rating:.1f})</small>'
            f'<p class="review-text">{escape(s.review_text)}</p>'
            f'</div>'
        )

    return f"""
    <div class="sent-verdict"><strong>📝 Customer Verdict</strong><br>{verdict}</div>
    <div class="sent-card">
        <strong>Overall Sentiment</strong> &nbsp;| {ps.total_reviews} reviews &nbsp;| ⭐{ps.avg_rating:.1f} avg
        <div class="sent-bar-wrap">{bar}</div>
        <span class="sent-pos">🟢 Positive {pos_w:.1f}%</span> &nbsp;
        <span class="sent-neu">⚪ Neutral {neu_w:.1f}%</span> &nbsp;
        <span class="sent-neg">🔴 Negative {neg_w:.1f}%</span>
    </div>
    <h3 style="font-size:1em;margin-top:16px">Review Samples</h3>
    {review_rows}
    <p class="review-count">Showing {min(max_reviews, ps.total_reviews)} of {ps.total_reviews} reviews</p>
    """


# ══════════════════════════════════════════════════════════════════════════════
#  Trading
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/trading", response_class=HTMLResponse)
async def trading_form(request: Request):
    return templates.TemplateResponse("trading.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "trading",
        "result_html": None,
    })


@app.post("/trading", response_class=HTMLResponse)
async def trading_run(
    request: Request,
    symbol: str = Form(default="AAPL"),
):
    result_html = _run_trading_workflow(symbol)
    return templates.TemplateResponse("trading.html", {
        "request": request,
        "config": _load_config(),
        "active_page": "trading",
        "result_html": result_html,
        "symbol": symbol,
    })


def _run_trading_workflow(symbol: str) -> str:
    if not symbol or not symbol.strip():
        return '<p class="error-msg">Please enter a stock symbol.</p>'
    try:
        from portfolio.trading.graph.trading_graph import run_trading_workflow
        state = run_trading_workflow(symbol.strip().upper())
    except Exception as e:
        return f'<p class="error-msg">Workflow failed: {escape(str(e))}</p>'

    cards = ""

    # Security
    security = state.get("security")
    if security:
        content = ""
        if security.company_name:
            content += f"🏢 <b>Company:</b> {escape(security.company_name)}<br>"
        if security.sector and security.industry:
            content += f"📊 <b>Sector/Industry:</b> {escape(security.sector)} / {escape(security.industry)}<br>"
        if security.current_price:
            content += f"💵 <b>Current Price:</b> ${security.current_price:.2f}<br>"
        content += f"<br>{'✅ Options Available' if security.is_optionable else '❌ No Options Available'}<br><br>"
        content += f"<i>🧠 Reasoning:</i><br>{escape(security.reasoning)}"
        cards += _agent_card("🔍", "Security Agent — Identification", content, "var(--trading-accent)")

    # Sentiment
    sentiment = state.get("sentiment")
    if sentiment:
        fg = sentiment.fear_greed
        content = f"📊 <b>CNN Fear & Greed:</b> {fg.value}/100 — {fg.zone.value}<br>"
        content += f"📈 <b>Market Trend:</b> {escape(sentiment.market_trend)}<br>"
        content += f"⚠️ <b>Risk:</b> {escape(sentiment.risk_assessment)}<br>"
        if sentiment.top_news:
            content += "<br>📰 <b>Key News:</b><br>"
            for n in sentiment.top_news[:5]:
                icon = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪"}.get(n.impact, "⚪")
                content += f"  {icon} [{escape(n.source)}] {escape(n.headline[:120])}<br>"
        content += f"<br><i>🧠 Analysis:</i><br>{escape(sentiment.reasoning[:400])}..."
        cards += _agent_card("🌐", "Risk & Sentiment Agent", content, "var(--trading-teal)")

    # Regime
    regime = state.get("regime")
    if regime:
        content = f'<b style="font-size:1.2em">{regime.regime.value}</b><br>'
        content += f"Confidence: {regime.confidence:.0%}<br>"
        if regime.volatility_index is not None:
            content += f"📉 Volatility: {regime.volatility_index:.1%}<br>"
        if regime.trend_strength is not None:
            content += f"📈 Trend Strength: {regime.trend_strength:.1%}<br>"
        content += f"<br><i>🧠 Reasoning:</i><br>{escape(regime.reasoning[:500])}"
        cards += _agent_card("🔄", "Regime Detection Agent", content, "var(--trading-amber)")

    # Decision
    decision = state.get("strategy")
    if decision:
        from portfolio.trading.models import OptionStrategy
        strat_colors = {"Long Call": "var(--trading-green)", "Long Put": "var(--trading-red)", "Long Strangle": "var(--trading-purple)", "No Trade": "var(--trading-amber)"}
        color = strat_colors.get(decision.strategy.value, "var(--trading-amber)")
        content = f'<b style="font-size:1.3em; color:{color}">{decision.strategy.value}</b><br>'
        content += f"Confidence: {decision.confidence:.0%}<br>"
        if decision.recommended_strike:
            content += f"💵 Strike: ${decision.recommended_strike:.2f}<br>"
        if decision.max_risk is not None:
            content += f"⚠️ Max Risk: ${decision.max_risk:.2f}<br>"
        content += f"<br><i>🧠 Rationale:</i><br>{escape(decision.rationale)}"
        cards += _agent_card("🎯", f"Decision Agent — {escape(symbol)}", content, color)

    # Execution
    execution = state.get("execution")
    if execution:
        from portfolio.trading.models import OptionStrategy
        if execution.request.strategy == OptionStrategy.NO_TRADE:
            content = "🚫 <b>No Trade Executed</b><br><br>Agent recommended no trade under current conditions."
            cards += _agent_card("⏸️", f"Execution Agent — {escape(symbol)}", content, "var(--trading-amber)")
        else:
            conf = execution.confirmation
            content = f"📋 Order: {escape(execution.request.order_id)}<br>"
            content += f"🎯 Status: {escape(str(conf.get('status', 'N/A')))}<br>"
            fp = conf.get("filled_price")
            if fp:
                content += f"💵 Fill Price: ${fp:.2f}/contract<br>"
            tc = conf.get("total_cost")
            if tc:
                content += f"💰 Total Cost: ${tc:,.2f}<br>"
            cards += _agent_card("💸", "Execution Agent", content, "var(--trading-green)")

    return f'<div class="trading-results">{cards}</div>'


def _agent_card(icon: str, title: str, content: str, accent: str) -> str:
    return f"""
    <div class="trading-card" style="border-left:4px solid {accent}">
        <div class="trading-card-header">
            <span class="trading-card-icon">{icon}</span>
            <strong>{escape(title)}</strong>
        </div>
        <div class="trading-card-body">{content}</div>
    </div>"""
