"""Gradio UI rendering for the Insurance Underwriting Agent tab."""

import gradio as gr

from .agent import UnderwritingAgent
from .models import UnderwritingDecision, RiskLevel

UNDERWRITING_CSS = """
#underwriting-tab {
    background:
        linear-gradient(180deg, rgba(255,255,255,.72), rgba(255,255,255,.92)),
        var(--theme-panel, #ffffff);
    border: 1px solid var(--theme-line, #d9e2ec);
    border-radius: 18px;
    box-shadow: 0 24px 70px var(--theme-shadow, rgba(16,24,40,.08));
    color: var(--theme-ink, rgba(255,255,255,.92));
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 20px;
}
#underwriting-tab h1, #underwriting-tab h2, #underwriting-tab h3 {
    color: var(--theme-blue, #1ca0f1);
}
#underwriting-tab h4 {
    color: var(--theme-green, #37c78a);
    font-size: 0.8em;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 16px 0 8px;
}
.uw-result-approve {
    color: var(--theme-green, #37c78a);
    font-weight: bold;
    font-size: 1.3em;
}
.uw-result-decline {
    color: var(--theme-red, #ff7369);
    font-weight: bold;
    font-size: 1.3em;
}
.uw-result-refer {
    color: var(--theme-amber, #dfab01);
    font-weight: bold;
    font-size: 1.3em;
}
.uw-result-request {
    color: var(--theme-blue, #1ca0f1);
    font-weight: bold;
    font-size: 1.3em;
}
.uw-metric-card {
    background: var(--theme-panel, #373c3f);
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-radius: 14px;
    padding: 16px;
    margin: 10px 0;
    box-shadow: 0 16px 40px var(--theme-shadow, rgba(16,24,40,.08));
}
.uw-decision-card {
    background: linear-gradient(135deg, var(--theme-panel, #373c3f), var(--theme-surface, #454b4e));
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-left: 4px solid var(--theme-blue, #1ca0f1);
    border-radius: 16px;
    padding: 20px;
    margin: 14px 0;
    box-shadow: 0 18px 48px var(--theme-shadow, rgba(16,24,40,.08));
}
.uw-decision-card.approve { border-left-color: var(--theme-green, #37c78a); }
.uw-decision-card.decline { border-left-color: var(--theme-red, #ff7369); }
.uw-decision-card.refer { border-left-color: var(--theme-amber, #dfab01); }
.uw-decision-card.request { border-left-color: var(--theme-blue, #1ca0f1); }
.risk-low { color: var(--theme-green, #37c78a); }
.risk-moderate { color: var(--theme-amber, #dfab01); }
.risk-high { color: var(--theme-orange, #ff9a56); }
.risk-critical { color: var(--theme-red, #ff7369); }
.uw-extracted-table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
}
.uw-extracted-table td {
    padding: 6px 12px 6px 0;
    vertical-align: top;
}
.uw-extracted-table td:first-child {
    color: var(--theme-muted, rgba(255,255,255,.68));
    font-weight: 600;
    white-space: nowrap;
    width: 130px;
}
.uw-risk-factor {
    border-top: 1px solid var(--theme-line, rgba(255,255,255,.14));
    padding: 10px 0;
}
.uw-risk-factor:first-child { border-top: none; }
.uw-risk-cat {
    display: inline-block;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 0.78em;
    font-weight: 750;
    margin-right: 8px;
}
.uw-risk-cat-Health { background: rgba(255,115,105,0.15); color: var(--theme-red, #ff7369); }
.uw-risk-cat-Occupation { background: rgba(223,171,1,0.15); color: var(--theme-amber, #dfab01); }
.uw-risk-cat-Lifestyle { background: rgba(28,160,241,0.15); color: var(--theme-blue, #1ca0f1); }
.uw-risk-cat-Financial { background: rgba(55,199,138,0.15); color: var(--theme-green, #37c78a); }
.uw-reasoning {
    background: var(--theme-surface, #454b4e);
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-radius: 12px;
    padding: 14px 18px;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 0.88em;
    color: var(--theme-muted, rgba(255,255,255,.68));
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
}
.uw-score-ring {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    border: 4px solid var(--theme-line);
    font-size: 1.1em;
    font-weight: 800;
}
.uw-policy-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 10px;
    margin: 8px 0;
}
.uw-policy-item {
    background: var(--theme-surface, #454b4e);
    border-radius: 12px;
    padding: 10px 14px;
}
.uw-policy-label {
    font-size: 0.75em;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--theme-muted, rgba(255,255,255,.68));
}
.uw-policy-value {
    font-size: 1em;
    font-weight: 650;
    margin-top: 2px;
}
"""

