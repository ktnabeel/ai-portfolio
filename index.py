"""Vercel FastAPI entrypoint for the mini deployment."""

from __future__ import annotations

from portfolio.trading.deploy import create_fastapi_app


app = create_fastapi_app()
