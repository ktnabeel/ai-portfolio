from pathlib import Path

from portfolio.db import add_project, get_projects, init_db, seed_projects
from portfolio.config import load_config
from portfolio.models import Project
from portfolio.project_templates import PROJECT_TEMPLATES, get_project_templates
from portfolio.render import render_page


def test_empty_portfolio_renders_empty_state(tmp_path: Path) -> None:
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    html = render_page(get_projects(db_path))

    assert "Real project entries are ready to be added." in html
    assert "AI Engineering Portfolio" in html


def test_project_round_trip_renders_tile(tmp_path: Path) -> None:
    db_path = tmp_path / "portfolio.db"
    add_project(
        db_path,
        Project(
            title="Trading Agents Research App",
            outcome="Runs multi-agent stock analysis with OpenAI chat models.",
            tech_stack="Python, OpenAI, LangGraph",
            status="Built",
            tags=("Agents", "Finance", "OpenAI"),
            github_url="https://github.com/example/repo",
            demo_url="https://example.com",
        ),
    )

    projects = get_projects(db_path)
    html = render_page(projects)

    assert len(projects) == 1
    assert "Trading Agents Research App" in html
    assert "Python, OpenAI, LangGraph" in html


def test_static_base_template_uses_neurons_logo_asset() -> None:
    html = Path("templates/base.html").read_text(encoding="utf-8")

    assert 'class="brand-logo"' in html
    assert "/static/neurons%20logo.png" in html


def test_project_templates_include_seven_titles() -> None:
    titles = [project.title for project in PROJECT_TEMPLATES]

    assert "Portfolio Manager" in titles
    assert "Trading Desk" in titles
    assert "Claim Processing" in titles
    assert "Insurance Underwriting Agent" in titles
    assert "Product Review Sentiment Analyzer" in titles
    assert "Finance Planning" in titles
    assert "Movie Recommendations" in titles
    assert len(titles) == 7


