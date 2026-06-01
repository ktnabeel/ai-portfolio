"""Tests for the CNN Fear & Greed scraper parser."""

from __future__ import annotations

from portfolio.trading.models import FearGreedZone
from portfolio.trading.scrapers.cnn_fear_greed import _parse_graph_payload


def test_parse_graph_payload_from_playwright_response() -> None:
    payload = {
        "fear_and_greed": {
            "score": 60.1714285714286,
            "rating": "greed",
            "timestamp": "2026-05-29T23:59:54+00:00",
            "previous_close": 60.2285714285714,
            "previous_1_week": 58.9714285714286,
            "previous_1_month": 66.22857142857143,
            "previous_1_year": 64.45714285714287,
        }
    }

    result = _parse_graph_payload(payload, "playwright-browser")

    assert result is not None
    assert result.value == 60
    assert result.zone == FearGreedZone.GREED
    assert result.previous_close == 60
    assert result.one_week_ago == 59
    assert result.one_month_ago == 66
    assert result.one_year_ago == 64
    assert result.source_method == "playwright-browser"


def test_parse_graph_payload_rejects_missing_current_score() -> None:
    assert _parse_graph_payload({"fear_and_greed": {"rating": "greed"}}, "playwright-browser") is None
