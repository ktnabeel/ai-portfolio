from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    title: str
    outcome: str
    tech_stack: str
    status: str
    tags: tuple[str, ...]
    github_url: str = ""
    demo_url: str = ""
    image_url: str = ""

