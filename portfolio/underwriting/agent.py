"""UnderwritingAgent — agentic assistant for risk review, policy context, and recommendation support."""

import re
from typing import Optional

from .models import (
    ApplicationData,
    UnderwritingResult,
    UnderwritingDecision,
    RiskLevel,
    RiskFactor,
    PolicyContext,
)

# ── Risk factor rule definitions ────────────────────────────────────────────

_HEALTH_RULES: dict[str, tuple[RiskLevel, str]] = {
    r"\b(?:heart\s*(?:disease|attack|condition)|cardiovascular|stroke|bypass)\b": (
        RiskLevel.HIGH,
        "Cardiovascular condition — elevated mortality risk.",
    ),
    r"\b(?:cancer|malignant|tumor|oncology|chemotherapy)\b": (
        RiskLevel.CRITICAL,
        "Cancer diagnosis — significant underwriting concern.",
    ),
    r"\b(?:diabetes\s*type\s*[12]|insulin[- ]dependent)\b": (
        RiskLevel.HIGH,
        "Diabetes with insulin dependence — glycemic control risk.",
    ),
    r"\b(?:diabetes|type\s*2|glucose|A1C)\b": (
        RiskLevel.MODERATE,
        "Diabetes or impaired glucose — requires further evaluation.",
    ),
    r"\b(?:asthma|copd|emphysema|lung|respiratory)\b": (
        RiskLevel.MODERATE,
        "Respiratory condition — pulmonary function risk.",
    ),
    r"\b(?:hypertension|high\s+blood\s+pressure|bp\s*\d{2,3}\s*/\s*\d{2,3})\b": (
        RiskLevel.MODERATE,
        "Hypertension — managed blood pressure concern.",
    ),
    r"\b(?:depression|anxiety|bipolar|schizophrenia|mental\s+health|PTSD)\b": (
        RiskLevel.MODERATE,
        "Mental health condition — requires severity assessment.",
    ),
    r"\b(?:surgery|operation|procedure)\b.*\b(?:last|recent|year|month)\b": (
        RiskLevel.MODERATE,
        "Recent surgical procedure — recovery status unclear.",
    ),
    r"\b(?:pre[- ]existing|chronic|ongoing)\b": (
        RiskLevel.MODERATE,
        "Pre-existing condition noted — requires detailed review.",
    ),
    r"\b(?:smoker|smoking|tobacco|nicotine|cigarette)\b": (
        RiskLevel.MODERATE,
        "Tobacco use — increased mortality risk.",
    ),
}

_OCCUPATION_RULES: dict[str, tuple[RiskLevel, str]] = {
    r"\b(?:pilot|flight|aviation|airline)\b": (
        RiskLevel.HIGH,
        "Aviation occupation — occupational hazard risk.",
    ),
    r"\b(?:firefighter|fire\s*fighter|ems|paramedic)\b": (
        RiskLevel.HIGH,
        "Emergency services — hazardous duty.",
    ),
    r"\b(?:military|army|navy|marine|combat|deployed)\b": (
        RiskLevel.HIGH,
        "Military service — deployment and combat risk.",
    ),
    r"\b(?:construction|roofer|scaffold|steel\s*worker|iron\s*worker)\b": (
        RiskLevel.HIGH,
        "High-risk construction — falls and equipment hazards.",
    ),
    r"\b(?:miner|mining|oil\s*rig|offshore|drilling)\b": (
        RiskLevel.HIGH,
        "Extractive industry — hazardous work environment.",
    ),
    r"\b(?:commercial\s*driver|trucker|long[- ]haul|delivery)\b": (
        RiskLevel.MODERATE,
        "Commercial driving — road accident exposure.",
    ),
    r"\b(?:warehouse|factory|manufacturing|machinery)\b": (
        RiskLevel.MODERATE,
        "Industrial work — machinery and repetitive stress risks.",
    ),
    r"\b(?:self[- ]employed|freelance|contractor|gig)\b": (
        RiskLevel.LOW,
        "Self-employed — income stability concern (financial underwriting).",
    ),
}

