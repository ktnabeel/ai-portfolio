from pathlib import Path
import sqlite3

from .models import Project


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
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
            INSERT INTO projects (
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


def seed_projects(db_path: str | Path, projects: list[Project]) -> int:
    existing_titles = {project.title for project in get_projects(db_path)}
    added = 0

    for project in projects:
        if project.title in existing_titles:
            continue
        add_project(db_path, project)
        added += 1

    return added
