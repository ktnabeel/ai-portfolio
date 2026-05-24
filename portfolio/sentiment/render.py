"""Gradio UI rendering for the Product Review Sentiment Analyzer tab."""

from collections import defaultdict

import gradio as gr

from .pipeline import get_reviews, get_business_domains
from .analyzer import build_product_sentiment, generate_verdict
from .models import ProductSentiment

SENTIMENT_CSS = """
#sentiment-tab {
    background: var(--theme-bg, #0d1117);
    color: var(--theme-ink, #c9d1d9);
    font-family: 'Segoe UI', system-ui, sans-serif;
}
#sentiment-tab h1, #sentiment-tab h2, #sentiment-tab h3 {
    color: var(--theme-blue, #58a6ff);
}
/* Loading spinner */
.sent-loading {
    text-align: center;
    padding: 60px 20px;
    color: var(--theme-muted, #8b949e);
    font-size: 1.05em;
}
.sent-spinner {
    width: 48px;
    height: 48px;
    margin: 0 auto 18px;
    border: 4px solid var(--theme-line, #30363d);
    border-top-color: var(--theme-blue, #58a6ff);
    border-radius: 50%;
    animation: sent-spin 0.7s linear infinite;
}
@keyframes sent-spin {
    to { transform: rotate(360deg); }
}
.sent-pos { color: #3fb950; font-weight: bold; }
.sent-neg { color: #f85149; font-weight: bold; }
.sent-neu { color: #b0b8c1; font-weight: bold; }
.sent-card {
    background: var(--theme-panel, #161b22);
    border: 1px solid var(--theme-line, #30363d);
    border-radius: 10px;
    padding: 18px;
    margin: 10px 0;
}
.sent-verdict {
    background: linear-gradient(135deg, var(--theme-panel, #161b22), #1a2332);
    border: 1px solid var(--theme-line, #30363d);
    border-left: 4px solid var(--theme-blue, #58a6ff);
    border-radius: 10px;
    padding: 18px 22px;
    margin: 14px 0;
    font-size: 0.96em;
    line-height: 1.7;
}
.sent-verdict em {
    color: var(--theme-blue, #58a6ff);
    font-style: normal;
    font-weight: 600;
}
.sent-bar-wrap {
    height: 10px;
    border-radius: 5px;
    background: var(--theme-line, #30363d);
    margin: 8px 0 12px;
    overflow: hidden;
    display: flex;
}
.sent-bar-pos { background: #3fb950; height: 100%; }
.sent-bar-neu { background: #6e7681; height: 100%; }
.sent-bar-neg { background: #f85149; height: 100%; }
.review-row {
    border-top: 1px solid var(--theme-line, #30363d);
    padding: 12px 0;
}
.review-row:first-child { border-top: none; }
.review-text {
    color: var(--theme-muted, #8b949e);
    font-size: 0.92em;
    line-height: 1.5;
}
/* Side-by-side comparison */
.sent-compare {
    display: flex;
    gap: 20px;
    padding: 10px 0;
}
.sent-col {
    flex: 1;
    min-width: 0;
    background: var(--theme-panel, #161b22);
    border: 1px solid var(--theme-line, #30363d);
    border-radius: 10px;
    padding: 18px;
}
.sent-col-a { border-left: 4px solid var(--theme-blue, #58a6ff); }
.sent-col-b { border-left: 4px solid #d2991d; }
.sent-col-title {
    font-size: 1.15em;
    font-weight: 700;
    color: var(--theme-blue, #58a6ff);
    margin-bottom: 4px;
}
.sent-col-b .sent-col-title { color: #d2991d; }
.sent-compare-summary {
    background: linear-gradient(135deg, #1a2332, #1c1f2a);
    border: 1px solid var(--theme-line, #30363d);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    text-align: center;
}
.sent-winner {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 0.9em;
    margin-left: 6px;
}
.sent-winner-a { background: rgba(88,166,255,0.2); color: #58a6ff; }
.sent-winner-b { background: rgba(210,153,29,0.2); color: #d2991d; }
.sent-stat-row {
    display: flex;
    justify-content: center;
    gap: 30px;
    margin: 8px 0;
    font-size: 0.9em;
}
.sent-stat-item { text-align: center; }
.sent-stat-val { font-size: 1.3em; font-weight: 700; }
.sent-stat-label { color: var(--theme-muted, #8b949e); font-size: 0.85em; }
"""

# Global cache
_review_index: dict[str, list] | None = None
_sentiment_cache: dict[str, ProductSentiment] = {}
_name_to_id: dict[str, str] = {}
_domain_map: dict[str, str] = {}


