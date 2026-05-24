from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "portfolio.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 7860,
    },
    "site": {
        "title": "AI Project Portfolio",
        "meta_description": "AI project portfolio for applied machine learning, agents, automation, and product prototypes.",
        "brand": "AI Portfolio",
        "brand_mark": "AI",
        "kicker": "Applied AI Portfolio",
        "headline": "Python AI projects for agents, automation, and analytics.",
        "side_copy": "A public LinkedIn-ready portfolio focused on practical AI systems, workflow automation, and decision support prototypes.",
        "intro_kicker": "Portfolio Workspace",
        "intro_headline": "Selected AI builds presented as concise case studies.",
        "intro_copy": "Each project tile is designed for fast review: what it does, where AI is applied, the Python stack, and the next link a recruiter or collaborator would expect.",
        "project_kicker": "Project Index",
        "project_heading": "AI project tiles",
        "status_label": "Public showcase",
        "linkedin_url": "https://www.linkedin.com/",
    },
    "stats": [
        {"label": "Projects", "value": "6"},
        {"label": "Stack", "value": "Python"},
        {"label": "Deploy", "value": "HF + Vercel"},
    ],
    "capabilities": [
        {"title": "Agents", "description": "Research, routing, planning"},
        {"title": "NLP", "description": "Reviews, claims, sentiment"},
        {"title": "Decision Support", "description": "Finance, underwriting, recommendations"},
    ],
}


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    path = Path(path)
    if not path.exists():
        return config

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")

    _merge(config, raw)
    raw_site = raw.get("site")
    if isinstance(raw_site, dict) and "headline" in raw_site and "intro_headline" not in raw_site:
        config["site"]["intro_headline"] = config["site"]["headline"]
    config["server"]["port"] = int(config["server"]["port"])
    config["server"]["host"] = str(config["server"]["host"])
    return config


def get_config_value(key_path: str, path: str | Path = CONFIG_PATH) -> Any:
    value: Any = load_config(path)
    for part in key_path.split("."):
        value = value[part]
    return value


def _merge(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = value
