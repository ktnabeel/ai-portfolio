from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "portfolio.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 7860,
    },
    "site": {
        "title": "AI Project Portfolio",
        "meta_description": "AI project portfolio for applied machine learning, agents, automation, and product prototypes.",
        "brand": "neurons.fyi",
        "brand_mark": "N",
        "kicker": "Applied AI Portfolio",
        "headline": "Python AI projects for agents, automation, and analytics.",
        "side_copy": "A public LinkedIn-ready portfolio focused on practical AI systems, workflow automation, and decision support prototypes.",
        "intro_kicker": "Portfolio Workspace",
        "intro_headline": "Selected AI builds, framed as concise case studies.",
        "intro_copy": "Each tile gives a fast read on the workflow, architecture, AI role, and production proof behind the work.",
        "project_kicker": "Project Index",
        "project_heading": "AI project tiles",
        "status_label": "Public showcase",
        "linkedin_url": "https://www.linkedin.com/",
    },
    "stats": [
        {"label": "AI demos", "value": "8"},
        {"label": "Agent workflows", "value": "5+"},
        {"label": "VPS deploy", "value": "Linux"},
    ],
    "proof_strip": [
        {"label": "Agent Architecture", "value": "LangGraph pipelines, tool calls, fallback paths"},
        {"label": "Production Wiring", "value": "FastAPI surfaces, Linux deploy scripts, health checks"},
        {"label": "Reliability", "value": "Typed Pydantic models, pytest coverage, cached external data"},
        {"label": "Domain Range", "value": "Finance, insurance, NLP, recommendations"},
    ],
    "tabs": {
        "trading_agents": "Portfolio Manager",
        "trading": "Trading Desk",
        "underwriting": "Insurance Underwriting",
        "claim": "Claim Processing",
        "movie": "Movie Recommendations",
        "sentiment": "Sentiment Analyzer",
        "resume_matcher": "Resume Matcher",
        "financial": "Financial Agent",
    },
    "project_tab_links": {
        "Portfolio Manager": "trading_agents",
        "Trading Desk": "trading",
        "Claim Processing": "claim",
        "Insurance Underwriting Agent": "underwriting",
        "Finance Planning": "financial",
        "Movie Recommendations": "movie",
        "Product Review Sentiment Analyzer": "sentiment",
        "Resume Matcher": "resume_matcher",
    },
    "project_demo_urls": {
        "Portfolio Manager": "",
        "Trading Desk": "",
        "Claim Processing": "",
        "Insurance Underwriting Agent": "",
        "Product Review Sentiment Analyzer": "",
        "Resume Matcher": "",
        "Finance Planning": "",
        "Movie Recommendations": "",
    },
    "projects": [
        {
            "key": "trading",
            "title": "Trading Desk",
            "description": "Multi-agent options trading desk with Black-Scholes pricing, MCP paper-trading server, and LangGraph-orchestrated agent pipeline for market analysis.",
            "tech_stack": "Python, LangGraph, LangChain, yfinance, Black-Scholes",
            "status": "Built",
            "tags": ["Agents", "Finance", "Trading", "Options"],
            "tab": "trading",
        },
        {
            "key": "trading_agents",
            "title": "Portfolio Manager",
            "description": "Multi-agent portfolio manager powered by LangGraph — FastAPI service orchestrating Security, Sentiment, Regime, Decision, and Execution agents for market analysis.",
            "tech_stack": "Python, FastAPI, LangGraph, yfinance, Pydantic",
            "status": "Built",
            "tags": ["Agents", "Finance", "FastAPI", "LangGraph"],
            "tab": "trading_agents",
        },
        {
            "key": "claim",
            "title": "Claim Processing",
            "description": "AI-assisted workflow for reviewing claims, extracting details, and routing decisions.",
            "tech_stack": "Python, document AI, workflow automation",
            "status": "Built",
            "tags": ["Insurance", "Automation", "Documents"],
            "tab": "claim",
        },
        {
            "key": "underwriting",
            "title": "Insurance Underwriting Agent",
            "description": "Agentic underwriting assistant that extracts application data, scans for risk factors across health/occupation/lifestyle/financial dimensions, builds policy context, and generates structured decisions with chain-of-thought reasoning.",
            "tech_stack": "Python, rule-based NLP, underwriting risk engine, Gradio",
            "status": "Built",
            "tags": ["Insurance", "Agents", "Risk"],
            "tab": "underwriting",
        },
        {
            "key": "sentiment",
            "title": "Product Review Sentiment Analyzer",
            "description": "Sentiment analysis app for summarizing customer reviews and product feedback patterns.",
            "tech_stack": "Python, NLP, sentiment analysis",
            "status": "Built",
            "tags": ["NLP", "Sentiment", "Analytics"],
            "tab": "sentiment",
        },
        {
            "key": "financial",
            "title": "Finance Planning",
            "description": "AI planning assistant for budgeting, scenario analysis, and financial goal tracking.",
            "tech_stack": "Python, analytics, LLM workflows",
            "status": "Built",
            "tags": ["Finance", "Planning", "Assistant"],
            "tab": "financial",
        },
        {
            "key": "resume_matcher",
            "title": "Resume Matcher",
            "description": "NVIDIA-backed resume-to-job matching app that scores fit, highlights gaps, and recommends targeted resume edits.",
            "tech_stack": "Python, Gradio, NVIDIA API, LangChain",
            "status": "Built",
            "tags": ["NLP", "Recruiting", "NVIDIA", "LLM"],
            "tab": "resume_matcher",
        },
        {
            "key": "movie",
            "title": "Movie Recommendations",
            "description": "AI-powered movie recommender combining two-tower embeddings, SVD collaborative filtering, and LLM-style preference extraction from TMDB data.",
            "tech_stack": "Python, scikit-learn, TMDB API, Gradio",
            "status": "Built",
            "tags": ["Recommendations", "ML", "NLP"],
            "tab": "movie",
        },
    ],
    "capabilities": [
        {"title": "Agents", "description": "Research, routing, planning"},
        {"title": "NLP", "description": "Reviews, claims, sentiment"},
        {"title": "Decision Support", "description": "Finance, underwriting, recommendations"},
    ],
}


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    path = Path(path)
    if not path.exists():
        return config

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")

    _merge(config, raw)
    raw_site = raw.get("site")
    if isinstance(raw_site, dict) and "headline" in raw_site and "intro_headline" not in raw_site:
        config["site"]["intro_headline"] = config["site"]["headline"]
    config["server"]["port"] = int(config["server"]["port"])
    config["server"]["host"] = str(config["server"]["host"])
    config["site"].setdefault("copyright", f"© {datetime.now().year} neurons.fyi")
    _derive_project_tab_links(config)
    return config


def get_config_value(key_path: str, path: str | Path = CONFIG_PATH) -> Any:
    value: Any = load_config(path)
    for part in key_path.split("."):
        value = value[part]
    return value


def _merge(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = value


def _derive_project_tab_links(config: dict[str, Any]) -> None:
    """Add title -> tab mappings from YAML project entries.

    This keeps project links stable when visible project titles are edited.
    Existing explicit project_tab_links remain as fallback mappings.
    """
    tab_links = dict(config.get("project_tab_links", {}))
    for project in config.get("projects", []):
        if not isinstance(project, dict):
            continue
        title = project.get("title")
        tab = project.get("tab") or project.get("tab_id") or project.get("key")
        if title and tab:
            tab_links[str(title)] = str(tab)
    config["project_tab_links"] = tab_links
