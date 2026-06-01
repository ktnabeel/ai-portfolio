# AI Portfolio — Skills & Capabilities

## Core Stack

| Area | Technologies |
|------|-------------|
| **Language** | Python 3.11+ with full type hints |
| **UI Framework** | Gradio (Blocks API, custom CSS, theme toggling) |
| **ML / Linear Algebra** | NumPy, scikit-learn (TF-IDF, TruncatedSVD, cosine similarity) |
| **Agent Orchestration** | LangGraph, LangChain, OpenAI, Anthropic |
| **API Integration** | TMDB, Polygon.io, yfinance, CNN Fear & Greed scraping |
| **Quant / Pricing** | Black-Scholes options pricing, synthetic chain generation |
| **Protocols** | Model Context Protocol (MCP) paper-trading server |
| **Persistence** | SQLite (project tiles auto-seeded on startup) |
| **Data Modeling** | Frozen dataclasses, Enums, immutability-first design |
| **Package Management** | `uv` (fast Python package manager) |
| **Deployment** | Hugging Face Spaces (Gradio), Vercel (static HTML export) |

## Project Skills by Tab

### 📋 Portfolio Landing Page
- Glassmorphism CSS (`backdrop-filter: blur()`, semi-transparent panels)
- Sticky floating top bar with smooth scrolling
- Spring-bounce card hover animations (`cubic-bezier(.34,1.56,.64,1)`)
- Light/dark theme toggle persisted to `localStorage`
- Responsive grid layout with CSS Grid
- Sidebar elevation effects and sticky positioning
- Font smoothing and micro-interactions

### 💹 Financial Agent
- Multi-agent portfolio decision system with five specialized agents (Market Data, Technical, Fundamental, Sentiment, Risk) feeding a `DecisionOrchestrator`
- Per-agent `AgentSignal` outputs (BUY / SELL / HOLD, confidence, rationale) aggregated into a `PortfolioDecision`
- `StockDecision` + `PortfolioHolding` dataclasses with enums for `SignalType`, `RiskLevel`, `DecisionAction`
- Gradio tab with structured per-agent output rendering

### 📄 Claim Processing
- Insurance claim automation pipeline
- Multi-step processing with status tracking
- Gradio tab with step-by-step progress display

### 🎬 Movie Recommendations
- **NLP Preference Extraction**: Regex + keyword heuristics simulating LLM parsing (genres, people, mood, year range, rating)
- **Two-Tower Embeddings**: TF-IDF text encoding + one-hot genre encoding + scalar feature normalization → cosine similarity
- **Collaborative Filtering**: SVD matrix factorization on pseudo-ratings matrix (genre archetypes × movies)
- **Ensemble Recommendation**: Weighted combination (50% content + 35% collaborative + 15% popularity)
- **TMDB API Integration**: Rate-limited client with session pooling, genre caching, multi-endpoint discovery
- **Data Pipeline**: Genre-batched discovery, deduplication, full credit/keyword enrichment, sample fallback
- **TMDB Image CDN**: Public backdrop/poster image loading without API key
- **Gradio UI**: Card-based layout with gradient overlays, score bars, preference chips, stats bar
- **Dual-mode**: Works with live TMDB API or offline with 15-movie curated sample

### 💬 Sentiment Analyzer
- Product-review sentiment classification on Amazon reviews
- `Review` → `ReviewSentiment` → `ProductSentiment` aggregation pipeline
- Score distributions and product-level summaries
- Sample-data fallback when no live source is configured

### 📈 Trading
- **Five-agent LangGraph pipeline with human review gate**: Security → Risk/Sentiment → Regime → Decision → Human Review → Execution
- **OpenAI/Anthropic reasoning** per agent with full rationale surfaced in the UI
- **Hoverable pipeline audit map** with per-agent input/output traces, scrollable tooltips, and path summaries
- **Human-in-the-loop execution review** with approve/reject controls before paper orders are sent
- **Dedicated order confirmation panel** separate from MCP connectivity/tool-call traces
- **Options strategies**: Long Call, Long Put, Long Strangle, No-Trade
- **Black-Scholes pricing** for synthetic option chains when Polygon.io is unavailable
- **CNN Fear & Greed + news scrapers** feeding the risk/sentiment agent
- **MCP paper-trading server**: `place_option_order`, `get_account_status`, `cancel_order`, `reset_account` ($100k starting balance, $0.65/contract commission)
- **Graceful degradation**: rule-based fallbacks if LLM providers / Polygon / yfinance are unavailable

## Design Patterns
- Immutable data models (`@dataclass(frozen=True)`)
- Lazy initialization with singleton caching (`_get_recommender()`)
- Strategy pattern (pluggable preference parser — swappable with real LLM)
- Pipeline pattern (fetch → deduplicate → enrich → index → recommend)
- Ensemble pattern (multiple scorers with configurable weights)
- CSS custom properties for theme management (`--theme-*` variables)

## DevOps & Tooling
- `uv` for fast dependency management and script running
- `pyproject.toml` for project metadata and dependencies
- Static HTML export for Vercel deployment
- Gradio `launch()` for Hugging Face Spaces
- YAML-based site configuration (`portfolio.yaml`)
- Seed/export scripts for project management