_LIFESTYLE_RULES: dict[str, tuple[RiskLevel, str]] = {
    r"\b(?:skydiving|base\s*jump|wingsuit|hang\s*gliding)\b": (
        RiskLevel.CRITICAL,
        "Extreme aerial sports — very high hazard.",
    ),
    r"\b(?:scuba|deep[- ]sea|underwater\s*diving|cave\s*diving)\b": (
        RiskLevel.HIGH,
        "High-risk diving activities — pressure/decompression hazards.",
    ),
    r"\b(?:rock\s*climb|mountaineering|alpinism)\b": (
        RiskLevel.HIGH,
        "Mountaineering/climbing — fall and altitude risk.",
    ),
    r"\b(?:motorcycle|motocross|racing|rally)\b": (
        RiskLevel.HIGH,
        "Motor racing — high-speed collision risk.",
    ),
    r"\b(?:alcohol|drinking|heavy\s*drinker|alcoholic)\b": (
        RiskLevel.HIGH,
        "Alcohol use concern — liver and behavioral risk.",
    ),
    r"\b(?:drug|substance|opioid|recreational\s*use)\b": (
        RiskLevel.CRITICAL,
        "Substance use — significant underwriting concern.",
    ),
    r"\b(?:travel.*(?:high[- ]risk|dangerous|war|conflict))\b": (
        RiskLevel.MODERATE,
        "Travel to high-risk regions — geopolitical exposure.",
    ),
    r"\b(?:sedentary|inactive|no\s*exercise|rarely\s*exercise)\b": (
        RiskLevel.LOW,
        "Sedentary lifestyle — long-term health risk factor.",
    ),
}

_FINANCIAL_RULES: dict[str, tuple[RiskLevel, str]] = {
    r"\b(?:bankrupt|bankruptcy|insolven)\b": (
        RiskLevel.HIGH,
        "Bankruptcy history — financial stability concern.",
    ),
    r"\b(?:unemployed|laid\s*off|terminated|jobless)\b": (
        RiskLevel.MODERATE,
        "Employment gap — income verification needed.",
    ),
    r"\b\$\s*(?:[\d,]+)\b": None,  # Special handling in method
    r"\b(?:debt|loan|mortgage|liab)\b.*\b(?:high|significant|large|heavy)\b": (
        RiskLevel.MODERATE,
        "High debt burden — financial stability risk.",
    ),
    r"\b(?:dependents|children|child|spouse)\b.*\b(?:multiple|several|[3-9]|many)\b": (
        RiskLevel.LOW,
        "Multiple dependents — coverage adequacy consideration.",
    ),
    r"\b(?:no\s*dependents|single|unmarried)\b": (
        RiskLevel.LOW,
        "No dependents — lower coverage urgency.",
    ),
}

# ── Policy product matching ──────────────────────────────────────────────────

_PRODUCT_PATTERNS: dict[str, str] = {
    "Term Life": r"\b(?:term\s*life|t\d{2}|level\s*term|yearly\s*renewable)\b",
    "Whole Life": r"\b(?:whole\s*life|permanent|universal\s*life|endowment)\b",
    "Disability": r"\b(?:disability|income\s*protection|DI|LTD|STD)\b",
    "Critical Illness": r"\b(?:critical\s*illness|CI|dread\s*disease|specified\s*illness)\b",
    "Long-Term Care": r"\b(?:long[- ]term\s*care|LTC|nursing\s*home|assisted\s*living)\b",
    "Annuity": r"\b(?:annuity|retirement\s*income|pension)\b",
}


