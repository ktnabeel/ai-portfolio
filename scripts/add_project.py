import argparse
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from portfolio.db import add_project
from portfolio.models import Project


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a real AI project tile to the portfolio database.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--tech-stack", required=True)
    parser.add_argument("--status", default="In progress")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--github-url", default="")
    parser.add_argument("--demo-url", default="")
    parser.add_argument("--image-url", default="")
    parser.add_argument("--db", default=str(BASE_DIR / "portfolio.db"))
    args = parser.parse_args()

    project = Project(
        title=args.title,
        outcome=args.outcome,
        tech_stack=args.tech_stack,
        status=args.status,
        tags=tuple(tag.strip() for tag in args.tags.split(",") if tag.strip()),
        github_url=args.github_url,
        demo_url=args.demo_url,
        image_url=args.image_url,
    )
    add_project(args.db, project)
    print(f"Added project: {project.title}")


if __name__ == "__main__":
    main()
