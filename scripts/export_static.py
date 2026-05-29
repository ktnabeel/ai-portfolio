from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from portfolio.config import load_config
from portfolio.db import get_projects, init_db, seed_projects
from portfolio.project_templates import get_project_templates
from portfolio.render import render_page

DB_PATH = BASE_DIR / "portfolio.db"
DIST_DIR = BASE_DIR / "dist"


def main() -> None:
    config = load_config()
    init_db(DB_PATH)
    seed_projects(DB_PATH, get_project_templates(config))
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "index.html").write_text(
        render_page(get_projects(DB_PATH), mode="static", config=config),
        encoding="utf-8",
    )
    print(f"Exported static site to {DIST_DIR}")


if __name__ == "__main__":
    main()
