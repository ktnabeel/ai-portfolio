from __future__ import annotations

from typing import Any

from .config import load_config
from .models import Project


def get_project_templates(config: dict[str, Any] | None = None) -> list[Project]:
    """Return project index cards from portfolio.yaml.

    The visible title, description, stack, status, and tags are intentionally
    config-driven so the portfolio index can be maintained without code edits.
    """
    config = config or load_config()
    demo_urls = config.get("project_demo_urls", {})
    projects = config.get("projects", [])
    tab_order = {
        str(tab_id): index
        for index, tab_id in enumerate(config.get("tabs", {}).keys())
    }

    indexed_projects = [
        (index, item)
        for index, item in enumerate(projects)
        if isinstance(item, dict)
    ]
    indexed_projects.sort(
        key=lambda pair: (
            tab_order.get(str(pair[1].get("tab", "")), len(tab_order) + pair[0]),
            pair[0],
        )
    )

    templates: list[Project] = []
    for _, item in indexed_projects:
        title = str(item.get("title", "")).strip()
        if not title:
            continue

        tags = item.get("tags", ())
        if isinstance(tags, str):
            tag_values = tuple(tag.strip() for tag in tags.split(",") if tag.strip())
        else:
            tag_values = tuple(str(tag).strip() for tag in tags if str(tag).strip())

        templates.append(
            Project(
                title=title,
                outcome=str(item.get("description") or item.get("outcome") or "").strip(),
                tech_stack=str(item.get("tech_stack", "")).strip(),
                status=str(item.get("status", "In progress")).strip(),
                tags=tag_values,
                github_url=str(item.get("github_url", "")).strip(),
                demo_url=str(item.get("demo_url") or demo_urls.get(title, "")).strip(),
                image_url=str(item.get("image_url", "")).strip(),
            )
        )

    return templates


def __getattr__(name: str) -> list[Project]:
    """Lazy-load PROJECT_TEMPLATES for backward compatibility (PEP 562)."""
    if name == "PROJECT_TEMPLATES":
        return get_project_templates()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
