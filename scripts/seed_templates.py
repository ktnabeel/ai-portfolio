from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from portfolio.db import seed_projects
from portfolio.project_templates import PROJECT_TEMPLATES


DB_PATH = BASE_DIR / "portfolio.db"


def main() -> None:
    added = seed_projects(DB_PATH, PROJECT_TEMPLATES)
    print(f"Seeded {added} project template(s).")


if __name__ == "__main__":
    main()