DECISION_CLASSES = {
    "Approve": "uw-result-approve",
    "Decline": "uw-result-decline",
    "Refer": "uw-result-refer",
    "Request Info": "uw-result-request",
}

DECISION_CARD_CLASSES = {
    "Approve": "approve",
    "Decline": "decline",
    "Refer": "refer",
    "Request Info": "request",
}

RISK_CLASSES = {
    "Low": "risk-low",
    "Moderate": "risk-moderate",
    "High": "risk-high",
    "Critical": "risk-critical",
}

RISK_CAT_CLASSES = {
    "Health": "uw-risk-cat-Health",
    "Occupation": "uw-risk-cat-Occupation",
    "Lifestyle": "uw-risk-cat-Lifestyle",
    "Financial": "uw-risk-cat-Financial",
}

DECISION_ICONS = {
    "Approve": "✅",
    "Decline": "❌",
    "Refer": "🔍",
    "Request Info": "📋",
}


def _score_ring_color(risk_score: float) -> str:
    """Return CSS color for the risk score ring based on score."""
    if risk_score >= 70:
        return "#ff7369"
    if risk_score >= 45:
        return "#ff9a56"
    if risk_score >= 20:
        return "#dfab01"
    return "#37c78a"


def _run_underwriting(application_text: str) -> str:
    """Process an underwriting application and return HTML result."""
    if not application_text or not application_text.strip():
        return "<p style='color:var(--theme-red,#ff7369)'>Please enter application details.</p>"

    agent = UnderwritingAgent()
    result = agent.underwrite(application_text)

    decision_cls = DECISION_CLASSES.get(result.decision.value, "uw-result-refer")
    card_cls = DECISION_CARD_CLASSES.get(result.decision.value, "refer")
    risk_cls = RISK_CLASSES.get(result.overall_risk.value, "risk-moderate")
    icon = DECISION_ICONS.get(result.decision.value, "🔍")

    # Extracted details table
    extracted_rows = ""
    for key, value in result.extracted_details.items():
        extracted_rows += f"<tr><td>{key}</td><td>{value}</td></tr>"

    # Risk factors list
    risk_factors_html = ""
    if result.risk_factors:
        for factor in result.risk_factors:
            cat_cls = RISK_CAT_CLASSES.get(factor.category, "")
            sev_cls = RISK_CLASSES.get(factor.severity.value, "risk-moderate")
            risk_factors_html += (
                f"<div class='uw-risk-factor'>"
                f"<span class='uw-risk-cat {cat_cls}'>{factor.category}</span>"
                f"<span class='{sev_cls}'>{factor.severity.value}</span>"
                f"<br><strong>{factor.name}</strong>"
                f"<br><small style='color:var(--theme-muted)'>{factor.description}</small>"
                f"</div>"
            )
    else:
        risk_factors_html = (
            "<p style='color:var(--theme-muted)'>No elevated risk factors detected.</p>"
        )

    # Policy context grid
    pc = result.policy_context
    policy_html = f"""
    <div class='uw-policy-grid'>
        <div class='uw-policy-item'>
            <div class='uw-policy-label'>Product</div>
            <div class='uw-policy-value'>{pc.product_type or '—'}</div>
        </div>
        <div class='uw-policy-item'>
            <div class='uw-policy-label'>Coverage</div>
            <div class='uw-policy-value'>{f'${pc.coverage_amount:,.0f}' if pc.coverage_amount else '—'}</div>
        </div>
        <div class='uw-policy-item'>
            <div class='uw-policy-label'>Premium Band</div>
            <div class='uw-policy-value'>{pc.premium_band or '—'}</div>
        </div>
        <div class='uw-policy-item'>
            <div class='uw-policy-label'>Term</div>
            <div class='uw-policy-value'>{f'{pc.policy_term_years} years' if pc.policy_term_years else '—'}</div>
        </div>
    </div>
    """
    if pc.exclusions:
        policy_html += (
            "<p style='font-size:0.85em;color:var(--theme-amber)'><strong>Exclusions:</strong> "
            + ", ".join(pc.exclusions)
            + "</p>"
        )
    if pc.riders:
        policy_html += (
            "<p style='font-size:0.85em;color:var(--theme-blue)'><strong>Suggested Riders:</strong> "
            + ", ".join(pc.riders)
            + "</p>"
        )

    ring_color = _score_ring_color(result.risk_score)

    html = f"""
    <div id='underwriting-tab' style='padding:20px'>
        <h2>{icon} Underwriting Assessment</h2>

        <div class='uw-decision-card {card_cls}'>
            <div style='display:flex;align-items:center;gap:16px;flex-wrap:wrap'>
                <div class='uw-score-ring' style='border-color:{ring_color};color:{ring_color}'>
                    {result.risk_score:.0f}
                </div>
                <div>
                    <div style='font-size:1.15em;font-weight:700;margin-bottom:4px'>
                        <span class='{decision_cls}'>{result.decision.value}</span>
                        &nbsp;| Risk: <span class='{risk_cls}'>{result.overall_risk.value}</span>
                    </div>
                    <p style='margin:0;color:var(--theme-muted);line-height:1.5'>{result.recommendation}</p>
                </div>
            </div>
        </div>

        <h3>Extracted Details</h3>
        <div class='uw-metric-card'>
            <table class='uw-extracted-table'>
                {extracted_rows}
            </table>
        </div>

        <h3>Risk Factors ({len(result.risk_factors)})</h3>
        <div class='uw-metric-card'>
            {risk_factors_html}
        </div>

        <h3>Policy Context</h3>
        <div class='uw-metric-card'>
            {policy_html}
        </div>

        <h3>Reasoning Chain</h3>
        <div class='uw-reasoning'>{result.reasoning}</div>
    </div>
    """
    return html


