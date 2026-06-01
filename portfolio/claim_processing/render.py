"""Gradio UI rendering for the Claim Processing tab."""

import re

import gradio as gr

from .processor import ClaimProcessor
from .models import FraudRisk, ClaimSeverity, RoutingDecision

CLAIM_DARK_CSS = """
#claim-tab {
    background:
        radial-gradient(circle at top left, rgba(37,99,235,.08), transparent 32%),
        linear-gradient(180deg, rgba(255,255,255,.84), rgba(255,255,255,.96)),
        var(--theme-panel, #ffffff);
    border: 1px solid rgba(217,226,236,.9);
    border-radius: 22px;
    box-shadow: 0 24px 70px rgba(16,24,40,.10);
    color: var(--theme-ink, rgba(255,255,255,.92));
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 20px;
}
#claim-tab h1, #claim-tab h2, #claim-tab h3 {
    color: var(--theme-blue, #1ca0f1);
}
.result-approve {
    color: var(--theme-green, #37c78a);
    font-weight: bold;
    font-size: 1.2em;
}
.result-deny {
    color: var(--theme-red, #ff7369);
    font-weight: bold;
    font-size: 1.2em;
}
.result-review {
    color: var(--theme-amber, #dfab01);
    font-weight: bold;
    font-size: 1.2em;
}
.result-escalate {
    color: var(--theme-orange, #ff9a56);
    font-weight: bold;
    font-size: 1.2em;
}
.claim-single-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(420px, 0.92fr);
    gap: 24px;
    align-items: start;
}
.claim-input-panel,
.claim-output-panel,
.claim-sample-panel {
    background:
        linear-gradient(180deg, rgba(255,255,255,.94), rgba(255,255,255,.82)),
        var(--theme-panel, #ffffff);
    border: 1px solid rgba(199,213,232,.86);
    border-radius: 18px;
    padding: 20px;
    box-shadow:
        0 26px 70px rgba(16,24,40,.10),
        inset 0 1px 0 rgba(255,255,255,.9);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.claim-output-panel {
    min-height: 440px;
    overflow: hidden;
}
.claim-output-placeholder {
    min-height: 350px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px dashed var(--theme-line, #d9e2ec);
    border-radius: 14px;
    color: var(--theme-muted, #667085);
    text-align: center;
    padding: 24px;
}
.claim-decision-card {
    background:
        linear-gradient(135deg, rgba(255,255,255,.98), rgba(248,250,252,.9)),
        var(--theme-panel, #ffffff);
    border: 1px solid rgba(199,213,232,.9);
    border-left: 4px solid var(--theme-blue, #1ca0f1);
    border-radius: 18px;
    padding: 20px;
    margin: 0 0 14px;
    box-shadow: 0 18px 46px rgba(16,24,40,.10);
}
.claim-decision-card.approve { border-left-color: var(--theme-green, #37c78a); }
.claim-decision-card.deny { border-left-color: var(--theme-red, #ff7369); }
.claim-decision-card.review { border-left-color: var(--theme-amber, #dfab01); }
.claim-decision-card.escalate { border-left-color: var(--theme-orange, #ff9a56); }
.claim-status-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 14px 0 0;
}
.claim-status-pill {
    background: rgba(248,250,252,.86);
    border: 1px solid rgba(199,213,232,.9);
    border-radius: 13px;
    padding: 10px 12px;
}
.claim-status-label {
    color: var(--theme-muted, #667085);
    display: block;
    font-size: 0.76em;
    font-weight: 750;
    letter-spacing: .03em;
    text-transform: uppercase;
}
.claim-status-value {
    display: block;
    font-size: 1.02em;
    font-weight: 800;
    margin-top: 3px;
}
.claim-metric-card {
    background:
        linear-gradient(180deg, rgba(255,255,255,.96), rgba(248,250,252,.88)),
        var(--theme-panel, #ffffff);
    border: 1px solid rgba(199,213,232,.86);
    border-radius: 16px;
    padding: 16px;
    margin: 0 0 12px;
    box-shadow: 0 12px 34px rgba(16,24,40,.08);
}
.fraud-low { color: var(--theme-green, #37c78a); }
.fraud-medium { color: var(--theme-amber, #dfab01); }
.fraud-high { color: var(--theme-red, #ff7369); }
.severity-low { color: var(--theme-green, #37c78a); }
.severity-medium { color: var(--theme-amber, #dfab01); }
.severity-high { color: var(--theme-orange, #ff9a56); }
.severity-critical { color: var(--theme-red, #ff7369); }
.extracted-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    margin: 8px 0;
}
.extracted-table td {
    border-bottom: 1px solid var(--theme-line, #d9e2ec);
    padding: 9px 12px 9px 0;
    vertical-align: top;
    overflow-wrap: anywhere;
}
.extracted-table tr:last-child td {
    border-bottom: none;
}
.extracted-table td:first-child {
    color: var(--theme-muted, rgba(255,255,255,.68));
    font-weight: 600;
    width: 130px;
}
.claim-analysis-result h2 {
    margin-top: 0;
}
.claim-analysis-result h3 {
    color: var(--theme-ink, #101828) !important;
    font-size: 1.02em;
    margin: 18px 0 10px;
}
@media (max-width: 980px) {
    .claim-single-layout {
        grid-template-columns: 1fr;
    }
    .claim-status-grid {
        grid-template-columns: 1fr;
    }
}
"""

