"""Gradio UI rendering for the Claim Processing tab."""

import re

import gradio as gr

from .processor import ClaimProcessor
from .models import FraudRisk, ClaimSeverity, RoutingDecision

CLAIM_DARK_CSS = """
#claim-tab {
    background: var(--theme-bg, #0d1117);
    color: var(--theme-ink, #c9d1d9);
    font-family: 'Segoe UI', system-ui, sans-serif;
}
#claim-tab h1, #claim-tab h2, #claim-tab h3 {
    color: var(--theme-blue, #58a6ff);
}
.result-approve {
    color: #3fb950;
    font-weight: bold;
    font-size: 1.2em;
}
.result-deny {
    color: #f85149;
    font-weight: bold;
    font-size: 1.2em;
}
.result-review {
    color: #d2991d;
    font-weight: bold;
    font-size: 1.2em;
}
.result-escalate {
    color: #f0883e;
    font-weight: bold;
    font-size: 1.2em;
}
.claim-metric-card {
    background: var(--theme-panel, #161b22);
    border: 1px solid var(--theme-line, #30363d);
    border-radius: 8px;
    padding: 12px;
    margin: 6px 0;
}
.fraud-low { color: #3fb950; }
.fraud-medium { color: #d2991d; }
.fraud-high { color: #f85149; }
.severity-low { color: #3fb950; }
.severity-medium { color: #d2991d; }
.severity-high { color: #f0883e; }
.severity-critical { color: #f85149; }
.extracted-table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
}
.extracted-table td {
    padding: 6px 12px 6px 0;
    vertical-align: top;
}
.extracted-table td:first-child {
    color: var(--theme-muted, #8b949e);
    font-weight: 600;
    white-space: nowrap;
    width: 120px;
}
"""

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
        return "<p style='color:#f85149'>Please enter claim details.</p>"

    processor = ClaimProcessor()
    result = processor.process_claim(claim_text)

    routing_cls = ROUTING_COLORS.get(result.routing.value, "result-review")
    fraud_cls = FRAUD_COLORS.get(result.fraud_risk.value, "fraud-low")
    severity_cls = SEVERITY_COLORS.get(result.severity.value, "severity-low")

    # Build extracted details table
    extracted_rows = ""
    for key, value in result.extracted_details.items():
        extracted_rows += f"<tr><td>{key}</td><td>{value}</td></tr>"

    html = f"""
    <div id='claim-tab' style='padding:20px'>
        <h2>Claim Analysis Results</h2>

        <div class='claim-metric-card'>
            <span class='{routing_cls}'>{result.routing.value}</span>
            &nbsp;| Fraud: <span class='{fraud_cls}'>{result.fraud_risk.value}</span> ({result.fraud_confidence:.0%})
            &nbsp;| Severity: <span class='{severity_cls}'>{result.severity.value}</span>
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
        return "<p style='color:#f85149'>Please enter claim details.</p>"

    # Split by double newline or separator
    claims = [c.strip() for c in re.split(r"\n\s*\n|---+", claims_text) if c.strip()]
    if not claims:
        return "<p style='color:#f85149'>No claims found.</p>"

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
    <div id='claim-tab' style='padding:20px'>
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
                claim_input = gr.Textbox(
                    label="Claim Description",
                    placeholder=(
                        "Claimant: John Smith\n"
                        "Policy: POL-A12345\n"
                        "My car was rear-ended on 3/15/2024 at a stoplight. "
                        "The bumper and tail light are damaged. "
                        "Repair estimate is $4,200. No witnesses."
                    ),
                    lines=8,
                )
                process_btn = gr.Button("🔍 Process Claim", variant="primary")
                single_output = gr.HTML()
                process_btn.click(
                    fn=_process_single,
                    inputs=[claim_input],
                    outputs=[single_output],
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
