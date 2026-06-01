"""Tests for the trading flow diagram hover trace renderer."""

from __future__ import annotations

from portfolio.trading.ui.trading_ui import _render_flow_diagram


def test_flow_diagram_includes_path_and_hover_io() -> None:
    html = _render_flow_diagram(
        security_ok=True,
        sentiment_ok=True,
        regime_ok=True,
        chain_ok=True,
        decision_ok=True,
        strategy_name="Long Call",
        pending_approval=True,
        agent_traces={
            "decision": {
                "input": "Security + Risk/Sentiment + Regime + Options Chain",
                "output": "Strategy: Long Call",
            }
        },
    )

    assert "Path taken: Security → Risk/Sentiment → Regime → Options → Decision → Human Review" in html
    assert "flow-tooltip-section" in html
    assert "<span>Input</span>" in html
    assert "<span>Output</span>" in html
    assert "Security + Risk/Sentiment + Regime + Options Chain" in html
    assert "Strategy: Long Call" in html
    assert html.count("<span>Input</span>") == 7
    assert html.count("<span>Output</span>") == 7


def test_flow_diagram_contains_execution_tile_and_containment_css() -> None:
    html = _render_flow_diagram(
        security_ok=True,
        sentiment_ok=True,
        regime_ok=True,
        chain_ok=True,
        decision_ok=True,
        execution_ok=True,
        strategy_name="Long Call",
    )
    compact = "".join(html.split())
    flow_start = html.index('class="agent-flow-map"')
    execution_index = html.index("Execution<br>Agent")

    assert execution_index > flow_start
    assert "grid-area:execution" in compact
    assert "max-width:100%" in compact
    assert "min-width:0" in compact
    assert "max-height:min(360px,70vh)" in compact
    assert "overflow-y:auto" in compact
    assert "overscroll-behavior:contain" in compact
    assert "flow-tooltip-below" in html
    assert "flow-tooltip-above" in html
    assert "@media(max-width:1200px)" in compact
    assert compact.count("flow-tooltip-section") >= 14


def test_regime_detection_tooltip_opens_below_tile() -> None:
    html = _render_flow_diagram(
        security_ok=True,
        sentiment_ok=True,
        regime_ok=True,
        agent_traces={
            "regime": {
                "input": "Long regime input " * 40,
                "output": "Long regime output " * 80,
            }
        },
    )
    regime_start = html.index("Regime<br>Detection")
    options_start = html.index("Options<br>Chain")
    regime_node = html[regime_start:options_start]

    assert "flow-tooltip flow-tooltip-below" in regime_node