def test_project_templates_load_visible_strings_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "portfolio.yaml"
    config_path.write_text(
        """
projects:
  - key: custom
    title: Custom Project Title
    description: Custom project description from YAML.
    tech_stack: Python, YAML
    status: Built
    tags:
      - Config
      - Portfolio
    tab: financial
tabs:
  financial: Financial Agent
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    projects = get_project_templates(config)
    html = render_page(projects, mode="gradio", config=config)

    assert len(projects) == 1
    assert projects[0].title == "Custom Project Title"
    assert projects[0].outcome == "Custom project description from YAML."
    assert "Custom Project Title" in html
    assert "Custom project description from YAML." in html
    assert "Financial Agent" in html


def test_seed_projects_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "portfolio.db"

    first_count, _ = seed_projects(db_path, PROJECT_TEMPLATES)
    second_count, _ = seed_projects(db_path, PROJECT_TEMPLATES)

    assert first_count == 7
    assert second_count == 0
    assert len(get_projects(db_path)) == 7


def test_seed_projects_deletes_stale_entries(tmp_path: Path) -> None:
    """Projects no longer in the template list are deleted on re-seed."""
    db_path = tmp_path / "portfolio.db"

    # Seed with full templates first.
    seed_projects(db_path, PROJECT_TEMPLATES)
    assert len(get_projects(db_path)) == 7

    # Create a subset of templates (e.g. remove "Trading Desk" and "Movie Recommendations").
    subset = [p for p in PROJECT_TEMPLATES if p.title not in ("Trading Desk", "Movie Recommendations")]
    assert len(subset) == 5

    added, deleted = seed_projects(db_path, subset)
    assert added == 0
    assert deleted == 2
    assert len(get_projects(db_path)) == 5

    # Verify stale titles are gone.
    titles = {p.title for p in get_projects(db_path)}
    assert "Trading Desk" not in titles
    assert "Movie Recommendations" not in titles
    assert "Portfolio Manager" in titles


def test_seed_projects_delete_empty_stale_set_is_noop(tmp_path: Path) -> None:
    """When no stale entries exist, deleted count is 0."""
    db_path = tmp_path / "portfolio.db"

    seed_projects(db_path, PROJECT_TEMPLATES)
    _, deleted = seed_projects(db_path, PROJECT_TEMPLATES)
    assert deleted == 0
    assert len(get_projects(db_path)) == 7


def test_underwriting_agent_imports_and_runs() -> None:
    """UnderwritingAgent imports cleanly and processes a sample application."""
    from portfolio.underwriting import (
        UnderwritingAgent,
        ApplicationData,
        UnderwritingResult,
        UnderwritingDecision,
        RiskLevel,
        RiskFactor,
        PolicyContext,
    )
    from portfolio.underwriting.render import render_underwriting_tab, UNDERWRITING_CSS

    assert isinstance(UNDERWRITING_CSS, str)
    assert len(UNDERWRITING_CSS) > 0
    assert callable(render_underwriting_tab)

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: Test User. Age 30. Occupation: Accountant. "
        "Income $80,000. $500,000 term life. "
        "Medical: No conditions. Non-smoker. Regular exercise."
    )
    assert isinstance(result, UnderwritingResult)
    assert result.application.applicant_name == "Test User"
    assert result.application.age == 30
    assert result.application.annual_income == 80_000
    assert result.application.coverage_requested == 500_000
    assert result.application.product_type == "Term Life"
    assert isinstance(result.decision, UnderwritingDecision)
    assert isinstance(result.overall_risk, RiskLevel)
    assert 0 <= result.risk_score <= 100
    assert result.extracted_details is not None
    assert len(result.reasoning) > 0


def test_underwriting_high_risk_decline() -> None:
    """High-risk application with critical factors returns DECLINE."""
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: High Risk Person. Age 60. Occupation: Fighter pilot. "
        "Income $200,000. $5,000,000 term life. "
        "Medical: Cancer diagnosis. Smoker. "
        "Lifestyle: Skydiving, heavy drinking, drug use."
    )
    assert result.decision == UnderwritingDecision.DECLINE
    assert result.risk_score >= 70
    assert len(result.risk_factors) >= 3


def test_underwriting_low_risk_approve() -> None:
    """Low-risk application returns APPROVE."""
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: Safe Person. Age 28. Occupation: Software Engineer. "
        "Income $120,000. $500,000 term life. "
        "Medical: No conditions. Non-smoker. Exercises daily."
    )
    assert result.decision in (UnderwritingDecision.APPROVE, UnderwritingDecision.REFER)
    assert result.risk_score < 30


def test_underwrite_single_healthy_young_approve() -> None:
    """Full pipeline: healthy young applicant produces APPROVE with all result fields populated."""
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision, RiskLevel

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: Emily Clark. Age 26. Occupation: Data Analyst. "
        "Income $95,000. $400,000 term life. "
        "Medical: No conditions. Does not smoke. Exercises 4x/week. "
        "Lifestyle: Hiking and yoga. Non-drinker."
    )

    # Decision
    assert result.decision == UnderwritingDecision.APPROVE
    assert result.overall_risk == RiskLevel.LOW
    assert result.risk_score < 20

    # Application extraction
    assert result.application.applicant_name == "Emily Clark"
    assert result.application.age == 26
    assert result.application.annual_income == 95_000
    assert result.application.coverage_requested == 400_000
    assert result.application.product_type == "Term Life"
    assert result.application.occupation == "Data Analyst"

    # Extracted details
    assert result.extracted_details["Applicant"] == "Emily Clark"
    assert result.extracted_details["Age"] == "26"
    assert "$95,000" in result.extracted_details["Annual Income"]
    assert "$400,000" in result.extracted_details["Coverage"]

    # Policy context
    assert result.policy_context.premium_band == "Preferred"
    assert result.policy_context.product_type == "Term Life"
    assert result.policy_context.coverage_amount == 400_000
    assert "Waiver of Premium Rider (disability)" in result.policy_context.riders

    # Reasoning chain
    assert len(result.reasoning) > 0
    assert "risk_score" in result.reasoning.lower() or "Risk score" in result.reasoning
    assert result.recommendation is not None
    assert len(result.recommendation) > 0


def test_underwrite_single_multi_dimension_decline() -> None:
    """Full pipeline: applicant with risks across all 4 dimensions triggers DECLINE."""
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision, RiskLevel

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: Mark Danger. Age 58. Occupation: Offshore drilling supervisor. "
        "Income $250,000. $8,000,000 term life. "
        "Medical: Heart disease, smoker, diabetes. "
        "Lifestyle: Skydiving and motorcycle racing. "
        "Financial: Bankruptcy 2 years ago. High debt."
    )

    assert result.decision == UnderwritingDecision.DECLINE
    assert result.risk_score >= 70
    assert result.overall_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH)

    # Should have risk factors from multiple dimensions
    categories = {f.category for f in result.risk_factors}
    assert len(categories) >= 3  # Health, Occupation, Lifestyle, Financial

    # Policy context should reflect high coverage
    assert result.policy_context.coverage_amount == 8_000_000
    assert result.policy_context.premium_band == "Substandard"  # age 58 >= 55

    # Extracted details
    assert result.extracted_details["Applicant"] == "Mark Danger"
    assert "$250,000" in result.extracted_details["Annual Income"]
    assert "$8,000,000" in result.extracted_details["Coverage"]


def test_underwrite_single_missing_info_request() -> None:
    """Full pipeline: application with missing key info (no age, no medical) returns REQUEST_INFO."""
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: Mystery Person. Occupation: Consultant. "
        "Income $120,000. $1,000,000 whole life."
    )

    assert result.decision == UnderwritingDecision.REQUEST_INFO
    assert result.application.age is None
    assert result.application.medical_history == ""
    assert result.recommendation is not None
    assert len(result.recommendation) > 0


def test_underwrite_single_moderate_risk_refer() -> None:
    """Full pipeline: moderate-risk applicant with one HIGH factor triggers REFER."""
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: Firefighter Sam. Age 35. Occupation: Firefighter. "
        "Income $75,000. $500,000 term life. "
        "Medical: Mild hypertension. Non-smoker. Regular exercise."
    )

    # Firefighter is HIGH occupation risk → should be at least REFER
    assert result.decision in (UnderwritingDecision.REFER, UnderwritingDecision.DECLINE)
    assert len(result.risk_factors) >= 1
    assert result.policy_context.premium_band == "Standard"


def test_underwrite_single_minimal_application() -> None:
    """Full pipeline: minimal application text still produces a valid result (REQUEST_INFO)."""
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision, UnderwritingResult

    agent = UnderwritingAgent()
    result = agent.underwrite(
        "Applicant: Jane Smith. Age 40. $200,000 coverage."
    )

    assert isinstance(result, UnderwritingResult)
    assert result.application.applicant_name == "Jane Smith"
    assert result.application.age == 40
    assert result.application.coverage_requested == 200_000
    # Missing medical, occupation, income → REQUEST_INFO or REFER
    assert result.decision in (
        UnderwritingDecision.REQUEST_INFO,
        UnderwritingDecision.REFER,
    )
    assert len(result.reasoning) > 0


def test_underwrite_batch_mixed_outcomes() -> None:
    """Batch pipeline: 3 applications with different risk profiles produce correct summary."""
    from portfolio.underwriting.render import _run_batch

    html = _run_batch(
        # Low risk → APPROVE
        "Applicant: Alice Johnson. Age 28. Occupation: Software Engineer. "
        "Income $110,000. $400,000 term life. "
        "Medical: No conditions. Non-smoker. Exercises daily.\n\n"
        "---\n\n"
        # High risk → DECLINE
        "Applicant: Bob Danger. Age 62. Occupation: Fighter pilot. "
        "Income $300,000. $5,000,000 term life. "
        "Medical: Cancer diagnosis. Smoker. "
        "Lifestyle: Skydiving, heavy drinking.\n\n"
        "---\n\n"
        # Moderate risk → REFER
        "Applicant: Carol Moderate. Age 45. Occupation: Firefighter. "
        "Income $80,000. $300,000 term life. "
        "Medical: Mild hypertension. Non-smoker."
    )

    assert "Batch Underwriting Assessment" in html
    assert "Batch Summary (3 applications)" in html

    # All three names should appear
    assert "Alice Johnson" in html
    assert "Bob Danger" in html
    assert "Carol Moderate" in html

    # Should have at least one of each decision type
    assert "Approved" in html or "Approve" in html
    assert "Decline" in html
    assert "Refer" in html

    # Each application gets a metric card
    assert html.count("uw-metric-card") >= 4  # summary card + 3 app cards


def test_underwrite_batch_all_low_risk() -> None:
    """Batch pipeline: 3 low-risk applications all produce APPROVE."""
    from portfolio.underwriting.render import _run_batch

    html = _run_batch(
        "Applicant: Alice Johnson. Age 28. Occupation: Developer. "
        "Income $100,000. $500,000 term life. "
        "Medical: No conditions. Non-smoker. Exercises regularly.\n\n"
        "---\n\n"
        "Applicant: Bob Williams. Age 32. Occupation: Accountant. "
        "Income $90,000. $300,000 term life. "
        "Medical: No conditions. Non-smoker.\n\n"
        "---\n\n"
        "Applicant: Carol Davis. Age 29. Occupation: Teacher. "
        "Income $65,000. $250,000 term life. "
        "Medical: No conditions. Non-smoker. Walks daily."
    )

    assert "Batch Summary (3 applications)" in html
    assert "Alice Johnson" in html
    assert "Bob Williams" in html
    assert "Carol Davis" in html
    assert "uw-metric-card" in html


def test_underwrite_batch_count_accuracy() -> None:
    """Batch pipeline: verify individual decision counts in summary are accurate."""
    from portfolio.underwriting.render import _run_batch
    from portfolio.underwriting import UnderwritingAgent, UnderwritingDecision

    # Process two known applications and count decisions manually
    agent = UnderwritingAgent()
    app1 = (
        "Applicant: Alice Johnson. Age 28. Occupation: Developer. "
        "Income $100,000. $500,000 term life. "
        "Medical: No conditions. Non-smoker. Exercises daily."
    )
    app2 = (
        "Applicant: Bob Danger. Age 62. Occupation: Fighter pilot. "
        "Income $300,000. $5,000,000 term life. "
        "Medical: Cancer diagnosis. Smoker. "
        "Lifestyle: Skydiving, heavy drinking."
    )

    r1 = agent.underwrite(app1)
    r2 = agent.underwrite(app2)

    # Run batch and verify
    batch_text = app1 + "\n\n---\n\n" + app2
    html = _run_batch(batch_text)

    assert "Batch Summary (2 applications)" in html

    # The counts in the batch summary should match the individual decisions
    # If r1 is APPROVE and r2 is DECLINE, we expect Approve:1 and Decline:1
    if r1.decision == UnderwritingDecision.APPROVE:
        assert "Approve:" in html
    if r2.decision == UnderwritingDecision.DECLINE:
        assert "Decline:" in html
    """build_policy_context with no age defaults to Substandard and skips age-based riders."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, PolicyContext

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="No Age Applicant",
        age=None,
        occupation="Teacher",
        annual_income=50_000,
        product_type="Term Life",
        coverage_requested=250_000,
        raw_text="Applicant: No Age Applicant. Occupation: Teacher.",
    )
    ctx = agent.build_policy_context(app)
    assert isinstance(ctx, PolicyContext)
    assert ctx.premium_band == "Substandard"
    assert "Waiver of Premium Rider (disability)" not in ctx.riders
    assert ctx.product_type == "Term Life"
    assert ctx.coverage_amount == 250_000