SAMPLE_CLAIM = """Claimant: John Smith
Policy: POL-A12345
Claim ID: CLM-2024-7712
Incident date: 03/15/2024

My car was rear-ended at a stoplight. The rear bumper and left tail light are damaged.
Repair estimate is $4,200. No injuries reported. No witnesses were present.

The other driver accepted responsibility and provided insurance information."""

ROUTING_COLORS = {
    "Approve": "result-approve",
    "Deny": "result-deny",
    "Review": "result-review",
    "Escalate": "result-escalate",
}

FRAUD_COLORS = {
    "Low": "fraud-low",
    "Medium": "fraud-medium",
    "High": "fraud-high",
}

SEVERITY_COLORS = {
    "Low": "severity-low",
    "Medium": "severity-medium",
    "High": "severity-high",
    "Critical": "severity-critical",
}


def _process_single(claim_text: str) -> str:
    """Process a single claim and return HTML result."""
    if not claim_text or not claim_text.strip():
        return "<p style='color:var(--theme-red,#ff7369)'>Please enter claim details.</p>"

    processor = ClaimProcessor()
    result = processor.process_claim(claim_text)

    routing_cls = ROUTING_COLORS.get(result.routing.value, "result-review")
    fraud_cls = FRAUD_COLORS.get(result.fraud_risk.value, "fraud-low")
    severity_cls = SEVERITY_COLORS.get(result.severity.value, "severity-low")
    card_cls = result.routing.value.lower()

    # Build extracted details table
    extracted_rows = ""
    for key, value in result.extracted_details.items():
        extracted_rows += f"<tr><td>{key}</td><td>{value}</td></tr>"

    html = f"""
    <div class='claim-analysis-result'>
        <h2>Claim Analysis Results</h2>

        <div class='claim-decision-card {card_cls}'>
            <div style='font-size:1.18em;font-weight:800;margin-bottom:8px'>
                Decision: <span class='{routing_cls}'>{result.routing.value}</span>
            </div>
            <p style='margin:0;color:var(--theme-muted);line-height:1.55'>{result.routing_reasoning}</p>
            <div class='claim-status-grid'>
                <div class='claim-status-pill'>
                    <span class='claim-status-label'>Fraud risk</span>
                    <span class='claim-status-value {fraud_cls}'>{result.fraud_risk.value} ({result.fraud_confidence:.0%})</span>
                </div>
                <div class='claim-status-pill'>
                    <span class='claim-status-label'>Severity</span>
                    <span class='claim-status-value {severity_cls}'>{result.severity.value}</span>
                </div>
            </div>
        </div>

        <h3>Extracted Details</h3>
        <div class='claim-metric-card'>
            <table class='extracted-table'>
                {extracted_rows}
            </table>
        </div>

        <h3>Fraud Assessment</h3>
        <div class='claim-metric-card'>
            <strong>Risk: <span class='{fraud_cls}'>{result.fraud_risk.value}</span></strong>
            <br><small>{result.fraud_reasoning}</small>
        </div>

        <h3>Severity Assessment</h3>
        <div class='claim-metric-card'>
            <strong>Severity: <span class='{severity_cls}'>{result.severity.value}</span></strong>
            <br><small>{result.severity_reasoning}</small>
        </div>

        <h3>Routing Decision</h3>
        <div class='claim-metric-card'>
            <strong>Action: <span class='{routing_cls}'>{result.routing.value}</span></strong>
            <br><small>{result.routing_reasoning}</small>
        </div>
    </div>
    """
    return html


