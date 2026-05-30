"""FastAPI app for lightweight Vercel/static-style deployment.

The main local application is Gradio in app.py. This API module remains a
small independent FastAPI surface for portfolio/claims routes.
"""

from __future__ import annotations

import os
import re
from html import escape
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Nabeel's AI Project Portfolio")

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)


def _render(name: str, context: dict) -> HTMLResponse:
    template = _jinja_env.get_template(name)
    return HTMLResponse(template.render(**context))


def _load_config():
    from portfolio.config import load_config

    return load_config()


def _get_projects():
    from portfolio.db import get_projects, init_db, seed_projects
    from portfolio.project_templates import get_project_templates

    config = _load_config()
    db_path = Path("/tmp/portfolio.db") if "VERCEL" in os.environ else BASE_DIR / "portfolio.db"
    init_db(db_path)
    seed_projects(db_path, get_project_templates(config))
    return get_projects(db_path)


@app.get("/", response_class=HTMLResponse)
async def portfolio(request: Request):
    from portfolio.render import _PROJECT_DETAILS

    config = _load_config()
    return _render("index.html", {
        "request": request,
        "config": config,
        "projects": _get_projects(),
        "project_details": _PROJECT_DETAILS,
        "active_page": "portfolio",
        "app_routes": {
            "trading_agents": "/portfolio-manager",
            "underwriting": "/underwriting",
            "claim": "/claims",
            "movie": "/movies",
            "sentiment": "/sentiment",
            "financial": "/financial",
            "trading": "/trading",
        },
    })


@app.get("/claims", response_class=HTMLResponse)
async def claims_form(request: Request):
    return _render("claims.html", {
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
    result_html = _run_batch_claims(claim_text) if mode == "batch" else _run_single_claim(claim_text)
    return _render("claims.html", {
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

    result = ClaimProcessor().process_claim(claim_text)
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
    <div class="claim-metric-card"><table class="extracted-table">{rows}</table></div>
    <h3>Fraud Assessment</h3>
    <div class="claim-metric-card"><strong>Risk: <span class="{fraud_cls}">{result.fraud_risk.value}</span></strong><br><small>{escape(result.fraud_reasoning)}</small></div>
    <h3>Severity Assessment</h3>
    <div class="claim-metric-card"><strong>Severity: <span class="{sev_cls}">{result.severity.value}</span></strong><br><small>{escape(result.severity_reasoning)}</small></div>
    <h3>Routing Decision</h3>
    <div class="claim-metric-card"><strong>Action: <span class="{routing_cls}">{result.routing.value}</span></strong><br><small>{escape(result.routing_reasoning)}</small></div>
    """


def _run_batch_claims(claims_text: str) -> str:
    if not claims_text or not claims_text.strip():
        return '<p class="error-msg">Please enter claim details.</p>'
    from portfolio.claim_processing.models import RoutingDecision
    from portfolio.claim_processing.processor import ClaimProcessor

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
        amount_str = f"${result.claim.amount:,.2f}" if result.claim.amount else "-"
        claimant = result.claim.claimant or f"Claim #{i}"
        rows += (
            f'<div class="claim-metric-card"><strong>{escape(claimant)}</strong> &nbsp;| '
            f'{result.claim.claim_type.value} &nbsp;| {amount_str}'
            f' &nbsp;| Fraud: <span class="{fraud_cls}">{result.fraud_risk.value}</span>'
            f' &nbsp;| <span class="{routing_cls}">{result.routing.value}</span></div>'
        )
    summary = (
        f'<div class="claim-metric-card" style="margin-bottom:16px"><strong>Batch Summary ({len(claims)} claims)</strong><br>'
        f'<span class="result-approve">Approve: {approve}</span> &nbsp;| '
        f'<span class="result-review">Review: {review}</span> &nbsp;| '
        f'<span class="result-deny">Deny: {deny}</span> &nbsp;| '
        f'<span class="result-escalate">Escalate: {escalate}</span></div>'
    )
    return f"<h2>Batch Claim Processing</h2>{summary}{rows}"


def _routing_color(v: str) -> str:
    return {"Approve": "result-approve", "Deny": "result-deny", "Review": "result-review", "Escalate": "result-escalate"}.get(v, "result-review")


def _fraud_color(v: str) -> str:
    return {"Low": "fraud-low", "Medium": "fraud-medium", "High": "fraud-high"}.get(v, "fraud-low")


def _severity_color(v: str) -> str:
    return {"Low": "severity-low", "Medium": "severity-medium", "High": "severity-high", "Critical": "severity-critical"}.get(v, "severity-low")
