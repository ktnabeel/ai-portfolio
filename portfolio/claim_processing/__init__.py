"""AI-assisted claim processing — extraction, fraud detection, and routing decisions."""

from .models import (
    ClaimData,
    ClaimAnalysis,
    ClaimType,
    ClaimSeverity,
    FraudRisk,
    RoutingDecision,
)
from .processor import ClaimProcessor

# render_claim_tab requires gradio — lazy import to avoid breakage in non-Gradio environments.
__all__ = [
    "ClaimData",
    "ClaimAnalysis",
    "ClaimType",
    "ClaimSeverity",
    "FraudRisk",
    "RoutingDecision",
    "ClaimProcessor",
]


def _get_render():
    """Return render helpers, loading gradio only when needed."""
    from .render import render_claim_tab, CLAIM_DARK_CSS
    return render_claim_tab, CLAIM_DARK_CSS