class UnderwritingAgent:
    """Agentic underwriting assistant for risk review, policy context, and recommendations.

    Analyses free-text applications across four dimensions (health, occupation,
    lifestyle, financial), matches policy context, scores aggregate risk, and
    generates a structured recommendation with chain-of-thought reasoning.
    """

    # ── Extraction ──────────────────────────────────────────────────────────

    def extract_application(self, application_text: str) -> ApplicationData:
        """Extract structured application data from free text."""
        text = application_text.strip()
        return ApplicationData(
            application_id=self._extract_application_id(text),
            applicant_name=self._extract_applicant_name(text),
            age=self._extract_age(text),
            occupation=self._extract_occupation(text),
            annual_income=self._extract_income(text),
            product_type=self._extract_product_type(text),
            coverage_requested=self._extract_coverage(text),
            medical_history=self._extract_section(text, r"medical|health|condition"),
            lifestyle_notes=self._extract_section(text, r"lifestyle|hobbies|habits|smoking"),
            financial_notes=self._extract_section(text, r"financial|income|debt|assets"),
            raw_text=text,
        )

    @staticmethod
    def _extract_application_id(text: str) -> str:
        match = re.search(
            r"(?:application|app|case)[\s#:]*([A-Z0-9]{4,20})", text, re.IGNORECASE,
        )
        return match.group(1) if match else ""

    @staticmethod
    def _extract_applicant_name(text: str) -> str:
        patterns = [
            r"(?:applicant|insured|proposer|client|name)[\s:]*([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})",
            r"(?:I am|my name is|this is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_age(text: str) -> Optional[int]:
        patterns = [
            r"\b(?:age|aged)[\s:]*(\d{1,3})\b",
            r"\b(\d{2})\s*(?:years?\s*old|yo|yrs|y/o)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if 16 <= age <= 120:
                    return age
        return None

    @staticmethod
    def _extract_occupation(text: str) -> str:
        match = re.search(
            r"(?:occupation|job|profession|work|employed\s*as)[\s:]*([A-Za-z][A-Za-z\s/-]{3,40})",
            text, re.IGNORECASE,
        )
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_income(text: str) -> Optional[float]:
        patterns = [
            r"(?:income|salary|earn)[\s:]*\$?[\s]?([\d,]+(?:\.\d{2})?)",
            r"\$\s?([\d,]+(?:\.\d{2})?)\s*(?:per\s*year|annually|annual|p/a)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_product_type(text: str) -> str:
        lower = text.lower()
        for product, pattern in _PRODUCT_PATTERNS.items():
            if re.search(pattern, lower):
                return product
        return ""

    @staticmethod
    def _extract_coverage(text: str) -> Optional[float]:
        patterns = [
            r"(?:coverage|cover|sum\s*assured|face\s*amount|death\s*benefit)[\s:]*\$?[\s]?([\d,]+(?:\.\d{2})?)",
            r"\$\s?([\d,]+(?:\.\d{2})?)\s*(?:cover|policy|term|benefit)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1).replace(",", ""))
                    if 10_000 <= val <= 100_000_000:
                        return val
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_section(text: str, section_keywords: str) -> str:
        """Extract a tagged section around keyword matches, up to 200 chars."""
        match = re.search(
            rf"(.{{0,100}}\b(?:{section_keywords})\b.{{0,200}})",
            text, re.IGNORECASE,
        )
        return match.group(1).strip() if match else ""

    # ── Risk Assessment ─────────────────────────────────────────────────────

    def assess_risk(self, application: ApplicationData) -> tuple[list[RiskFactor], float]:
        """Evaluate application across all risk dimensions and compute aggregate score."""
        factors: list[RiskFactor] = []

        # Health
        factors.extend(self._check_rules(
            _HEALTH_RULES, application.medical_history + " " + application.raw_text,
            "Health",
        ))

        # Occupation
        factors.extend(self._check_rules(
            _OCCUPATION_RULES,
            application.occupation + " " + application.raw_text,
            "Occupation",
        ))

        # Lifestyle
        factors.extend(self._check_rules(
            _LIFESTYLE_RULES,
            application.lifestyle_notes + " " + application.raw_text,
            "Lifestyle",
        ))

        # Financial
        factors.extend(self._check_rules(
            _FINANCIAL_RULES,
            application.financial_notes + " " + application.raw_text,
            "Financial",
        ))
        factors.extend(self._assess_financial_ratios(application))

        # Age-based risk
        if application.age is not None:
            if application.age >= 65:
                factors.append(RiskFactor(
                    category="Health", name="Advanced age",
                    severity=RiskLevel.MODERATE,
                    description=f"Age {application.age} — increased mortality risk at older ages.",
                ))
            elif application.age <= 25:
                factors.append(RiskFactor(
                    category="Health", name="Young applicant",
                    severity=RiskLevel.LOW,
                    description=f"Age {application.age} — favorable mortality profile.",
                ))

        # Compute aggregate risk score
        risk_score = self._compute_risk_score(factors, application)
        return factors, risk_score

    @staticmethod
    def _check_rules(
        rules: dict[str, tuple[RiskLevel, str] | None],
        text: str,
        category: str,
    ) -> list[RiskFactor]:
        """Scan text against a rule dictionary and return matched RiskFactors."""
        factors: list[RiskFactor] = []
        lower = text.lower()
        for pattern, result in rules.items():
            if result is None:
                continue  # skip special-handling rules
            match = re.search(pattern, lower)
            if match:
                severity, description = result
                factors.append(RiskFactor(
                    category=category,
                    name=match.group(0)[:60],
                    severity=severity,
                    description=description,
                ))
        return factors

    @staticmethod
    def _assess_financial_ratios(application: ApplicationData) -> list[RiskFactor]:
        """Check financial ratios: coverage-to-income and debt indicators."""
        factors: list[RiskFactor] = []
        income = application.annual_income
        coverage = application.coverage_requested

        if income and coverage:
            ratio = coverage / income
            if ratio > 30:
                factors.append(RiskFactor(
                    category="Financial",
                    name="Coverage-to-income ratio",
                    severity=RiskLevel.HIGH,
                    description=f"Coverage (${coverage:,.0f}) is {ratio:.1f}x annual income — excessive relative to earnings.",
                ))
            elif ratio > 20:
                factors.append(RiskFactor(
                    category="Financial",
                    name="Coverage-to-income ratio",
                    severity=RiskLevel.MODERATE,
                    description=f"Coverage (${coverage:,.0f}) is {ratio:.1f}x annual income — above typical guidelines.",
                ))

        if income and income < 30_000 and coverage and coverage > 500_000:
            factors.append(RiskFactor(
                category="Financial",
                name="Low income / high coverage mismatch",
                severity=RiskLevel.HIGH,
                description=f"Income ${income:,.0f} with ${coverage:,.0f} coverage — possible insurable interest concern.",
            ))

        return factors

    @staticmethod
    def _compute_risk_score(factors: list[RiskFactor], application: ApplicationData) -> float:
        """Compute aggregate risk score (0-100) from risk factor severities."""
        severity_weights = {
            RiskLevel.LOW: 5,
            RiskLevel.MODERATE: 15,
            RiskLevel.HIGH: 30,
            RiskLevel.CRITICAL: 50,
        }
        base = 10.0  # baseline risk
        for factor in factors:
            base += severity_weights.get(factor.severity, 5)

        # Age adjustment
        if application.age:
            if application.age < 30:
                base -= 5
            elif application.age > 55:
                base += 5
            if application.age > 70:
                base += 10

        # Missing information penalty
        if not application.occupation:
            base += 3
        if application.age is None:
            base += 3
        if not application.medical_history:
            base += 5

        return min(max(base, 0.0), 100.0)

    # ── Policy Context ──────────────────────────────────────────────────────

    @staticmethod
    def build_policy_context(application: ApplicationData) -> PolicyContext:
        """Build policy context from application data."""
        product = application.product_type or "Term Life"
        coverage = application.coverage_requested

        # Determine premium band
        if application.age and application.age < 35:
            premium_band = "Preferred"
        elif application.age and application.age < 55:
            premium_band = "Standard"
        else:
            premium_band = "Substandard"

        # Suggest exclusions based on risk
        exclusions: list[str] = []
        raw_lower = application.raw_text.lower()
        if "aviation" in raw_lower or "pilot" in raw_lower:
            exclusions.append("Aviation-related death or disability")

        riders: list[str] = []
        if coverage and coverage > 1_000_000:
            riders.append("Accidental Death Benefit Rider")
        if application.age and application.age < 50:
            riders.append("Waiver of Premium Rider (disability)")

        return PolicyContext(
            product_type=product,
            coverage_amount=coverage,
            policy_term_years=20 if "term" in product.lower() else None,
            premium_band=premium_band,
            exclusions=exclusions,
            riders=riders,
        )

    # ── Decision Engine ─────────────────────────────────────────────────────

    @staticmethod
    def make_decision(
        application: ApplicationData,
        risk_factors: list[RiskFactor],
        risk_score: float,
    ) -> tuple[UnderwritingDecision, str, str]:
        """Generate underwriting decision with chain-of-thought reasoning."""

        # Count critical and high factors
        critical_count = sum(1 for f in risk_factors if f.severity == RiskLevel.CRITICAL)
        high_count = sum(1 for f in risk_factors if f.severity == RiskLevel.HIGH)
        moderate_count = sum(1 for f in risk_factors if f.severity == RiskLevel.MODERATE)

        # Chain-of-thought reasoning
        cot_parts = []
        cot_parts.append(f"Risk score: {risk_score:.0f}/100")
        cot_parts.append(
            f"Risk factors: {critical_count} critical, {high_count} high, "
            f"{moderate_count} moderate, "
            f"{len(risk_factors) - critical_count - high_count - moderate_count} low"
        )

        # Decision logic
        if critical_count >= 1:
            decision = UnderwritingDecision.DECLINE
            reasoning = (
                f"Critical risk factors present ({critical_count}). "
                "These represent unacceptable underwriting exposure under standard guidelines."
            )
            cot_parts.append(f"[Decline] critical factors={critical_count}")
        elif risk_score >= 70:
            decision = UnderwritingDecision.DECLINE
            reasoning = (
                f"Aggregate risk score of {risk_score:.0f}/100 exceeds the declinature "
                "threshold (70). Multiple high-severity factors present."
            )
            cot_parts.append(f"[Decline] risk_score={risk_score:.0f} >= 70")
        elif high_count >= 2 and risk_score >= 50:
            decision = UnderwritingDecision.REFER
            reasoning = (
                f"{high_count} high-severity factors with risk score {risk_score:.0f}. "
                "Refer to senior underwriter for manual review and possible rating."
            )
            cot_parts.append(f"[Refer] high_count={high_count}, risk_score={risk_score:.0f}")
        elif high_count >= 1:
            decision = UnderwritingDecision.REFER
            reasoning = (
                f"{high_count} high-severity factor(s) present. "
                "Recommend referral for detailed assessment and possible loading."
            )
            cot_parts.append(f"[Refer] high_count={high_count}")
        elif application.age is None or not application.medical_history:
            decision = UnderwritingDecision.REQUEST_INFO
            missing = []
            if application.age is None:
                missing.append("age")
            if not application.medical_history:
                missing.append("medical history")
            reasoning = (
                f"Missing essential information: {', '.join(missing)}. "
                "Cannot complete assessment without these details."
            )
            cot_parts.append(f"[Request Info] missing={missing}")
        elif moderate_count >= 2 and risk_score >= 30:
            decision = UnderwritingDecision.REFER
            reasoning = (
                f"{moderate_count} moderate factors with risk score {risk_score:.0f}. "
                "Recommend referral with possible standard or rated acceptance."
            )
            cot_parts.append(f"[Refer] moderate_count={moderate_count}")
        elif risk_score < 25:
            decision = UnderwritingDecision.APPROVE
            reasoning = (
                f"Risk score {risk_score:.0f}/100 is well within standard acceptance. "
                "No elevated risk factors. Recommend standard terms."
            )
            cot_parts.append(f"[Approve] risk_score={risk_score:.0f} < 25")
        elif risk_score < 45:
            decision = UnderwritingDecision.APPROVE
            reasoning = (
                f"Risk score {risk_score:.0f}/100 within standard acceptance range. "
                "Minor factors present but within acceptable tolerance."
            )
            cot_parts.append(f"[Approve] risk_score={risk_score:.0f} < 45")
        else:
            decision = UnderwritingDecision.REFER
            reasoning = (
                f"Risk score {risk_score:.0f}/100 warrants manual review. "
                "Multiple moderate factors present."
            )
            cot_parts.append(f"[Refer] fallback")

        cot = " → ".join(cot_parts)
        return decision, reasoning, cot

    # ── Full Pipeline ───────────────────────────────────────────────────────

    def underwrite(self, application_text: str) -> UnderwritingResult:
        """Run the complete underwriting assessment pipeline."""
        # Step 1: Extract structured data
        app = self.extract_application(application_text)

        # Step 2: Risk assessment
        risk_factors, risk_score = self.assess_risk(app)

        # Step 3: Determine overall risk level
        overall_risk = self._overall_risk_level(risk_score, risk_factors)

        # Step 4: Policy context
        policy_context = self.build_policy_context(app)

        # Step 5: Decision and reasoning
        decision, recommendation, reasoning = self.make_decision(app, risk_factors, risk_score)

        # Step 6: Build extracted details for display
        extracted: dict[str, str] = {}
        if app.applicant_name:
            extracted["Applicant"] = app.applicant_name
        if app.application_id:
            extracted["Application #"] = app.application_id
        if app.age is not None:
            extracted["Age"] = str(app.age)
        if app.occupation:
            extracted["Occupation"] = app.occupation
        if app.annual_income is not None:
            extracted["Annual Income"] = f"${app.annual_income:,.0f}"
        if app.product_type:
            extracted["Product"] = app.product_type
        if app.coverage_requested is not None:
            extracted["Coverage"] = f"${app.coverage_requested:,.0f}"

        return UnderwritingResult(
            application=app,
            decision=decision,
            overall_risk=overall_risk,
            risk_score=risk_score,
            risk_factors=risk_factors,
            policy_context=policy_context,
            recommendation=recommendation,
            reasoning=reasoning,
            extracted_details=extracted,
        )

    @staticmethod
    def _overall_risk_level(risk_score: float, risk_factors: list[RiskFactor]) -> RiskLevel:
        has_critical = any(f.severity == RiskLevel.CRITICAL for f in risk_factors)
        if has_critical or risk_score >= 70:
            return RiskLevel.CRITICAL
        if risk_score >= 45:
            return RiskLevel.HIGH
        if risk_score >= 20:
            return RiskLevel.MODERATE
        return RiskLevel.LOW
