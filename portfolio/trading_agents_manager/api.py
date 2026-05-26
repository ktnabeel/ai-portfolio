"""FastAPI application for the TradingAgents Portfolio Manager.

Exposes REST endpoints for running multi-agent market analysis,
retrieving results, and health monitoring.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from .manager import PortfolioManager
from .models import AnalysisRequest, AnalysisResponse, AnalysisStatus, HealthResponse

# ── App & State ──────────────────────────────────────────────────────────

app = FastAPI(
    title="TradingAgents Portfolio Manager",
    description="Multi-agent trading analysis API powered by TradingAgents LangGraph pipeline. "
                "Orchestrates Security, Sentiment, Regime, Decision, and Execution agents.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

_start_time = time.time()
_manager = PortfolioManager()


# ── Endpoints ────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health check — verifies the API is running."""
    try:
        import tradingagents
        ta_version = getattr(tradingagents, "__version__", "0.2.4")
    except ImportError:
        ta_version = "not installed"

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        tradingagents_version=ta_version,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    """Run a full multi-agent analysis on the given ticker symbol.

    Orchestrates the complete pipeline:
    Security → Sentiment → Regime → Decision → Execution
    """
    return _manager.analyze(request.symbol, request.date)


@app.get("/api/v1/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str) -> AnalysisResponse:
    """Retrieve a previously-run analysis by ID."""
    analysis = _manager.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    # Return the full stored response if available, otherwise return metadata-only
    stored_response = analysis.get("response")
    if stored_response is not None:
        return stored_response

    return AnalysisResponse(
        id=analysis_id,
        symbol=analysis.get("symbol", ""),
        status=analysis.get("status", AnalysisStatus.FAILED),
        error=analysis.get("error"),
    )


@app.get("/api/v1/symbols")
async def list_symbols(
    q: Optional[str] = Query(default=None, description="Search query for symbol lookup"),
) -> list[dict[str, str]]:
    """List supported stock symbols (filtered by optional query)."""
    symbols = [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
        {"symbol": "MSFT", "name": "Microsoft Corp.", "sector": "Technology"},
        {"symbol": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Communication"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Cyclical"},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "sector": "ETF"},
    ]
    if q:
        q_lower = q.lower()
        symbols = [s for s in symbols if q_lower in s["symbol"].lower() or q_lower in s["name"].lower()]
    return symbols


# ── Entrypoint ──────────────────────────────────────────────────────────

def run(host: str = "127.0.0.1", port: int = 8100) -> None:
    """Launch the FastAPI server via uvicorn."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