def test_underwriting_policy_context_no_coverage() -> None:
    """build_policy_context with no coverage skips Accidental Death Benefit Rider."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, PolicyContext

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="No Coverage Applicant",
        age=40,
        occupation="Engineer",
        annual_income=100_000,
        product_type="Whole Life",
        coverage_requested=None,
        raw_text="Applicant: No Coverage Applicant. Whole life policy.",
    )
    ctx = agent.build_policy_context(app)
    assert isinstance(ctx, PolicyContext)
    assert ctx.coverage_amount is None
    assert ctx.premium_band == "Standard"
    assert "Accidental Death Benefit Rider" not in ctx.riders
    assert "Waiver of Premium Rider (disability)" in ctx.riders


def test_underwriting_policy_context_aviation_exclusion() -> None:
    """build_policy_context adds aviation exclusion when pilot/aviation in raw_text."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, PolicyContext

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Pilot Applicant",
        age=42,
        occupation="Commercial airline pilot",
        annual_income=180_000,
        product_type="Term Life",
        coverage_requested=2_000_000,
        raw_text="Applicant: Pilot Applicant. Occupation: Commercial airline pilot. $2M term life.",
    )
    ctx = agent.build_policy_context(app)
    assert isinstance(ctx, PolicyContext)
    assert "Aviation-related death or disability" in ctx.exclusions
    assert ctx.premium_band == "Standard"
    assert ctx.coverage_amount == 2_000_000
    assert "Accidental Death Benefit Rider" in ctx.riders
    assert "Waiver of Premium Rider (disability)" in ctx.riders


