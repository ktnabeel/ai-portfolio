from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from portfolio.config import load_config
from portfolio.db import seed_projects
from portfolio.project_templates import get_project_templates


DB_PATH = BASE_DIR / "portfolio.db"


def main() -> None:
    config = load_config()
    added, deleted = seed_projects(DB_PATH, get_project_templates(config))
    if added:
        print(f"Seeded {added} new project(s).")
    if deleted:
        print(f"Removed {deleted} stale project(s).")
    if not added and not deleted:
        print("Projects are up to date.")


if __name__ == "__main__":
    main()