def _ensure_index():
    """Load reviews from pipeline and index by product_id."""
    global _review_index, _domain_map
    if _review_index is not None:
        return
    reviews = get_reviews()
    _domain_map = get_business_domains()
    _review_index = defaultdict(list)
    for r in reviews:
        _review_index[r.product_id].append(r)


def _get_domain_choices() -> list[str]:
    """Return sorted list of unique business domains."""
    _ensure_index()
    return sorted(set(_domain_map.values()))


def _filter_by_domain(domain: str | None) -> list[str]:
    """Return business names (sorted) for the selected domain. None/empty = all."""
    global _name_to_id
    _ensure_index()
    _name_to_id.clear()

    if not domain:
        # All businesses
        for pid, revs in _review_index.items():
            _name_to_id[revs[0].title] = pid
    else:
        for pid, revs in _review_index.items():
            if _domain_map.get(pid) == domain:
                _name_to_id[revs[0].title] = pid

    return sorted(_name_to_id.keys())


def _get_or_analyze(selection: str) -> ProductSentiment | None:
    """Resolve a business name to its ProductSentiment, computing if needed."""
    if not selection:
        return None
    _ensure_index()
    if not _name_to_id:
        _filter_by_domain(None)
    product_id = _name_to_id.get(selection)
    if product_id is None:
        _filter_by_domain(None)
        product_id = _name_to_id.get(selection)
        if product_id is None:
            return None
    if product_id not in _sentiment_cache:
        reviews = _review_index.get(product_id, [])
        if not reviews:
            return None
        _sentiment_cache[product_id] = build_product_sentiment(reviews)
    return _sentiment_cache[product_id]


def _render_product_card(ps: ProductSentiment, max_reviews: int = 6) -> str:
    """Render a single business sentiment card (verdict + bar + review samples)."""
    verdict = generate_verdict(ps)
    pos_w = ps.positive_pct * 100
    neg_w = ps.negative_pct * 100
    neu_w = ps.neutral_pct * 100

    bar = (
        f'<div class="sent-bar-pos" style="width:{pos_w:.1f}%"></div>'
        f'<div class="sent-bar-neu" style="width:{neu_w:.1f}%"></div>'
        f'<div class="sent-bar-neg" style="width:{neg_w:.1f}%"></div>'
    )

    review_rows = ""
    for s in ps.review_sentiments[:max_reviews]:
        icon = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪"}
        review_rows += (
            f'<div class="review-row">'
            f'<strong>{icon.get(s.label, "")} {s.label}</strong> '
            f'<small>({s.score:.0%} confidence | ⭐{s.rating:.1f})</small>'
            f'<p class="review-text">{s.review_text}</p>'
            f'</div>'
        )

    return f"""
        <div class='sent-verdict'>
            <strong>📝 Customer Verdict</strong><br>
            {verdict}
        </div>
        <div class='sent-card'>
            <strong>Overall Sentiment</strong> &nbsp;| {ps.total_reviews} reviews &nbsp;| ⭐{ps.avg_rating:.1f} avg
            <div class='sent-bar-wrap'>{bar}</div>
            <span class='sent-pos'>🟢 Positive {pos_w:.1f}%</span> &nbsp;
            <span class='sent-neu'>⚪ Neutral {neu_w:.1f}%</span> &nbsp;
            <span class='sent-neg'>🔴 Negative {neg_w:.1f}%</span>
        </div>
        <h3 style='font-size:1em;margin-top:16px'>Review Samples</h3>
        {review_rows}
        <p style='color:var(--theme-muted);font-size:.85em;margin-top:12px'>
            Showing {min(max_reviews, ps.total_reviews)} of {ps.total_reviews} reviews
        </p>
"""


def _score(ps: ProductSentiment) -> float:
    """Compute a composite score for ranking (higher = better)."""
    return ps.avg_rating * 20 + ps.positive_pct * 40 - ps.negative_pct * 30


def _analyze_product(selection: str) -> str:
    """Run sentiment analysis for the selected business (by name), return HTML."""
    if not selection:
        return ""
    ps = _get_or_analyze(selection)
    if ps is None:
        return "<p style='color:#f85149'>Business not found.</p>"

    card = _render_product_card(ps, max_reviews=10)
    return f"""
    <div id='sentiment-tab' style='padding:20px'>
        <h2>📊 {ps.product_title}</h2>
        <h4 style='color:var(--theme-muted,#8b949e);margin-top:-8px'>
            {_domain_map.get(ps.product_id, "")}
        </h4>
        {card}
    </div>
    """


