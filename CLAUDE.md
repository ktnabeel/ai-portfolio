# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**AI Portfolio** is a Python-based portfolio landing page showcasing public AI project tiles. Built with Gradio for Hugging Face Spaces deployment, with optional static HTML export for Vercel.

Key tabs:
- **Portfolio** — Landing page with project cards, capability strip, glassmorphism floating UI
- **Financial Agent** — Multi-agent portfolio decision system (Market Data → Technical → Fundamental → Sentiment → Risk → Orchestrator)
- **Claim Processing** — Insurance claim automation pipeline
- **Movie Recommendations** — AI-powered movie recommender (two-tower embeddings + SVD collaborative filtering + LLM-style preference parsing)
- **Sentiment Analyzer** — Product review sentiment analysis on Amazon reviews
- **Insurance Underwriting** — Agentic underwriting assistant with 4-dimension risk assessment (Health, Occupation, Lifestyle, Financial), policy context builder, and chain-of-thought decision engine
- **TradingAgents Manager** — FastAPI portfolio manager orchestrating LangGraph agents (Security → Risk/Sentiment → Regime → Decision → Execution)
- **Trading** — Multi-agent options trading via LangGraph (Security → Risk/Sentiment → Regime → Decision → Execution), MCP paper-trading server, Black-Scholes pricing

## Development Commands

```bash
# Install dependencies
cd projects/ai-portfolio && uv sync

# Run the app locally
uv run python app.py

# Type-check / import validation
uv run python -c "from portfolio.movie_recommender import MovieRecommender, MoviePipeline; print('OK')"

# Run tests (if available)
uv run pytest

# Export static HTML for Vercel
uv run python scripts/export_static.py
```

## Architecture

```
ai-portfolio/
├── app.py                  # Gradio app entry point — builds tabs, applies CSS
├── portfolio.yaml          # Site config (port, LinkedIn, stats, capabilities)
├── portfolio.db            # SQLite — auto-seeded with project tiles on startup
├── portfolio/
│   ├── config.py           # YAML config loader
│   ├── db.py               # SQLite init / seed / read helpers
│   ├── models.py           # Project tile dataclass
│   ├── project_templates.py # Seed data for portfolio tiles
│   ├── render.py           # Landing page CSS + HTML (glassmorphism, floating top bar)
│   ├── underwriting/       # Insurance Underwriting Agent tab
│   │   ├── __init__.py     # Package exports (lazy gradio import)
│   │   ├── models.py       # ApplicationData, UnderwritingResult, RiskFactor, enums
│   │   ├── agent.py        # UnderwritingAgent — extraction, risk assessment, policy context, decision engine
│   │   └── render.py       # Gradio UI + UNDERWRITING_CSS
│   ├── financial/          # Financial Agent tab — multi-agent portfolio decisions
│   │   ├── __init__.py     # Package exports + DARK_CSS
│   │   ├── models.py       # AgentSignal, PortfolioHolding, StockDecision, enums
│   │   ├── _utils.py       # Shared helpers
│   │   ├── market_data.py  # MarketDataAgent — price/volume ingestion
│   │   ├── technical.py    # TechnicalAnalysisAgent — indicators
│   │   ├── fundamental.py  # FundamentalAnalysisAgent — ratios / financials
│   │   ├── sentiment.py    # SentimentAnalysisAgent — news/social signals
│   │   ├── risk.py         # RiskAssessmentAgent — exposure & risk scoring
│   │   ├── orchestrator.py # DecisionOrchestrator — combines agent signals
│   │   └── render.py       # Gradio UI rendering
│   ├── claim_processing/   # Claim Processing tab
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── processor.py
│   │   └── render.py
│   ├── movie_recommender/  # Movie Recommendations tab
│   │   ├── __init__.py     # Package exports
│   │   ├── models.py       # Movie, Person, Genre, UserPreference, etc.
│   │   ├── tmdb_client.py  # TMDB API wrapper (rate-limited)
│   │   ├── embeddings.py   # Two-tower model (MovieEmbedder + UserEmbedder)
│   │   ├── collaborative.py # SVD collaborative filtering
│   │   ├── preference_parser.py # LLM-style NLP preference extraction
│   │   ├── pipeline.py     # Data ingestion pipeline (TMDB or sample fallback)
│   │   ├── recommender.py  # Ensemble recommender (content + collab + popularity)
│   │   └── render.py       # Gradio UI + CSS + TMDB image CDN helpers
│   ├── sentiment/          # Sentiment Analyzer tab — Amazon product reviews
│   │   ├── __init__.py     # Package exports + SENTIMENT_CSS
│   │   ├── models.py       # Review, ReviewSentiment, ProductSentiment
│   │   ├── pipeline.py     # Review fetching / sample fallback
│   │   ├── analyzer.py     # Sentiment classification + aggregation
│   │   └── render.py       # Gradio UI rendering
│   └── trading/            # Trading tab — multi-agent options trading via LangGraph
│       ├── __init__.py
│       ├── models.py       # Trading domain dataclasses
│       ├── agents/         # Security, Risk/Sentiment, Regime, Decision, Execution
│       ├── graph/          # LangGraph state + graph wiring
│       ├── options/        # Black-Scholes pricing, Polygon.io options client
│       ├── scrapers/       # CNN Fear & Greed, news scrapers
│       ├── mcp/            # MCP paper-trading server + broker
│       ├── ui/             # Gradio UI + TRADING_CSS
│       └── docs/           # Trading-specific README / ARCHITECTURE / FLOWS
├── scripts/                # Admin scripts (seed_templates, add_project, export_static, config_value)
└── README.md
```

## CSS Theme Variables

Two themes (light/dark) toggled via `data-theme` attribute on `<html>`. Key variables:

| Variable | Light | Dark |
|----------|-------|------|
| `--theme-bg` | `#f7faf8` | `#0d1117` |
| `--theme-ink` | `#1a1a2e` | `#c9d1d9` |
| `--theme-muted` | `#4b5563` | `#b0b8c1` |
| `--theme-panel` | `#ffffff` | `#161b22` |
| `--theme-blue` | `#2563eb` | `#58a6ff` |
| `--theme-green` | `#16a34a` | `#3fb950` |

## Code Conventions

- **Style**: Follow existing conventions in each file — match surrounding formatting, naming, and structure
- **Imports**: Standard library → third-party → local. Use `from .module import X` for package-internal imports
- **Types**: Use type hints everywhere (`list[Movie]`, `dict[str, float]`, `Optional[str]`)
- **Docstrings**: Every public function/method must have a docstring. Use Google-style with Args/Returns sections
- **Frozen dataclasses**: Immutable data models use `@dataclass(frozen=True)` with `field(default_factory=...)`
- **Gradio UI**: Use `gr.Blocks(elem_id=...)` for tabs, CSS scoped with `#tab-id` selectors
- **Theme toggle**: JavaScript in `render.py` manages `data-theme` on `<html>` and persists to `localStorage`

## Dependencies

Managed via `uv` with `pyproject.toml`. Key packages:
- `gradio` — UI framework
- `numpy`, `scikit-learn` — ML/embeddings
- `requests` — TMDB / scraping HTTP client
- `pyyaml` — Config parsing
- `langgraph`, `langchain-openai` — Trading-agent orchestration (GPT-4o reasoning)
- `yfinance` — Financial / trading market data
- `beautifulsoup4` — CNN Fear & Greed + news scraping

See `portfolio/trading/docs/` for trading-subsystem usage, architecture, and flow docs.
