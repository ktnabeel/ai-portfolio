"""Vercel entrypoint dispatcher.

The repo can serve either the full portfolio app or the lean trading
deployment from the same Vercel function entrypoint, selected via env var.
"""

from __future__ import annotations

import os


def _trading_mode() -> bool:
    flag = os.getenv("TRADING_DEPLOY_MODE", "").strip().lower()
    if flag in {"0", "false", "no", "portfolio", "full"}:
        return False
    if flag in {"1", "true", "yes", "trading", "lean"}:
        return True
    return "VERCEL" in os.environ


if _trading_mode():
    from app_deploy import app
else:
    from portfolio_api import app