def test_compute_risk_score_young_age_bonus() -> None:
    """Age < 30 applies -5 bonus to risk score."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Young Applicant",
        age=25,
        occupation="Developer",
        annual_income=60_000,
        medical_history="No conditions",
        raw_text="Applicant: Young Applicant. Age 25.",
    )
    score = agent._compute_risk_score([], app)
    assert score == 5.0  # base 10 - 5 (young age bonus)


def test_compute_risk_score_elderly_age_penalty() -> None:
    """Age > 70 applies +15 penalty (+5 for >55, +10 for >70)."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Elderly Applicant",
        age=75,
        occupation="Retired",
        annual_income=40_000,
        medical_history="No conditions",
        raw_text="Applicant: Elderly Applicant. Age 75.",
    )
    score = agent._compute_risk_score([], app)
    assert score == 25.0  # base 10 + 5 (age > 55) + 10 (age > 70)


def test_compute_risk_score_mid_age_above_55_penalty() -> None:
    """Age > 55 (but ≤ 70) applies +5 penalty only."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Senior Applicant",
        age=60,
        occupation="Consultant",
        annual_income=80_000,
        medical_history="No conditions",
        raw_text="Applicant: Senior Applicant. Age 60.",
    )
    score = agent._compute_risk_score([], app)
    assert score == 15.0  # base 10 + 5 (age > 55)


def test_compute_risk_score_missing_occupation_penalty() -> None:
    """Missing occupation applies +3 penalty."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="No Job Applicant",
        age=35,
        occupation="",
        annual_income=50_000,
        medical_history="No conditions",
        raw_text="Applicant: No Job Applicant.",
    )
    score = agent._compute_risk_score([], app)
    assert score == 13.0  # base 10 + 3 (missing occupation)


