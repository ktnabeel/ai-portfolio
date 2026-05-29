"""Unit tests verifying all tabs in app.py render without errors.

Covers: Portfolio, Portfolio Manager, Insurance Underwriting, Claim Processing,
Movie Recommendations, Sentiment Analyzer, Financial Agent, and Trading Desk.
"""

from pathlib import Path

import gradio as gr

from portfolio.db import get_projects, init_db
from portfolio.financial import render_financial_tab
from portfolio.claim_processing.render import render_claim_tab
from portfolio.movie_recommender import render_movie_tab
from portfolio.sentiment import render_sentiment_tab
from portfolio.render import render_page
from portfolio.trading_agents_manager import render_trading_agents_tab
from portfolio.trading.ui import render_trading_tab


def test_portfolio_tab_renders_html(tmp_path: Path) -> None:
    """Portfolio tab renders valid HTML without errors."""
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    html = render_page(get_projects(db_path))
    assert isinstance(html, str)
    assert len(html) > 0
    assert "AI Engineering Portfolio" in html


def test_financial_tab_renders() -> None:
    """Financial Agent tab renders without errors."""
    with gr.Blocks():
        tab = render_financial_tab()
        assert isinstance(tab, gr.Blocks)


def test_claim_tab_renders() -> None:
    """Claim Processing tab renders without errors."""
    with gr.Blocks():
        tab = render_claim_tab()
        assert isinstance(tab, gr.Blocks)


def test_movie_tab_renders() -> None:
    """Movie Recommendations tab renders without errors."""
    with gr.Blocks():
        tab = render_movie_tab()
        assert isinstance(tab, gr.Blocks)


def test_sentiment_tab_renders() -> None:
    """Sentiment Analyzer tab renders without errors."""
    with gr.Blocks():
        tab = render_sentiment_tab()
        assert isinstance(tab, gr.Blocks)


def test_trading_tab_renders() -> None:
    """Trading tab renders without errors inside a Gradio Blocks context."""
    with gr.Blocks():
        result = render_trading_tab()
        assert result is None


def test_trading_css_exported() -> None:
    """TRADING_CSS is exported and contains expected rules."""
    from portfolio.trading.ui import TRADING_CSS

    assert isinstance(TRADING_CSS, str)
    assert len(TRADING_CSS) > 0
    assert ".trading-card" in TRADING_CSS
    assert "#trading-log" in TRADING_CSS
    assert "#trading-desk-shell" in TRADING_CSS
    assert ".trading-window" in TRADING_CSS
    assert ".trading-action-panel" in TRADING_CSS
    assert "#trading-account-summary" in TRADING_CSS
    assert "display: none" in TRADING_CSS
    assert "#approval-panel {\n    display: none;" not in TRADING_CSS


def test_trading_approval_visibility_helper() -> None:
    """Execute Trade panel is visible only for tradeable recommendations."""
    from portfolio.trading.ui.trading_ui import _approval_panel_update

    assert _approval_panel_update("{}")["visible"] is False
    assert _approval_panel_update('{"strategy_value":"No Trade"}')["visible"] is False
    assert _approval_panel_update('{"strategy_value":"Long Call"}')["visible"] is True
    assert _approval_panel_update('{"strategy_value":"Long Put"}')["visible"] is True
    assert _approval_panel_update('{"strategy_value":"Long Strangle"}')["visible"] is True


def test_all_tab_css_exports_are_strings() -> None:
    """Every tab's CSS export is a non-empty string."""
    from portfolio.financial import DARK_CSS
    from portfolio.claim_processing.render import CLAIM_DARK_CSS
    from portfolio.movie_recommender import MOVIE_CSS
    from portfolio.sentiment import SENTIMENT_CSS
    from portfolio.trading.ui import TRADING_CSS

    for name, css in [
        ("DARK_CSS", DARK_CSS),
        ("CLAIM_DARK_CSS", CLAIM_DARK_CSS),
        ("MOVIE_CSS", MOVIE_CSS),
        ("SENTIMENT_CSS", SENTIMENT_CSS),
        ("TRADING_CSS", TRADING_CSS),
    ]:
        assert isinstance(css, str), f"{name} is not a string"
        assert len(css) > 0, f"{name} is empty"


def test_underwriting_tab_renders() -> None:
    """Insurance Underwriting tab renders without errors."""
    with gr.Blocks():
        from portfolio.underwriting.render import render_underwriting_tab

        tab = render_underwriting_tab()
        assert isinstance(tab, gr.Blocks)


def test_underwriting_css_exported() -> None:
    """UNDERWRITING_CSS is exported and contains expected rules."""
    from portfolio.underwriting.render import UNDERWRITING_CSS

    assert isinstance(UNDERWRITING_CSS, str)
    assert len(UNDERWRITING_CSS) > 0
    assert ".uw-metric-card" in UNDERWRITING_CSS
    assert "#underwriting-tab" in UNDERWRITING_CSS


def test_all_render_functions_are_callable() -> None:
    """Every tab render function is importable and callable."""
    from portfolio.underwriting.render import render_underwriting_tab

    tabs = [
        ("Portfolio", render_page),
        ("Financial Agent", render_financial_tab),
        ("Claim Processing", render_claim_tab),
        ("Movie Recommendations", render_movie_tab),
        ("Sentiment Analyzer", render_sentiment_tab),
        ("Insurance Underwriting", render_underwriting_tab),
        ("Trading Desk", render_trading_tab),
        ("Portfolio Manager", render_trading_agents_tab),
    ]
    assert len(tabs) == 8, "Expected exactly 8 tabs"
    for name, fn in tabs:
        assert callable(fn), f"{name} render function is not callable"