def _compare_products(sel_a: str, sel_b: str) -> str:
    """Render side-by-side comparison of two businesses."""
    if not sel_a or not sel_b:
        return "<p style='color:#f85149'>Please select two businesses to compare.</p>"
    if sel_a == sel_b:
        return "<p style='color:#f85149'>Please select two different businesses to compare.</p>"

    ps_a = _get_or_analyze(sel_a)
    ps_b = _get_or_analyze(sel_b)
    if ps_a is None or ps_b is None:
        missing = sel_a if ps_a is None else sel_b
        return f"<p style='color:#f85149'>Business not found: {missing}</p>"

    score_a = _score(ps_a)
    score_b = _score(ps_b)
    winner = "a" if score_a > score_b else ("b" if score_b > score_a else "tie")

    winner_html = ""
    if winner == "a":
        winner_html = f'<span class="sent-winner sent-winner-a">🏆 {ps_a.product_title}</span>'
    elif winner == "b":
        winner_html = f'<span class="sent-winner sent-winner-b">🏆 {ps_b.product_title}</span>'
    else:
        winner_html = '<span class="sent-winner" style="background:rgba(110,118,129,0.2);color:#6e7681">🤝 Too close to call</span>'

    summary = f"""
    <div class='sent-compare-summary'>
        <strong style='font-size:1.1em'>⚖️ Comparison Summary</strong>
        {winner_html}
        <div class='sent-stat-row'>
            <div class='sent-stat-item' style='color:#58a6ff'>
                <div class='sent-stat-val'>{ps_a.avg_rating:.1f}⭐</div>
                <div class='sent-stat-label'>{ps_a.product_title[:20]}</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:var(--theme-muted)'>vs</div>
                <div class='sent-stat-label'>&nbsp;</div>
            </div>
            <div class='sent-stat-item' style='color:#d2991d'>
                <div class='sent-stat-val'>{ps_b.avg_rating:.1f}⭐</div>
                <div class='sent-stat-label'>{ps_b.product_title[:20]}</div>
            </div>
        </div>
        <div class='sent-stat-row'>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:#3fb950'>{ps_a.positive_pct:.0%}</div>
                <div class='sent-stat-label'>Positive</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:#f85149'>{ps_a.negative_pct:.0%}</div>
                <div class='sent-stat-label'>Negative</div>
            </div>
            <div class='sent-stat-item' style='opacity:0.5'>
                <div class='sent-stat-val'>{ps_a.total_reviews}</div>
                <div class='sent-stat-label'>Reviews</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:#3fb950'>{ps_b.positive_pct:.0%}</div>
                <div class='sent-stat-label'>Positive</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:#f85149'>{ps_b.negative_pct:.0%}</div>
                <div class='sent-stat-label'>Negative</div>
            </div>
            <div class='sent-stat-item' style='opacity:0.5'>
                <div class='sent-stat-val'>{ps_b.total_reviews}</div>
                <div class='sent-stat-label'>Reviews</div>
            </div>
        </div>
    </div>
    """

    card_a = _render_product_card(ps_a, max_reviews=5)
    card_b = _render_product_card(ps_b, max_reviews=5)

    return f"""
    <div id='sentiment-tab' style='padding:20px'>
        {summary}
        <div class='sent-compare'>
            <div class='sent-col sent-col-a'>
                <div class='sent-col-title'>📊 {ps_a.product_title}</div>
                <div style='color:var(--theme-muted);font-size:.85em;margin-bottom:12px'>
                    {_domain_map.get(ps_a.product_id, "")} &nbsp;|&nbsp; ⭐{ps_a.avg_rating:.1f} &nbsp;|&nbsp; {ps_a.total_reviews} reviews
                </div>
                {card_a}
            </div>
            <div class='sent-col sent-col-b'>
                <div class='sent-col-title'>📊 {ps_b.product_title}</div>
                <div style='color:var(--theme-muted);font-size:.85em;margin-bottom:12px'>
                    {_domain_map.get(ps_b.product_id, "")} &nbsp;|&nbsp; ⭐{ps_b.avg_rating:.1f} &nbsp;|&nbsp; {ps_b.total_reviews} reviews
                </div>
                {card_b}
            </div>
        </div>
    </div>
    """