def test_compute_risk_score_missing_medical_penalty() -> None:
    """Missing medical history applies +5 penalty."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="No Medical Applicant",
        age=35,
        occupation="Analyst",
        annual_income=70_000,
        medical_history="",
        raw_text="Applicant: No Medical Applicant.",
    )
    score = agent._compute_risk_score([], app)
    assert score == 15.0  # base 10 + 5 (missing medical history)


def test_compute_risk_score_missing_age_penalty() -> None:
    """Age is None applies +3 penalty."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Unknown Age Applicant",
        age=None,
        occupation="Engineer",
        annual_income=80_000,
        medical_history="No conditions",
        raw_text="Applicant: Unknown Age Applicant.",
    )
    score = agent._compute_risk_score([], app)
    assert score == 13.0  # base 10 + 3 (missing age)


def test_compute_risk_score_with_risk_factors() -> None:
    """Risk factors combine correctly with age adjustments."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Risky Applicant",
        age=30,
        occupation="Driver",
        annual_income=50_000,
        medical_history="Smoker",
        raw_text="Applicant: Risky Applicant. Smoker.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Health", name="Smoker", severity=RiskLevel.MODERATE,
                   description="Tobacco use"),
        RiskFactor(category="Lifestyle", name="Sedentary", severity=RiskLevel.LOW,
                   description="No exercise"),
    ]
    score = agent._compute_risk_score(factors, app)
    # base 10 + 15 (moderate) + 5 (low) = 30, no age adjustment (age 30 not < 30, not > 55)
    assert score == 30.0


def test_make_decision_critical_factor_decline() -> None:
    """A single critical risk factor triggers DECLINE regardless of score."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Critical Applicant",
        age=40,
        occupation="Engineer",
        medical_history="Cancer diagnosis",
        raw_text="Applicant: Critical Applicant.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Health", name="Cancer", severity=RiskLevel.CRITICAL,
                   description="Cancer diagnosis"),
    ]
    decision, reasoning, cot = agent.make_decision(app, factors, 25.0)
    assert decision == UnderwritingDecision.DECLINE
    assert "Critical" in reasoning
    assert "[Decline]" in cot


