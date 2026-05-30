"""Smoke tests for the self-contained Vercel workflow app."""

from __future__ import annotations

import html
import json
import re

from fastapi.testclient import TestClient

from index import app


def _extract_payload(page: str) -> str:
    match = re.search(r'name="payload" value="([^"]+)"', page)
    assert match is not None
    return html.unescape(match.group(1))


def test_homepage_renders_workflow() -> None:
    client = TestClient(app)
    home = client.get("/")
    assert home.status_code == 200
    assert "Workflow Lab" in home.text
    assert "Agent decisions first. Execution second." in home.text
    assert "Agent Pipeline Flow" in home.text
    assert "Agent Deep Dive" in home.text
    assert "Human approval" in home.text


def test_analysis_approval_and_execution_flow() -> None:
    client = TestClient(app)

    analysis = client.post("/analyze", data={"symbol": "AAPL"})
    assert analysis.status_code == 200
    assert "Decision Agent" in analysis.text
    assert "Approve and continue" in analysis.text

    payload = _extract_payload(analysis.text)
    state = json.loads(payload)
    assert state["symbol"] == "AAPL"
    assert state["side"] in {"BUY", "SELL"}

    approval = client.post(
        "/approve",
        data={
            "payload": payload,
            "approval": "approve",
            "approval_note": "Looks good.",
        },
    )
    assert approval.status_code == 200
    assert 'action="/execute"' in approval.text
    assert "Execute trade" in approval.text
    assert "Approval captured" in approval.text

    executed = client.post(
        "/execute",
        data={
            "payload": payload,
            "approval_note": "Looks good.",
        },
    )
    assert executed.status_code == 200
    assert "Trade executed" in executed.text
    assert "Execution Agent" in executed.text

    account = client.get("/api/account")
    assert account.status_code == 200
    data = account.json()
    assert data["position_count"] >= 1
    assert data["order_count"] >= 1
