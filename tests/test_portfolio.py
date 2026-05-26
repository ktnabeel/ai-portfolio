from pathlib import Path

from portfolio.db import add_project, get_projects, init_db, seed_projects
from portfolio.config import load_config
from portfolio.models import Project
from portfolio.project_templates import PROJECT_TEMPLATES
from portfolio.render import render_page


def test_empty_portfolio_renders_empty_state(tmp_path: Path) -> None:
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    html = render_page(get_projects(db_path))

    assert "Real project entries are ready to be added." in html
    assert "AI Engineering Portfolio" in html


def test_project_round_trip_renders_tile(tmp_path: Path) -> None:
    db_path = tmp_path / "portfolio.db"
    add_project(
        db_path,
        Project(
            title="Trading Agents Research App",
            outcome="Runs multi-agent stock analysis with OpenAI chat models.",
            tech_stack="Python, OpenAI, LangGraph",
            status="Built",
            tags=("Agents", "Finance", "OpenAI"),
            github_url="https://github.com/example/repo",
            demo_url="https://example.com",
        ),
    )

    projects = get_projects(db_path)
    html = render_page(projects)

    assert len(projects) == 1
    assert "Trading Agents Research App" in html
    assert "Python, OpenAI, LangGraph" in html
    assert "GitHub" in html
    assert "Demo" in html


def test_project_templates_include_seven_titles() -> None:
    titles = [project.title for project in PROJECT_TEMPLATES]

    assert "TradingAgents Manager" in titles
    assert "Trading Agents" in titles
    assert "Claim Processing" in titles
    assert "Insurance Underwriting Agent" in titles
    assert "Product Review Sentiment Analyzer" in titles
    assert "Finance Planning" in titles
    assert "Movie Recommendations" in titles
    assert len(titles) == 7


def test_seed_projects_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "portfolio.db"

    first_count = seed_projects(db_path, PROJECT_TEMPLATES)
    second_count = seed_projects(db_path, PROJECT_TEMPLATES)

    assert first_count == 7
    assert second_count == 0
    assert len(get_projects(db_path)) == 7


def test_static_export_does_not_render_gradio_tab_links() -> None:
    html = render_page(PROJECT_TEMPLATES, mode="static")

    assert "event.preventDefault();" not in html
    assert 'class="financial-nav-link"' not in html
    assert 'href="#">Demo</a>' not in html
    assert 'class="expand-toggle"' in html


def test_gradio_portfolio_renders_in_app_project_links() -> None:
    html = render_page(PROJECT_TEMPLATES, mode="gradio")

    assert "Trading Agents" in html
    assert 'data-tab-target="trading"' in html
    assert 'href="#" onclick=' not in html
    assert html.count(">Demo</a>") == 6


def test_yaml_config_overrides_static_text(tmp_path: Path) -> None:
    config_path = tmp_path / "portfolio.yaml"
    config_path.write_text(
        """
server:
  host: 0.0.0.0
  port: 9000
site:
  title: Custom Portfolio
  headline: Custom AI headline
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    html = render_page([], config=config)

    assert config["server"]["host"] == "0.0.0.0"
    assert config["server"]["port"] == 9000
    assert "Custom Portfolio" in html
    assert "Custom AI headline" in html
