"""Claim Processor — extracts, analyzes, and routes insurance claims."""

import re
from typing import Optional

from .models import (
    ClaimData,
    ClaimAnalysis,
    ClaimType,
    ClaimSeverity,
    FraudRisk,
    RoutingDecision,
)

# ── Keyword / pattern dictionaries ──────────────────────────────────────────

CLAIM_TYPE_KEYWORDS = {
    ClaimType.AUTO: [
        "car", "auto", "vehicle", "collision", "accident", "driver", "windshield",
        "bumper", "fender", "rear-ended", "t-boned", "totaled", "garage",
    ],
    ClaimType.PROPERTY: [
        "house", "home", "property", "roof", "flood", "fire", "theft", "burglary",
        "vandalism", "hail", "wind", "water damage", "pipe", "mold", "basement",
    ],
    ClaimType.HEALTH: [
        "hospital", "surgery", "medical", "doctor", "prescription", "treatment",
        "diagnosis", "mri", "x-ray", "ambulance", "emergency room", "clinic",
        "physical therapy", "dental", "vision",
    ],
    ClaimType.LIFE: [
        "deceased", "beneficiary", "death", "funeral", "estate", "will",
        "life insurance", "payout",
    ],
    ClaimType.LIABILITY: [
        "lawsuit", "liability", "negligence", "injury", "slip and fall",
        "damages", "settlement", "attorney", "legal",
    ],
}

FRAUD_RED_FLAGS = [
    (r"\bjust happened\b", "Claim reported immediately after alleged incident."),
    (r"\burgen(?:t|cy|tly)\b", "Urgency cues — rushing claim processing."),
    (r"\bcash\b", "Request for cash settlement."),
    (r"\bno witness(?:es)?\b", "No witnesses to the incident."),
    (r"\b(?:lost|destroyed) (?:receipt|document)", "Key documentation reported missing."),
    (r"\b(?:very|extremely|incredibly|unbelievably)\b", "Exaggerated language detected."),
    (r"\b(?:preexisting|pre-existing|prior)\b", "Reference to pre-existing conditions."),
    (r"\b(?:soon after|right after|just after) (?:purchas|bought|acquired)", "Incident timing suspicious — shortly after acquisition."),
    (r"\b(?:cannot|can't) (?:provide|remember|recall)\b", "Claimant unable to provide key details."),
    (r"\b(?:third time|repeated|again|another)\b.*\bclaim\b", "Pattern of repeated claims detected."),
]