def _process_batch(claims_text: str) -> str:
    """Process multiple claims and return summary HTML."""
    if not claims_text or not claims_text.strip():
        return "<p style='color:var(--theme-red,#ff7369)'>Please enter claim details.</p>"

    # Split by double newline or separator
    claims = [c.strip() for c in re.split(r"\n\s*\n|---+", claims_text) if c.strip()]
    if not claims:
        return "<p style='color:var(--theme-red,#ff7369)'>No claims found.</p>"

    processor = ClaimProcessor()
    rows = ""
    approve = review = deny = escalate = 0

    for i, claim_text in enumerate(claims, 1):
        result = processor.process_claim(claim_text)
        routing_cls = ROUTING_COLORS.get(result.routing.value, "result-review")
        fraud_cls = FRAUD_COLORS.get(result.fraud_risk.value, "fraud-low")

        # Count routing decisions
        if result.routing == RoutingDecision.APPROVE:
            approve += 1
        elif result.routing == RoutingDecision.DENY:
            deny += 1
        elif result.routing == RoutingDecision.ESCALATE:
            escalate += 1
        else:
            review += 1

        amount_str = f"${result.claim.amount:,.2f}" if result.claim.amount else "—"
        claimant = result.claim.claimant or f"Claim #{i}"

        rows += (
            f"<div class='claim-metric-card'>"
            f"<strong>{claimant}</strong> &nbsp;| {result.claim.claim_type.value}"
            f" &nbsp;| {amount_str}"
            f" &nbsp;| Fraud: <span class='{fraud_cls}'>{result.fraud_risk.value}</span>"
            f" &nbsp;| <span class='{routing_cls}'>{result.routing.value}</span>"
            f"</div>"
        )

    total = len(claims)
    summary = (
        f"<div class='claim-metric-card' style='margin-bottom:16px'>"
        f"<strong>Batch Summary ({total} claims)</strong><br>"
        f"<span class='result-approve'>Approve: {approve}</span> &nbsp;| "
        f"<span class='result-review'>Review: {review}</span> &nbsp;| "
        f"<span class='result-deny'>Deny: {deny}</span> &nbsp;| "
        f"<span class='result-escalate'>Escalate: {escalate}</span>"
        f"</div>"
    )

    html = f"""
    <div id='claim-tab' style='padding:10px'>
        <h2>Batch Claim Processing</h2>
        {summary}
        {rows}
    </div>
    """
    return html


def render_claim_tab() -> gr.Blocks:
    """Build and return the Claim Processing Gradio tab."""
    with gr.Blocks(elem_id="claim-tab") as tab:
        gr.Markdown("""
        # 📋 AI-Powered Claim Processing
        Extract claim details, assess fraud risk, classify severity, and route decisions
        automatically from free-text claim descriptions.
        """)

        with gr.Tabs():
            with gr.TabItem("📝 Single Claim"):
                gr.Markdown("""
                Enter a claim description. The system will extract claimant info, type, amount,
                detect fraud indicators, assess severity, and recommend a routing decision.
                """)
                with gr.Row(elem_classes=["claim-single-layout"]):
                    with gr.Column(elem_classes=["claim-input-panel"]):
                        claim_input = gr.Textbox(
                            label="Claim Description",
                            placeholder=SAMPLE_CLAIM,
                            lines=10,
                        )
                        process_btn = gr.Button("🔍 Process Claim", variant="primary")
                    with gr.Column(elem_classes=["claim-output-panel"]):
                        single_output = gr.HTML(
                            """
                            <div class='claim-output-placeholder'>
                                Process a claim to view the routing decision here.
                            </div>
                            """
                        )
                process_btn.click(
                    fn=_process_single,
                    inputs=[claim_input],
                    outputs=[single_output],
                )
                with gr.Group(elem_classes=["claim-sample-panel"]):
                    gr.Markdown("### Sample Claim")
                    gr.Textbox(
                        label="Copy and paste sample",
                        value=SAMPLE_CLAIM,
                        lines=8,
                        interactive=False,
                    )

            with gr.TabItem("📊 Batch Processing"):
                gr.Markdown("""
                Process multiple claims at once. Separate each claim with a blank line or `---`.<br>
                Example:
                ```
                Claimant: Alice Brown. Policy POL-X9988. Car accident on 1/10/2024. Bumper damage. $2,500 estimate.

                ---

                Claimant: Bob Wilson. Home water damage from burst pipe. $45,000 in repairs. No prior claims. Urgent!
                ```
                """)
                batch_input = gr.Textbox(
                    label="Claims Batch",
                    placeholder=(
                        "Claimant: Alice Brown. Auto accident. $2,500.\n\n"
                        "---\n\n"
                        "Claimant: Bob Wilson. Home water damage. $45,000. Urgent!"
                    ),
                    lines=10,
                )
                batch_btn = gr.Button("📊 Process Batch", variant="primary")
                batch_output = gr.HTML()
                batch_btn.click(
                    fn=_process_batch,
                    inputs=[batch_input],
                    outputs=[batch_output],
                )

    return tab