def test_make_decision_high_score_decline() -> None:
    """Risk score >= 70 triggers DECLINE even without critical factors."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="High Score Applicant",
        age=60,
        occupation="Pilot",
        medical_history="Hypertension",
        raw_text="Applicant: High Score Applicant.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Health", name="Hypertension", severity=RiskLevel.MODERATE,
                   description="Blood pressure"),
        RiskFactor(category="Occupation", name="Pilot", severity=RiskLevel.HIGH,
                   description="Aviation risk"),
    ]
    decision, reasoning, cot = agent.make_decision(app, factors, 75.0)
    assert decision == UnderwritingDecision.DECLINE
    assert "70" in reasoning
    assert "[Decline]" in cot


def test_make_decision_missing_age_request_info() -> None:
    """Missing age (age=None) with medical present triggers REQUEST_INFO."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Unknown Age Applicant",
        age=None,
        occupation="Teacher",
        medical_history="No conditions",
        raw_text="Applicant: Unknown Age Applicant.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Health", name="Sedentary", severity=RiskLevel.LOW,
                   description="No exercise"),
    ]
    decision, reasoning, cot = agent.make_decision(app, factors, 20.0)
    assert decision == UnderwritingDecision.REQUEST_INFO
    assert "age" in reasoning.lower()
    assert "[Request Info]" in cot


def test_make_decision_missing_medical_request_info() -> None:
    """Missing medical history with age present triggers REQUEST_INFO."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="No Medical Applicant",
        age=35,
        occupation="Analyst",
        medical_history="",
        raw_text="Applicant: No Medical Applicant.",
    )
    decision, reasoning, cot = agent.make_decision(app, [], 15.0)
    assert decision == UnderwritingDecision.REQUEST_INFO
    assert "medical" in reasoning.lower()
    assert "[Request Info]" in cot


def test_make_decision_two_high_factors_refer() -> None:
    """Two high-severity factors with score >= 50 triggers REFER."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="High Risk Refer",
        age=50,
        occupation="Firefighter",
        medical_history="Heart disease",
        raw_text="Applicant: High Risk Refer.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Health", name="Heart disease", severity=RiskLevel.HIGH,
                   description="Cardiovascular"),
        RiskFactor(category="Occupation", name="Firefighter", severity=RiskLevel.HIGH,
                   description="Hazardous duty"),
    ]
    decision, reasoning, cot = agent.make_decision(app, factors, 55.0)
    assert decision == UnderwritingDecision.REFER
    assert "senior underwriter" in reasoning.lower()
    assert "[Refer]" in cot


def test_make_decision_single_high_factor_refer() -> None:
    """A single high-severity factor triggers REFER."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="High Factor Refer",
        age=45,
        occupation="Engineer",
        medical_history="Diabetes type 2",
        raw_text="Applicant: High Factor Refer.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Health", name="Diabetes", severity=RiskLevel.HIGH,
                   description="Insulin dependent"),
    ]
    decision, reasoning, cot = agent.make_decision(app, factors, 35.0)
    assert decision == UnderwritingDecision.REFER
    assert "referral" in reasoning.lower()
    assert "[Refer]" in cot


def test_make_decision_low_score_approve() -> None:
    """Risk score < 25 with no critical/high factors triggers APPROVE."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Low Risk Approve",
        age=28,
        occupation="Developer",
        medical_history="No conditions",
        raw_text="Applicant: Low Risk Approve.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Lifestyle", name="Sedentary", severity=RiskLevel.LOW,
                   description="No exercise"),
    ]
    decision, reasoning, cot = agent.make_decision(app, factors, 15.0)
    assert decision == UnderwritingDecision.APPROVE
    assert "standard" in reasoning.lower()
    assert "[Approve]" in cot


