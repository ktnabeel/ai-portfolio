"""Agentic Insurance Underwriting Assistant — risk review, policy context, and recommendation support."""

from .models import (
    ApplicationData,
    UnderwritingResult,
    UnderwritingDecision,
    RiskLevel,
    RiskFactor,
    PolicyContext,
)
from .agent import UnderwritingAgent

__all__ = [
    "ApplicationData",
    "UnderwritingResult",
    "UnderwritingDecision",
    "RiskLevel",
    "RiskFactor",
    "PolicyContext",
    "UnderwritingAgent",
]


def _get_render():
    """Return render helpers, loading gradio only when needed."""
    from .render import render_underwriting_tab, UNDERWRITING_CSS  # noqa: F811
    return render_underwriting_tab, UNDERWRITING_CSS
