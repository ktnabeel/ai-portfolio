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
from .render import render_claim_tab, CLAIM_DARK_CSS

__all__ = [
    "ClaimData",
    "ClaimAnalysis",
    "ClaimType",
    "ClaimSeverity",
    "FraudRisk",
    "RoutingDecision",
    "ClaimProcessor",
    "render_claim_tab",
    "CLAIM_DARK_CSS",
]