def _init_dropdowns() -> tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown]:
    """Lazy-load domains & businesses. Called once on tab load."""
    domain_choices = ["— All Domains —"] + _get_domain_choices()
    business_choices = _filter_by_domain("")
    dd_info = "Pick a category to filter — or browse all 1,000 businesses"
    biz_info = "Type to search — businesses are filtered by your domain choice"
    return (
        gr.Dropdown(choices=domain_choices, value="— All Domains —", info=dd_info),
        gr.Dropdown(choices=business_choices, info=biz_info),
        gr.Dropdown(choices=business_choices, info=biz_info),
    )


def render_sentiment_tab() -> gr.Blocks:
    """Build and return the Product Review Sentiment Analyzer Gradio tab."""
    with gr.Blocks(elem_id="sentiment-tab") as tab:
        gr.Markdown("""
        # 🍽️ Business Review Sentiment Analyzer
        Explore 1,000 businesses from real Yelp reviews. Pick a domain, then
        select up to two businesses to compare sentiment side by side — no API keys, fully local.
        """)

        # ── Domain selector (populated lazily on tab load) ──
        domain_dd = gr.Dropdown(
            choices=[],
            label="1️⃣ Choose a Business Domain",
            info="Click Load Businesses to populate choices.",
            filterable=True,
            elem_id="sent-domain-dropdown",
        )

        # ── Two business selectors side by side (populated lazily) ──
        with gr.Row():
            business_a_dd = gr.Dropdown(
                choices=[],
                label="2️⃣ Business A",
                info="Click Load Businesses first.",
                filterable=True,
                scale=3,
                elem_id="sent-business-a-dropdown",
            )
            business_b_dd = gr.Dropdown(
                choices=[],
                label="3️⃣ Business B",
                info="Click Load Businesses first.",
                filterable=True,
                scale=3,
                elem_id="sent-business-b-dropdown",
            )

        # ── Action buttons ──
        load_btn = gr.Button("Load Businesses", variant="secondary")
        with gr.Row():
            analyze_a_btn = gr.Button("📊 Analyze A", variant="secondary", scale=1)
            compare_btn = gr.Button("⚖️ Compare Both", variant="primary", scale=1)
            analyze_b_btn = gr.Button("📊 Analyze B", variant="secondary", scale=1)

        analyze_output = gr.HTML()

        # ── Explicit init: avoid a page-load event that blocks tab navigation.
        load_btn.click(
            fn=_init_dropdowns,
            outputs=[domain_dd, business_a_dd, business_b_dd],
            show_progress="minimal",
        )

        # ── Cascading: domain change → filter both business dropdowns + clear both ──
        def _on_domain_change(domain: str) -> tuple[gr.Dropdown, gr.Dropdown]:
            if domain == "— All Domains —":
                domain = ""
            choices = _filter_by_domain(domain)
            return (
                gr.Dropdown(choices=choices, value=None),
                gr.Dropdown(choices=choices, value=None),
            )

        domain_dd.change(
            fn=_on_domain_change,
            inputs=[domain_dd],
            outputs=[business_a_dd, business_b_dd],
        )

        # ── Analyze A on button click ──
        analyze_a_btn.click(
            fn=_analyze_product,
            inputs=[business_a_dd],
            outputs=[analyze_output],
            show_progress="minimal",
        )

        # ── Analyze A on dropdown selection ──
        business_a_dd.change(
            fn=lambda: '<div class="sent-loading"><div class="sent-spinner"></div>⏳ Analyzing reviews with RoBERTa…<br><small>First inference may take a few seconds</small></div>',
            outputs=[analyze_output],
        ).then(
            fn=_analyze_product,
            inputs=[business_a_dd],
            outputs=[analyze_output],
        )

        # ── Analyze B on button click ──
        analyze_b_btn.click(
            fn=_analyze_product,
            inputs=[business_b_dd],
            outputs=[analyze_output],
            show_progress="minimal",
        )

        # ── Analyze B on dropdown selection ──
        business_b_dd.change(
            fn=lambda: '<div class="sent-loading"><div class="sent-spinner"></div>⏳ Analyzing reviews with RoBERTa…<br><small>First inference may take a few seconds</small></div>',
            outputs=[analyze_output],
        ).then(
            fn=_analyze_product,
            inputs=[business_b_dd],
            outputs=[analyze_output],
        )

        # ── Compare both ──
        compare_btn.click(
            fn=lambda: '<div class="sent-loading"><div class="sent-spinner"></div>⏳ Comparing businesses with RoBERTa…<br><small>First inference may take a few seconds</small></div>',
            outputs=[analyze_output],
        ).then(
            fn=_compare_products,
            inputs=[business_a_dd, business_b_dd],
            outputs=[analyze_output],
        )

    return tab
