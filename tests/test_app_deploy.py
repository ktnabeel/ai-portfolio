"""Smoke tests for the lean trading deployment entrypoint."""

from __future__ import annotations

import sys
import types

import gradio as gr
from fastapi.testclient import TestClient
import market_story
from market_story import SentimentDriver, SentimentSnapshot, SecurityDecision, TechnicalSnapshot


def _fake_sentiment_snapshot() -> SentimentSnapshot:
    return SentimentSnapshot(
        value=67,
        zone="Greed",
        description="CNN Fear & Greed sample reading for tests.",
        previous_close=64,
        one_week_ago=60,
        one_month_ago=58,
        one_year_ago=45,
        drivers=[
            SentimentDriver(
                title="Market momentum",
                summary="S&P 500 vs its 125-day average",
                detail="Price above the rolling average signals strength.",
                accent="blue",
            )
        ],
    )


def _fake_technical_snapshot(symbol: str) -> TechnicalSnapshot:
    return TechnicalSnapshot(
        symbol=symbol,
        current_price=200.0,
        ema_8=195.0,
        ema_21=188.0,
        high_20=198.0,
        low_20=176.0,
        average_volume_20=1_000_000.0,
        volume=1_250_000.0,
        bullish_stack=True,
        bearish_stack=False,
        breakout_up=True,
        breakdown=False,
        volume_surge=True,
        signal="Bullish breakout",
        summary="Price is above EMA 8 and EMA 21 and also cleared the recent range high.",
        data_points=60,
    )


def _fake_security_decision(
    symbol: str,
    sentiment: SentimentSnapshot | None = None,
    technical: TechnicalSnapshot | None = None,
) -> SecurityDecision:
    sentiment = sentiment or _fake_sentiment_snapshot()
    technical = technical or _fake_technical_snapshot(symbol)
    reasons = [
        "Price is above EMA 8 and EMA 21 at $200.00.",
        "Price broke above the 20-day high, which confirms upside momentum.",
        "Breakout is backed by heavier-than-average volume.",
        f"CNN Fear & Greed is {sentiment.value}/100 ({sentiment.zone}), which can support a contrarian long if price confirms.",
    ]
    return SecurityDecision(
        symbol=symbol.upper().strip() or "AAPL",
        side="BUY",
        confidence=0.88,
        thesis="Hybrid signal leans long",
        rationale=" ".join(reasons),
        reasons=reasons,
        sentiment=sentiment,
        technical=technical,
    )


class _MockFastInfo:
    last_price = 185.50


class _MockTicker:
    fast_info = _MockFastInfo()
    info = {"regularMarketPrice": 185.50}

    def __init__(self, symbol):
        self.symbol = symbol


_mock_yfinance = types.ModuleType("yfinance")
_mock_yfinance.Ticker = _MockTicker
sys.modules["yfinance"] = _mock_yfinance

market_story.fetch_sentiment_snapshot = _fake_sentiment_snapshot
market_story.fetch_technical_snapshot = _fake_technical_snapshot
market_story.build_security_decision = _fake_security_decision

import app_deploy


def test_gradio_demo_is_built() -> None:
    assert isinstance(app_deploy.demo, gr.Blocks)


def test_fastapi_health_and_home_page() -> None:
    client = TestClient(app_deploy.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    home = client.get("/")
    assert home.status_code == 200
    assert "Agent decisions first. Execution second." in home.text
    assert "Agent Pipeline Flow" in home.text
    assert "AI Engineer" in home.text
    assert "CNN Fear &amp; Greed" in home.text
    assert "Security rationale" in home.text
    assert "Workflow" in home.text
    assert "System Snapshot" in home.text


def test_place_close_and_reset_flow() -> None:
    client = TestClient(app_deploy.app)

    place = client.post(
        "/api/place-order",
        data={
            "symbol": "AAPL",
            "strategy": "Call",
            "option_type": "call",
            "strike": "150",
            "expiration": "",
            "quantity": "1",
            "limit_price": "",
        },
    )
    assert place.status_code == 200

    account = client.get("/api/account")
    assert account.status_code == 200
    account_json = account.json()
    assert account_json["position_count"] >= 1
    assert account_json["order_count"] >= 1

    position_id = account_json["positions"][0]["position_id"]
    close = client.post("/api/close", data={"position_id": position_id, "exit_price": ""})
    assert close.status_code == 200

    reset = client.post("/api/reset")
    assert reset.status_code == 200

    after_reset = client.get("/api/account")
    assert after_reset.json()["position_count"] == 0
