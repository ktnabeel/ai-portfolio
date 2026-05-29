from pathlib import Path
import sqlite3

from .models import Project


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    outcome TEXT NOT NULL,
    tech_stack TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'In progress',
    tags TEXT NOT NULL DEFAULT '',
    github_url TEXT NOT NULL DEFAULT '',
    demo_url TEXT NOT NULL DEFAULT '',
    image_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(SCHEMA)


def get_projects(db_path: str | Path) -> list[Project]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT title, outcome, tech_stack, status, tags, github_url, demo_url, image_url
            FROM projects
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    return [
        Project(
            title=row[0],
            outcome=row[1],
            tech_stack=row[2],
            status=row[3],
            tags=tuple(tag.strip() for tag in row[4].split(",") if tag.strip()),
            github_url=row[5],
            demo_url=row[6],
            image_url=row[7],
        )
        for row in rows
    ]


def add_project(db_path: str | Path, project: Project) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO projects (
                title, outcome, tech_stack, status, tags, github_url, demo_url, image_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.title,
                project.outcome,
                project.tech_stack,
                project.status,
                ", ".join(project.tags),
                project.github_url,
                project.demo_url,
                project.image_url,
            ),
        )


def seed_projects(db_path: str | Path, projects: list[Project]) -> tuple[int, int]:
    """Seed the projects table, updating existing entries, adding new ones,
    and removing stale entries no longer in the template list.

    Returns a tuple of (added_count, deleted_count).
    """
    existing = {project.title: project for project in get_projects(db_path)}
    added = 0
    template_titles = {project.title for project in projects}

    for project in projects:
        if project.title in existing:
            existing_project = existing[project.title]
            # Update if any field changed
            if (
                existing_project.outcome != project.outcome
                or existing_project.tech_stack != project.tech_stack
                or existing_project.status != project.status
                or existing_project.tags != project.tags
                or existing_project.github_url != project.github_url
                or existing_project.demo_url != project.demo_url
            ):
                _update_project(db_path, project)
            continue
        add_project(db_path, project)
        added += 1

    # Delete stale entries that are no longer in the template list.
    stale_titles = set(existing.keys()) - template_titles
    deleted = _delete_projects_by_titles(db_path, stale_titles)

    return added, deleted


def _update_project(db_path: str | Path, project: Project) -> None:
    """Update an existing project by title."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE projects
            SET outcome = ?,
                tech_stack = ?,
                status = ?,
                tags = ?,
                github_url = ?,
                demo_url = ?,
                image_url = ?
            WHERE title = ?
            """,
            (
                project.outcome,
                project.tech_stack,
                project.status,
                ", ".join(project.tags),
                project.github_url,
                project.demo_url,
                project.image_url,
                project.title,
            ),
        )


def _delete_projects_by_titles(db_path: str | Path, titles: set[str]) -> int:
    """Delete projects whose titles are in the given set.

    Returns the number of rows deleted.
    """
    if not titles:
        return 0
    init_db(db_path)
    placeholders = ", ".join("?" for _ in titles)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            f"DELETE FROM projects WHERE title IN ({placeholders})",
            tuple(titles),
        )
        return cursor.rowcount