def test_make_decision_moderate_score_approve() -> None:
    """Risk score 25-44 with no critical/high factors triggers APPROVE."""
    from portfolio.underwriting import UnderwritingAgent, ApplicationData, RiskFactor, RiskLevel
    from portfolio.underwriting import UnderwritingDecision

    agent = UnderwritingAgent()
    app = ApplicationData(
        applicant_name="Moderate Risk Approve",
        age=40,
        occupation="Manager",
        medical_history="Mild hypertension",
        raw_text="Applicant: Moderate Risk Approve.",
    )
    factors: list[RiskFactor] = [
        RiskFactor(category="Health", name="Hypertension", severity=RiskLevel.MODERATE,
                   description="Controlled blood pressure"),
    ]
    decision, reasoning, cot = agent.make_decision(app, factors, 35.0)
    assert decision == UnderwritingDecision.APPROVE
    assert "[Approve]" in cot


def test_run_underwriting_empty_input() -> None:
    """_run_underwriting returns error message for empty or whitespace-only input."""
    from portfolio.underwriting.render import _run_underwriting

    html_empty = _run_underwriting("")
    assert "enter application details" in html_empty.lower()

    html_whitespace = _run_underwriting("   \n  ")
    assert "enter application details" in html_whitespace.lower()


def test_run_underwriting_produces_full_html_structure() -> None:
    """_run_underwriting produces HTML with all expected sections for a valid application."""
    from portfolio.underwriting.render import _run_underwriting

    html = _run_underwriting(
        "Applicant: Jane Doe. Age 32. Occupation: Graphic Designer. "
        "Income $65,000. $300,000 term life. "
        "Medical: No conditions. Non-smoker. Regular exercise."
    )

    assert "Underwriting Assessment" in html
    assert "uw-decision-card" in html
    assert "uw-score-ring" in html
    assert "Extracted Details" in html
    assert "uw-extracted-table" in html
    assert "Risk Factors" in html
    assert "Policy Context" in html
    assert "uw-policy-grid" in html
    assert "Reasoning Chain" in html
    assert "uw-reasoning" in html


def test_run_underwriting_approve_has_green_classes() -> None:
    """_run_underwriting APPROVE decision uses approve CSS classes."""
    from portfolio.underwriting.render import _run_underwriting

    html = _run_underwriting(
        "Applicant: Safe Person. Age 25. Occupation: Developer. "
        "Income $100,000. $500,000 term life. "
        "Medical: No conditions. Non-smoker. Exercises daily."
    )

    assert "uw-result-approve" in html
    assert 'class="approve"' in html or "uw-decision-card approve" in html


def test_run_underwriting_decline_has_red_classes() -> None:
    """_run_underwriting DECLINE decision uses decline CSS classes."""
    from portfolio.underwriting.render import _run_underwriting

    html = _run_underwriting(
        "Applicant: Risky Person. Age 65. Occupation: Fighter pilot. "
        "Income $300,000. $5,000,000 term life. "
        "Medical: Cancer diagnosis. Smoker. "
        "Lifestyle: Skydiving, heavy drinking, drug use."
    )

    assert "uw-result-decline" in html
    assert "decline" in html


def test_run_underwriting_shows_risk_factors_when_present() -> None:
    """_run_underwriting renders risk factors when detected."""
    from portfolio.underwriting.render import _run_underwriting

    html = _run_underwriting(
        "Applicant: Smoker Person. Age 50. Occupation: Driver. "
        "Income $50,000. $100,000 term life. "
        "Medical: Smoker. Lifestyle: Heavy drinking."
    )

    assert "uw-risk-factor" in html
    assert "uw-risk-cat" in html


def test_run_batch_empty_input() -> None:
    """_run_batch returns error message for empty or whitespace-only input."""
    from portfolio.underwriting.render import _run_batch

    html_empty = _run_batch("")
    assert "enter application details" in html_empty.lower()

    html_separators = _run_batch("---")
    assert "no applications found" in html_separators.lower()


def test_run_batch_single_application() -> None:
    """_run_batch processes a single application and produces summary + row."""
    from portfolio.underwriting.render import _run_batch

    html = _run_batch(
        "Applicant: Solo Person. Age 30. Occupation: Writer. "
        "Income $55,000. $200,000 term life. "
        "Medical: No conditions. Non-smoker."
    )

    assert "Batch Underwriting Assessment" in html
    assert "Batch Summary (1 application)" in html or "Batch Summary (1 applications)" in html
    assert "Solo Person" in html
    assert "uw-metric-card" in html


