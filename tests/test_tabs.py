"""Unit tests verifying all tabs in app.py render without errors.

Covers: Portfolio, Portfolio Manager, Insurance Underwriting, Claim Processing,
Movie Recommendations, Sentiment Analyzer, Resume Matcher, Financial Agent,
and Trading Desk.
"""

from pathlib import Path

import gradio as gr

from portfolio.db import get_projects, init_db
from portfolio.financial import render_financial_tab
from portfolio.claim_processing.render import render_claim_tab
from portfolio.movie_recommender import render_movie_tab
from portfolio.sentiment import render_sentiment_tab
from portfolio.resume_matcher import render_resume_matcher_tab
from portfolio.models import Project
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


def test_gradio_project_open_buttons_use_tab_targets() -> None:
    """Project Index Open buttons carry stable tab IDs and expected labels."""
    projects = [
        Project(
            title="Portfolio Manager",
            outcome="Multi-agent portfolio manager.",
            tech_stack="Python, FastAPI, LangGraph",
            status="Built",
            tags=("Agents", "Finance"),
        ),
        Project(
            title="Claim Processing",
            outcome="AI-assisted claims workflow.",
            tech_stack="Python, document AI",
            status="Built",
            tags=("Insurance", "Automation"),
        ),
        Project(
            title="Insurance Underwriting Agent",
            outcome="Agentic underwriting assistant.",
            tech_stack="Python, rule-based NLP",
            status="Built",
            tags=("Insurance", "Risk"),
        ),
    ]

    html = render_page(projects, mode="gradio")

    assert 'data-tab-target="trading_agents"' in html
    assert 'data-tab-label="Portfolio Manager"' in html
    assert 'data-tab-target="claim"' in html
    assert 'data-tab-label="Claim Processing"' in html
    assert 'data-tab-target="underwriting"' in html
    assert 'data-tab-label="Insurance Underwriting"' in html


def test_gradio_tab_switch_script_is_included(tmp_path: Path) -> None:
    """Gradio mode includes one delegated tab-switch handler."""
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    html = render_page(get_projects(db_path), mode="gradio")

    assert "window.__portfolioTabSwitchBound" in html
    assert "document.addEventListener('click'" in html
    assert "closest('[data-tab-target]')" in html
    assert "scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })" in html


def test_theme_toggle_is_in_right_top_bar_group(tmp_path: Path) -> None:
    """Theme toggle is separated from status/contact and aligned right."""
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    html = render_page(get_projects(db_path), mode="gradio")

    assert '<div class="top-bar-left">' in html
    assert '<div class="top-bar-right">' in html
    right_group = html.split('<div class="top-bar-right">', 1)[1].split("</div>", 1)[0]
    left_group = html.split('<div class="top-bar-left">', 1)[1].split("</div>", 1)[0]
    assert 'class="theme-toggle"' not in right_group
    assert 'class="theme-toggle"' not in left_group
    assert "Toggle Theme" not in right_group
    assert "theme-icon-light" not in right_group
    assert "theme-icon-dark" not in right_group
    assert "Contact" in left_group


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


def test_sentiment_dataset_dropdown_modes() -> None:
    """Sentiment dataset modes use source-specific labels and visibility."""
    from portfolio.sentiment.render import _init_dropdowns

    amazon_category, amazon_subcategory, amazon_product, amazon_compare = _init_dropdowns("Amazon Style")
    yelp_category, yelp_subcategory, yelp_product, yelp_compare = _init_dropdowns("Yelp Style")

    assert amazon_category.label == "2. Product Category"
    assert amazon_category.value == "\u2014 All Categories \u2014"
    assert amazon_subcategory.visible is True
    assert amazon_subcategory.interactive is True
    assert amazon_product.label == "4. Amazon Product"
    assert amazon_compare.visible is False

    assert yelp_category.label == "2. Business Type"
    assert yelp_category.value == "\u2014 All Business Types \u2014"
    assert yelp_subcategory.visible is False
    assert yelp_product.label == "4. Selection A"
    assert yelp_compare.visible is True


def test_sentiment_actions_validate_required_selection() -> None:
    """Sentiment actions show validation instead of running with empty selections."""
    from portfolio.sentiment.render import _analyze_product, _compare_products

    amazon_html = _analyze_product("", "Amazon Style")
    yelp_html = _compare_products("", "", "Yelp Style")

    assert "Select a Amazon product first." in amazon_html
    assert "Choose an item from the dropdown" in amazon_html
    assert "Select two Yelp businesses first." in yelp_html
    assert "Choose Selection A and Selection B" in yelp_html


def test_resume_matcher_tab_renders() -> None:
    """Resume Matcher tab renders without errors."""
    with gr.Blocks():
        tab = render_resume_matcher_tab()
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
    from portfolio.resume_matcher import RESUME_MATCHER_CSS

    for name, css in [
        ("DARK_CSS", DARK_CSS),
        ("CLAIM_DARK_CSS", CLAIM_DARK_CSS),
        ("MOVIE_CSS", MOVIE_CSS),
        ("SENTIMENT_CSS", SENTIMENT_CSS),
        ("RESUME_MATCHER_CSS", RESUME_MATCHER_CSS),
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
        ("Resume Matcher", render_resume_matcher_tab),
        ("Insurance Underwriting", render_underwriting_tab),
        ("Trading Desk", render_trading_tab),
        ("Portfolio Manager", render_trading_agents_tab),
    ]
    assert len(tabs) == 9, "Expected exactly 9 tabs"
    for name, fn in tabs:
        assert callable(fn), f"{name} render function is not callable"
