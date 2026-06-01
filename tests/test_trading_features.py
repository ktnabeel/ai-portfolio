"""Tests for the trading follow-up features."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

from portfolio.trading.agents.risk_sentiment_agent import RiskSentimentAgent
from portfolio.trading.models import (
    ExecutionResult,
    FearGreedData,
    FearGreedZone,
    MarketRegime,
    OptionChain,
    OptionContract,
    OptionStrategy,
    OrderRequest,
    RegimeOutput,
    RiskSentimentOutput,
    SecurityInfo,
    StrategyDecision,
)
from portfolio.trading.scrapers import cnn_fear_greed as cnn
from portfolio.trading.ui.trading_ui import (
    _clear_order_confirmation,
    _render_sentiment_card,
    _run_analysis,
    _run_execution_phase,
)


def test_cnn_fear_greed_fetch_is_cached(monkeypatch) -> None:
    """The browser fetch should be reused within the TTL."""
    monkeypatch.setattr(cnn, "_CACHE_VALUE", None, raising=False)
    monkeypatch.setattr(cnn, "_CACHE_AT", 0.0, raising=False)

    result = FearGreedData(
        value=60,
        zone=FearGreedZone.GREED,
        description="Investors are optimistic and taking on more risk. Momentum is positive.",
        previous_close=59,
        one_week_ago=58,
        one_month_ago=66,
        one_year_ago=64,
        timestamp=datetime.now(timezone.utc),
        raw_score=60.2,
        source_url=cnn.FEAR_GREED_URL,
        source_method="playwright-browser",
    )

    calls = []

    def fake_playwright():
        calls.append("playwright")
        return result

    monkeypatch.setattr(cnn, "_fetch_with_playwright", fake_playwright)
    monkeypatch.setattr(cnn, "_fetch_with_httpx", lambda: result)

    first = cnn.fetch_fear_greed()
    second = cnn.fetch_fear_greed()

    assert first.value == 60
    assert second.value == 60
    assert calls == ["playwright"]


def test_sentiment_card_shows_freshness() -> None:
    """The sentiment card should surface the CNN data freshness."""
    sentiment = RiskSentimentOutput(
        fear_greed=FearGreedData(
            value=60,
            zone=FearGreedZone.GREED,
            description="Optimistic.",
            timestamp=datetime.now(timezone.utc),
            source_method="playwright-browser",
            source_url="https://www.cnn.com/markets/fear-and-greed",
        ),
        top_news=[],
        market_trend="Positive",
        risk_assessment="MODERATE",
        reasoning="",
    )

    html = _render_sentiment_card(sentiment)

    assert "Freshness:" in html
    assert "playwright-browser" in html


def test_run_analysis_persists_run_record(monkeypatch) -> None:
    """The serialized analysis state should keep the full run record."""
    fake_state = {
        "symbol": "AAPL",
        "security": SecurityInfo(symbol="AAPL", company_name="Apple Inc.", is_optionable=True),
        "sentiment": RiskSentimentOutput(
            fear_greed=FearGreedData(
                value=60,
                zone=FearGreedZone.GREED,
                description="Optimistic.",
                timestamp=datetime.now(timezone.utc),
                source_method="playwright-browser",
                source_url="https://www.cnn.com/markets/fear-and-greed",
            ),
            top_news=[],
            market_trend="Positive",
            risk_assessment="MODERATE",
            reasoning="",
        ),
        "regime": RegimeOutput(
            regime=MarketRegime.BULL,
            confidence=0.8,
            sp500_trend="UP",
            reasoning="Bullish.",
        ),
        "options_chain": OptionChain(
            symbol="AAPL",
            underlying_price=185.0,
            expiration_dates=["2026-06-19"],
            calls=[OptionContract(symbol="AAPL1", strike=185, expiration="2026-06-19", option_type="call")],
            puts=[OptionContract(symbol="AAPL2", strike=180, expiration="2026-06-19", option_type="put")],
        ),
        "strategy": StrategyDecision(
            strategy=OptionStrategy.CALL,
            confidence=0.8,
            rationale="Bullish regime and supportive sentiment.",
            recommended_strike=185,
            recommended_expiration="2026-06-19",
        ),
        "error": "",
        "stage": "decision",
        "log": ["[Security] ok", "[Risk/Sentiment] ok", "[Regime] ok", "[Decision] ok"],
    }

    monkeypatch.setattr(
        "portfolio.trading.ui.trading_ui.run_trading_workflow",
        lambda **_: fake_state,
    )

    _, _, _, _, state_json = _run_analysis(
        symbol="AAPL",
        api_key="",
        provider="openai",
        model="",
        show_trace=False,
    )

    payload = json.loads(state_json)

    assert payload["flow_traces"]["decision"]["output"].startswith("Strategy: Long Call")
    assert payload["run_record"]["path_summary"].startswith("Why this path:")
    assert payload["run_record"]["agent_traces"]["sentiment"]["output"].startswith("Fear & Greed: 60/100")


def test_run_execution_phase_splits_confirmation_from_trace() -> None:
    state_json = json.dumps({
        "symbol": "AAPL",
        "strategy_value": "Long Call",
        "strategy_strike": 185,
        "strategy_expiration": "2026-06-19",
        "deterministic": True,
        "flow_traces": {},
        "run_record": {"path_summary": "Why this path: test."},
    })
    result = ExecutionResult(
        request=OrderRequest(
            order_id="ORD-LEFT-1",
            symbol="AAPL",
            strategy=OptionStrategy.CALL,
            strike=185,
            expiration="2026-06-19",
        ),
        confirmation={
            "order_id": "ORD-LEFT-1",
            "status": "Filled",
            "filled_price": 5.25,
            "filled_quantity": 1,
            "total_cost": 525.0,
            "notes": "Paper fill.",
        },
        pnl_estimate=12.5,
        reasoning="Filled.",
    )

    with patch("portfolio.trading.ui.trading_ui.ExecutionAgent") as agent_cls:
        agent = agent_cls.return_value
        agent.execute.return_value = result
        agent.last_mcp_calls = [
            {"tool": "place_option_order", "status": "success", "detail": "filled"},
            {"tool": "get_account_status", "status": "success", "detail": "synced"},
        ]
        flow, trace, status, log_html, confirmation = _run_execution_phase(state_json, True)

    assert "grid-area:execution" in flow
    assert "Trade Executed" in status
    assert "Order submitted via MCP paper trading" in log_html
    assert "Order Confirmation" in confirmation
    assert "ORD-LEFT-1" in confirmation
    assert "MCP Paper-Trading Server" in trace
    assert "place_option_order" in trace
    assert "Order Confirmation" not in trace


def test_execution_no_trade_and_invalid_state_clear_confirmation_slot() -> None:
    no_trade_state = json.dumps({
        "symbol": "AAPL",
        "strategy_value": "No Trade",
        "deterministic": True,
        "flow_traces": {},
        "run_record": {"path_summary": "Why this path: no trade."},
    })

    assert _run_execution_phase(no_trade_state, True)[-1] == ""
    assert _run_execution_phase("not-json", True)[-1] == ""


def test_rejection_clearer_returns_empty_confirmation_html() -> None:
    assert _clear_order_confirmation() == ""
