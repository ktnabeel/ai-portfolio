"""Smoke tests for the lean trading deployment entrypoint."""

from __future__ import annotations

import sys
import types

import gradio as gr
from fastapi.testclient import TestClient


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
    assert "Multi-agent AI systems" in home.text
    assert "AI Engineer" in home.text
    assert "Account Snapshot" in home.text


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