def _run_batch(applications_text: str) -> str:
    """Process multiple applications and return summary HTML."""
    import re

    if not applications_text or not applications_text.strip():
        return "<p style='color:var(--theme-red,#ff7369)'>Please enter application details.</p>"

    apps = [a.strip() for a in re.split(r"\n\s*\n|---+", applications_text) if a.strip()]
    if not apps:
        return "<p style='color:var(--theme-red,#ff7369)'>No applications found.</p>"

    agent = UnderwritingAgent()
    rows = ""
    approve = decline = refer = request = 0

    for i, app_text in enumerate(apps, 1):
        result = agent.underwrite(app_text)
        decision_cls = DECISION_CLASSES.get(result.decision.value, "uw-result-refer")
        risk_cls = RISK_CLASSES.get(result.overall_risk.value, "risk-moderate")

        if result.decision == UnderwritingDecision.APPROVE:
            approve += 1
        elif result.decision == UnderwritingDecision.DECLINE:
            decline += 1
        elif result.decision == UnderwritingDecision.REQUEST_INFO:
            request += 1
        else:
            refer += 1

        name = result.application.applicant_name or f"Application #{i}"
        product = result.application.product_type or "—"
        coverage = f"${result.application.coverage_requested:,.0f}" if result.application.coverage_requested else "—"

        rows += (
            f"<div class='uw-metric-card'>"
            f"<strong>{name}</strong> &nbsp;| {product}"
            f" &nbsp;| {coverage}"
            f" &nbsp;| Risk: <span class='{risk_cls}'>{result.overall_risk.value}</span>"
            f" &nbsp;| <span class='{decision_cls}'>{result.decision.value}</span>"
            f"</div>"
        )

    total = len(apps)
    summary = (
        f"<div class='uw-metric-card' style='margin-bottom:16px'>"
        f"<strong>Batch Summary ({total} applications)</strong><br>"
        f"<span class='uw-result-approve'>✅ Approve: {approve}</span> &nbsp;| "
        f"<span class='uw-result-refer'>🔍 Refer: {refer}</span> &nbsp;| "
        f"<span class='uw-result-request'>📋 Request Info: {request}</span> &nbsp;| "
        f"<span class='uw-result-decline'>❌ Decline: {decline}</span>"
        f"</div>"
    )

    html = f"""
    <div id='underwriting-tab' style='padding:20px'>
        <h2>Batch Underwriting Assessment</h2>
        {summary}
        {rows}
    </div>
    """
    return html