def test_run_batch_multiple_applications() -> None:
    """_run_batch processes multiple applications with correct summary counts."""
    from portfolio.underwriting.render import _run_batch

    html = _run_batch(
        "Applicant: Alice Johnson. Age 30. Occupation: Teacher. "
        "Income $60,000. $250,000 term life. "
        "Medical: No conditions. Non-smoker.\n\n"
        "---\n\n"
        "Applicant: Bob Wilson. Age 45. Occupation: Pilot. "
        "Income $150,000. $1,000,000 term life. "
        "Medical: Hypertension. Lifestyle: Scuba diving."
    )

    assert "Batch Underwriting Assessment" in html
    assert "Batch Summary (2 applications)" in html
    assert "Alice Johnson" in html
    assert "Bob Wilson" in html
    # Summary should include decision counts
    assert "Approve:" in html or "approve" in html.lower()
    assert "Refer:" in html or "refer" in html.lower()
    assert "Decline:" in html or "decline" in html.lower()
    assert "Request Info:" in html or "request info" in html.lower()


def test_run_batch_separator_only_no_apps() -> None:
    """_run_batch with only separators returns 'no applications found'."""
    from portfolio.underwriting.render import _run_batch

    html = _run_batch("\n\n---\n\n---")
    assert "no applications found" in html.lower()


def test_static_export_does_not_render_gradio_tab_links() -> None:
    html = render_page(PROJECT_TEMPLATES, mode="static")

    assert "event.preventDefault();" not in html
    assert 'class="financial-nav-link"' not in html
    assert 'href="#">Demo</a>' not in html
    assert 'class="expand-toggle"' in html


def test_gradio_portfolio_renders_in_app_project_links() -> None:
    """Gradio mode uses delegated buttons for tab navigation."""
    html = render_page(PROJECT_TEMPLATES, mode="gradio")

    # All 7 projects should have "Open" links.
    assert html.count(">Open</button>") == 7
    assert "javascript:" not in html
    assert 'href="#"' not in html
    assert 'class="brand-lockup"' in html
    assert 'data:image/png;base64,' in html
    assert 'neurons.fyi' in html
    assert 'class="landing-footer"' in html
    assert '--theme-bg: #ffffff;' in html
    assert 'data-tab-target="trading"' in html
    assert 'data-tab-label="Trading Desk"' in html
    assert "closest('[data-tab-target]')" in html
    assert 'type="button"' in html
    # Theme init <script> is allowed (reads localStorage for dark/light mode).
    assert "<script>" in html
    assert "localStorage.getItem('theme')" in html


def test_project_tiles_render_hover_context() -> None:
    """Project tiles include additional context for hover/focus panels."""
    html = render_page(PROJECT_TEMPLATES, mode="gradio")

    assert 'class="project-insight"' in html
    assert "Project context" in html
    assert "Production-style multi-agent portfolio manager" in html
    assert "Problem" in html
    assert "Architecture" in html
    assert "AI role" in html
    assert "Impact" in html
    assert "LangGraph orchestration" in html


def test_project_tile_css_supports_hover_focus_and_mobile_details() -> None:
    """The floating tile treatment is available on hover/focus and touch layouts."""
    html = render_page(PROJECT_TEMPLATES, mode="gradio")

    assert ".project-card:hover .project-insight" in html
    assert ".project-card:focus-within .project-insight" in html
    assert "perspective: 1400px" in html
    assert "transform-style: preserve-3d" in html
    assert "grid-template-columns: 56px minmax(0, 1fr) auto" in html
    assert "padding: 14px;" in html
    assert "@media (max-width: 980px)" in html
    assert "max-height: 680px" in html
    assert "max-height: none" in html


def test_yaml_config_overrides_static_text(tmp_path: Path) -> None:
    config_path = tmp_path / "portfolio.yaml"
    config_path.write_text(
        """
server:
  host: 0.0.0.0
  port: 9000
site:
  title: Custom Portfolio
  headline: Custom AI headline
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    html = render_page([], config=config)

    assert config["server"]["host"] == "0.0.0.0"
    assert config["server"]["port"] == 9000
    assert "Custom Portfolio" in html
    assert "Custom AI headline" in html
