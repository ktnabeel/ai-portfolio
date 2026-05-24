"""Data models for the claim processing system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ClaimType(str, Enum):
    AUTO = "Auto"
    PROPERTY = "Property"
    HEALTH = "Health"
    LIFE = "Life"
    LIABILITY = "Liability"
    OTHER = "Other"


class ClaimSeverity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class FraudRisk(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class RoutingDecision(str, Enum):
    APPROVE = "Approve"
    REVIEW = "Review"
    DENY = "Deny"
    ESCALATE = "Escalate"


@dataclass(frozen=True)
class ClaimData:
    """Structured claim extracted from raw text."""
    claim_id: str = ""
    claimant: str = ""
    claim_type: ClaimType = ClaimType.OTHER
    amount: Optional[float] = None
    incident_date: str = ""
    description: str = ""
    policy_number: str = ""


@dataclass(frozen=True)
class ClaimAnalysis:
    """Complete analysis result for a single claim."""
    claim: ClaimData
    fraud_risk: FraudRisk = FraudRisk.LOW
    fraud_confidence: float = 0.0
    fraud_reasoning: str = ""
    severity: ClaimSeverity = ClaimSeverity.LOW
    severity_reasoning: str = ""
    routing: RoutingDecision = RoutingDecision.REVIEW
    routing_reasoning: str = ""
    extracted_details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