def render_underwriting_tab() -> gr.Blocks:
    """Build and return the Insurance Underwriting Agent Gradio tab."""
    with gr.Blocks(elem_id="underwriting-tab") as tab:
        gr.Markdown("""
        # 🏦 Agentic Insurance Underwriting Assistant
        AI-powered underwriting agent that reviews applications, identifies risk factors
        across four dimensions (health, occupation, lifestyle, financial), builds policy
        context, and generates structured recommendations with chain-of-thought reasoning.
        """)

        with gr.Tabs():
            with gr.TabItem("📋 Single Application"):
                gr.Markdown("""
                Enter a free-text insurance application. The agent will extract applicant
                details, scan for risk factors across health/occupation/lifestyle/financial
                dimensions, build policy context, and generate a decision with full reasoning.
                """)
                app_input = gr.Textbox(
                    label="Application Details",
                    placeholder=(
                        "Applicant: Sarah Chen\n"
                        "Application: APP-2024-0842\n"
                        "Age: 42. Occupation: Commercial airline pilot.\n"
                        "Annual income: $180,000. Seeking $2,000,000 term life coverage.\n\n"
                        "Medical: Mild hypertension controlled with medication. "
                        "No other conditions. Non-smoker. Regular exercise.\n\n"
                        "Lifestyle: Enjoys scuba diving and rock climbing on weekends. "
                        "Drinks socially. No drug use.\n\n"
                        "Financial: Two dependents (children ages 8 and 11). "
                        "Mortgage of $450,000 remaining. No other major debts."
                    ),
                    lines=12,
                )
                process_btn = gr.Button("🔍 Run Underwriting Assessment", variant="primary")
                single_output = gr.HTML()
                process_btn.click(
                    fn=_run_underwriting,
                    inputs=[app_input],
                    outputs=[single_output],
                )

            with gr.TabItem("📊 Batch Processing"):
                gr.Markdown("""
                Process multiple applications at once. Separate each application with a blank
                line or `---`. The agent will assess each independently and produce a summary.
                """)
                batch_input = gr.Textbox(
                    label="Applications Batch",
                    placeholder=(
                        "Applicant: Sarah Chen. Age 42. Pilot. $180k income. "
                        "$2M term life. Hypertension. Scuba diving.\n\n"
                        "---\n\n"
                        "Applicant: Marcus Rivera. Age 28. Software engineer. "
                        "$120k income. $500k term life. No medical issues. "
                        "Non-smoker. Sedentary lifestyle."
                    ),
                    lines=12,
                )
                batch_btn = gr.Button("📊 Process Batch", variant="primary")
                batch_output = gr.HTML()
                batch_btn.click(
                    fn=_run_batch,
                    inputs=[batch_input],
                    outputs=[batch_output],
                )

    return tab