class ClaimProcessor:
    """End-to-end claim processing: extraction, fraud detection, severity, routing."""

    # ── Extraction ──────────────────────────────────────────────────────

    def extract_details(self, claim_text: str) -> ClaimData:
        """Extract structured data from free-text claim description."""
        text = claim_text.strip()
        claim_type = self._classify_type(text)
        amount = self._extract_amount(text)
        claimant = self._extract_claimant(text)
        incident_date = self._extract_date(text)
        policy_number = self._extract_policy_number(text)
        claim_id = self._extract_claim_id(text)

        return ClaimData(
            claim_id=claim_id,
            claimant=claimant,
            claim_type=claim_type,
            amount=amount,
            incident_date=incident_date,
            description=text,
            policy_number=policy_number,
        )

    def _classify_type(self, text: str) -> ClaimType:
        lower = text.lower()
        scores = {}
        for claim_type, keywords in CLAIM_TYPE_KEYWORDS.items():
            scores[claim_type] = sum(1 for kw in keywords if kw in lower)
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        return ClaimType.OTHER

    @staticmethod
    def _extract_amount(text: str) -> Optional[float]:
        patterns = [
            r"\$[\s]?([\d,]+(?:\.\d{2})?)",
            r"([\d,]+(?:\.\d{2})?)\s*(?:dollars|USD)",
            r"(?:claimed|seeking|amount|value)[\s:]*\$?[\s]?([\d,]+(?:\.\d{2})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = match.group(1).replace(",", "")
                try:
                    return float(raw)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_claimant(text: str) -> str:
        patterns = [
            r"(?:claimant|customer|insured|policyholder|patient)[\s:]*([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})",
            r"(?:I am|my name is|this is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})",
            r"(?:from|by|submitted by)[\s:]*([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_date(text: str) -> str:
        patterns = [
            r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _extract_policy_number(text: str) -> str:
        match = re.search(r"(?:policy|pol)[\s#:]*([A-Z0-9]{4,20})", text, re.IGNORECASE)
        return match.group(1) if match else ""

    @staticmethod
    def _extract_claim_id(text: str) -> str:
        match = re.search(r"(?:claim|case)[\s#:]*([A-Z0-9]{4,20})", text, re.IGNORECASE)
        return match.group(1) if match else ""

    # ── Fraud Detection ──────────────────────────────────────────────────

    def assess_fraud(self, claim: ClaimData) -> tuple[FraudRisk, float, str]:
        """Assess fraud risk from claim data and description."""
        text = claim.description.lower()
        flags_found = []
        for pattern, explanation in FRAUD_RED_FLAGS:
            if re.search(pattern, text, re.IGNORECASE):
                flags_found.append(explanation)

        # Additional heuristics
        if claim.amount and claim.amount > 500_000:
            flags_found.append(f"Very high claim amount (${claim.amount:,.0f}) triggers additional scrutiny.")
        if not claim.claimant:
            flags_found.append("Claimant information missing.")
        if not claim.policy_number:
            flags_found.append("Policy number not provided.")

        flag_count = len(flags_found)
        if flag_count >= 3:
            risk = FraudRisk.HIGH
            confidence = min(0.65 + flag_count * 0.08, 0.95)
        elif flag_count >= 1:
            risk = FraudRisk.MEDIUM
            confidence = 0.35 + flag_count * 0.12
        else:
            risk = FraudRisk.LOW
            confidence = 0.80

        reasoning = "; ".join(flags_found) if flags_found else "No fraud indicators detected."
        return risk, confidence, reasoning

    # ── Severity ─────────────────────────────────────────────────────────

    def determine_severity(self, claim: ClaimData) -> tuple[ClaimSeverity, str]:
        """Classify claim severity based on amount and type."""
        amount = claim.amount

        if amount is None:
            if claim.claim_type in (ClaimType.LIFE, ClaimType.LIABILITY):
                return ClaimSeverity.HIGH, "No amount specified but claim type (Life/Liability) suggests significant exposure."
            return ClaimSeverity.MEDIUM, "Amount not specified — treating as medium severity."

        if amount >= 250_000:
            return ClaimSeverity.CRITICAL, f"Amount ${amount:,.0f} exceeds critical threshold ($250k)."
        if amount >= 50_000:
            return ClaimSeverity.HIGH, f"Amount ${amount:,.0f} is in the high severity range ($50k–$250k)."
        if amount >= 5_000:
            return ClaimSeverity.MEDIUM, f"Amount ${amount:,.0f} is in the medium severity range ($5k–$50k)."
        return ClaimSeverity.LOW, f"Amount ${amount:,.0f} is below $5k threshold."

    # ── Routing ──────────────────────────────────────────────────────────

    def route_decision(
        self,
        claim: ClaimData,
        fraud_risk: FraudRisk,
        severity: ClaimSeverity,
    ) -> tuple[RoutingDecision, str]:
        """Determine routing decision based on fraud risk and severity."""

        if fraud_risk == FraudRisk.HIGH:
            return RoutingDecision.DENY, "High fraud risk — automatic denial recommended."
        if severity == ClaimSeverity.CRITICAL:
            return RoutingDecision.ESCALATE, "Critical severity — escalate to senior adjuster."
        if fraud_risk == FraudRisk.MEDIUM and severity in (ClaimSeverity.HIGH, ClaimSeverity.CRITICAL):
            return RoutingDecision.REVIEW, "Medium fraud risk with high severity — manual review required."
        if fraud_risk == FraudRisk.MEDIUM:
            return RoutingDecision.REVIEW, "Medium fraud risk — recommend manual review."
        if severity in (ClaimSeverity.HIGH, ClaimSeverity.CRITICAL):
            return RoutingDecision.REVIEW, "High severity claim — recommend detailed review."
        if severity == ClaimSeverity.LOW and fraud_risk == FraudRisk.LOW:
            return RoutingDecision.APPROVE, "Low severity, low fraud risk — clear for fast-track approval."

        return RoutingDecision.REVIEW, "Standard routing — manual review recommended."

    # ── Full Pipeline ────────────────────────────────────────────────────

    def process_claim(self, claim_text: str) -> ClaimAnalysis:
        """Run the full claim processing pipeline."""
        claim = self.extract_details(claim_text)
        fraud_risk, fraud_conf, fraud_reasoning = self.assess_fraud(claim)
        severity, severity_reasoning = self.determine_severity(claim)
        routing, routing_reasoning = self.route_decision(claim, fraud_risk, severity)

        extracted = {}
        if claim.claimant:
            extracted["Claimant"] = claim.claimant
        if claim.policy_number:
            extracted["Policy #"] = claim.policy_number
        if claim.claim_id:
            extracted["Claim ID"] = claim.claim_id
        if claim.incident_date:
            extracted["Incident Date"] = claim.incident_date
        extracted["Type"] = claim.claim_type.value
        if claim.amount is not None:
            extracted["Amount"] = f"${claim.amount:,.2f}"

        return ClaimAnalysis(
            claim=claim,
            fraud_risk=fraud_risk,
            fraud_confidence=fraud_conf,
            fraud_reasoning=fraud_reasoning,
            severity=severity,
            severity_reasoning=severity_reasoning,
            routing=routing,
            routing_reasoning=routing_reasoning,
            extracted_details=extracted,
        )
