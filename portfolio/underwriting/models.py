"""Data models for the agentic insurance underwriting system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class UnderwritingDecision(str, Enum):
    APPROVE = "Approve"
    DECLINE = "Decline"
    REFER = "Refer"
    REQUEST_INFO = "Request Info"


@dataclass(frozen=True)
class RiskFactor:
    """A single risk factor identified during underwriting review."""
    category: str          # e.g. "Health", "Occupation", "Financial", "Lifestyle"
    name: str              # e.g. "Pre-existing condition", "Hazardous occupation"
    severity: RiskLevel
    description: str
    mitigating: str = ""   # Possible mitigation or offsetting factor


@dataclass(frozen=True)
class PolicyContext:
    """Policy details used for underwriting evaluation."""
    product_type: str = ""            # e.g. "Term Life", "Whole Life", "Disability"
    coverage_amount: Optional[float] = None
    policy_term_years: Optional[int] = None
    premium_band: str = ""            # e.g. "Standard", "Preferred", "Substandard"
    exclusions: list[str] = field(default_factory=list)
    riders: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ApplicationData:
    """Structured underwriting application extracted from free text."""
    application_id: str = ""
    applicant_name: str = ""
    age: Optional[int] = None
    occupation: str = ""
    annual_income: Optional[float] = None
    product_type: str = ""            # requested insurance type
    coverage_requested: Optional[float] = None
    medical_history: str = ""         # free-text summary
    lifestyle_notes: str = ""         # smoking, alcohol, hobbies, travel
    financial_notes: str = ""         # debts, assets, dependents
    raw_text: str = ""                # original application text


@dataclass(frozen=True)
class UnderwritingResult:
    """Complete underwriting assessment result."""
    application: ApplicationData
    decision: UnderwritingDecision = UnderwritingDecision.REFER
    overall_risk: RiskLevel = RiskLevel.MODERATE
    risk_score: float = 0.0           # 0-100, higher = riskier
    risk_factors: list[RiskFactor] = field(default_factory=list)
    policy_context: PolicyContext = field(default_factory=PolicyContext)
    recommendation: str = ""          # agentic recommendation narrative
    reasoning: str = ""               # structured chain-of-thought reasoning
    extracted_details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
