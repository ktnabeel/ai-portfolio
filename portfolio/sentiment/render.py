"""Gradio UI rendering for the Product Review Sentiment Analyzer tab."""

from collections import defaultdict

import gradio as gr

from .pipeline import get_reviews, get_amazon_reviews, get_business_domains, get_product_metadata
from .analyzer import build_product_sentiment, generate_verdict
from .models import ProductSentiment

SENTIMENT_CSS = """
#sentiment-tab {
    background:
        radial-gradient(circle at 10% 0%, rgba(124,183,255,.20), transparent 32%),
        radial-gradient(circle at 88% 12%, rgba(85,214,165,.14), transparent 30%),
        linear-gradient(180deg, rgba(255,255,255,.76), rgba(245,249,255,.92)),
        var(--theme-panel, #ffffff);
    border: 1px solid rgba(217,226,236,.9);
    border-radius: 26px;
    box-shadow: 0 28px 80px rgba(16,24,40,.12);
    color: var(--theme-ink, #111827);
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 20px;
    overflow: visible;
}
#sentiment-tab h1, #sentiment-tab h2, #sentiment-tab h3 {
    color: var(--theme-blue, #1ca0f1);
}
.sent-control-panel,
.sent-card,
.sent-col,
.sent-compare-summary {
    background:
        linear-gradient(180deg, rgba(255,255,255,.72), rgba(255,255,255,.48)),
        var(--theme-panel, #ffffff);
    border: 1px solid rgba(199,213,232,.72);
    border-radius: 22px;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.82),
        0 22px 56px rgba(16,24,40,.10);
}
.sent-control-panel {
    padding: 20px;
    margin: 12px 0 18px;
}
.sent-dataset-note {
    color: var(--theme-muted, #667085);
    font-size: .92em;
    line-height: 1.5;
    margin: -4px 0 12px;
}
#sentiment-tab .form,
#sentiment-tab .panel,
#sentiment-tab .block,
#sentiment-tab .gradio-row,
#sentiment-tab .gradio-column {
    background: transparent !important;
    box-shadow: none;
}
#sentiment-tab label,
#sentiment-tab .label-wrap span {
    color: var(--theme-muted, #667085) !important;
    font-weight: 650;
}
#sentiment-tab input,
#sentiment-tab textarea,
#sentiment-tab select,
#sentiment-tab .wrap,
#sentiment-tab .container,
#sentiment-tab [role="listbox"],
#sentiment-tab [data-testid="block-info"] {
    border-color: rgba(185,202,226,.78) !important;
}
#sentiment-tab .wrap,
#sentiment-tab .container {
    background:
        linear-gradient(180deg, rgba(255,255,255,.72), rgba(255,255,255,.52)) !important;
    border-radius: 14px !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.86),
        0 10px 26px rgba(16,24,40,.06) !important;
}
.sent-toolbar-row {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    gap: 12px !important;
    align-items: center !important;
    justify-content: flex-start !important;
    margin-top: 0 !important;
    padding: 0 !important;
}
.sent-toolbar {
    background: transparent !important;
    background-color: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin-top: 10px !important;
    display: inline-block !important;
    width: auto !important;
    max-width: 100% !important;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
}
.sent-toolbar .form,
.sent-toolbar > div,
.sent-toolbar .gradio-row,
.sent-toolbar-row .form,
.sent-toolbar-row > div,
#sentiment-tab .sent-toolbar,
#sentiment-tab .sent-toolbar.block,
#sentiment-tab .sent-toolbar-row,
#sentiment-tab .sent-toolbar-row.block {
    background: transparent !important;
    background-color: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
}
.sent-button-cell,
.sent-button-cell .form {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
}
.sent-toolbar-row > *,
.sent-refresh-btn,
.sent-action-btn,
.sent-primary-action {
    flex: 0 0 auto !important;
    min-width: 0 !important;
    width: auto !important;
}
#sentiment-tab .sent-refresh-btn button,
#sentiment-tab .sent-action-btn button,
#sentiment-tab .sent-primary-action button {
    min-height: 44px !important;
    width: auto !important;
    border-radius: 999px !important;
    border: 1px solid rgba(185,202,226,.72) !important;
    background:
        linear-gradient(180deg, rgba(255,255,255,.82), rgba(255,255,255,.54)) !important;
    color: #111827 !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.92),
        0 12px 30px rgba(16,24,40,.10) !important;
    font-weight: 750 !important;
    letter-spacing: 0 !important;
    backdrop-filter: blur(18px) saturate(170%);
    -webkit-backdrop-filter: blur(18px) saturate(170%);
    transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}
#sentiment-tab .sent-refresh-btn button {
    min-width: 156px !important;
    padding: 0 20px !important;
}
#sentiment-tab .sent-action-btn button {
    min-width: 158px !important;
    padding: 0 22px !important;
}
#sentiment-tab .sent-primary-action button {
    min-width: 246px !important;
    padding: 0 28px !important;
}
#sentiment-tab .sent-primary-action button {
    border-color: rgba(255,122,24,.60) !important;
    background:
        linear-gradient(180deg, rgba(255,139,55,.95), rgba(255,105,20,.92)) !important;
    color: #ffffff !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.38),
        0 16px 34px rgba(255,105,20,.26) !important;
}
#sentiment-tab .sent-refresh-btn button:hover,
#sentiment-tab .sent-action-btn button:hover,
#sentiment-tab .sent-primary-action button:hover {
    transform: translateY(-1px);
    border-color: rgba(124,183,255,.70) !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.94),
        0 16px 38px rgba(16,24,40,.14) !important;
}
#sentiment-tab .sent-primary-action button:hover {
    border-color: rgba(255,122,24,.78) !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.42),
        0 18px 42px rgba(255,105,20,.32) !important;
}
/* Loading spinner */
.sent-loading {
    text-align: center;
    padding: 60px 20px;
    color: var(--theme-muted, rgba(255,255,255,.68));
    font-size: 1.05em;
}
.sent-spinner {
    width: 48px;
    height: 48px;
    margin: 0 auto 18px;
    border: 4px solid var(--theme-line, rgba(255,255,255,.14));
    border-top-color: var(--theme-blue, #1ca0f1);
    border-radius: 50%;
    animation: sent-spin 0.7s linear infinite;
}
@keyframes sent-spin {
    to { transform: rotate(360deg); }
}
.sent-pos { color: var(--theme-green, #37c78a); font-weight: bold; }
.sent-neg { color: var(--theme-red, #ff7369); font-weight: bold; }
.sent-neu { color: var(--theme-muted, rgba(255,255,255,.68)); font-weight: bold; }
.sent-card {
    padding: 18px;
    margin: 10px 0;
}
.sent-verdict {
    background:
        linear-gradient(135deg, rgba(255,255,255,.98), rgba(248,250,252,.9)),
        var(--theme-panel, #ffffff);
    border: 1px solid rgba(199,213,232,.9);
    border-left: 4px solid var(--theme-blue, #1ca0f1);
    border-radius: 18px;
    padding: 18px 22px;
    margin: 14px 0;
    font-size: 0.96em;
    line-height: 1.7;
}
.sent-verdict em {
    color: var(--theme-blue, #1ca0f1);
    font-style: normal;
    font-weight: 600;
}
.sent-bar-wrap {
    height: 10px;
    border-radius: 5px;
    background: var(--theme-line, rgba(255,255,255,.14));
    margin: 8px 0 12px;
    overflow: hidden;
    display: flex;
}
.sent-bar-pos { background: var(--theme-green, #37c78a); height: 100%; }
.sent-bar-neu { background: var(--theme-muted, rgba(255,255,255,.68)); height: 100%; }
.sent-bar-neg { background: var(--theme-red, #ff7369); height: 100%; }
.review-row {
    border-top: 1px solid var(--theme-line, rgba(255,255,255,.14));
    padding: 12px 0;
}
.review-row:first-child { border-top: none; }
.review-text {
    color: var(--theme-muted, rgba(255,255,255,.68));
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
    padding: 18px;
}
.sent-col-a { border-left: 4px solid var(--theme-blue, #1ca0f1); }
.sent-col-b { border-left: 4px solid var(--theme-amber, #dfab01); }
.sent-col-title {
    font-size: 1.15em;
    font-weight: 700;
    color: var(--theme-blue, #1ca0f1);
    margin-bottom: 4px;
}
.sent-col-b .sent-col-title { color: var(--theme-amber, #dfab01); }
.sent-compare-summary {
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
.sent-winner-a { background: rgba(28,160,241,0.2); color: var(--theme-blue, #1ca0f1); }
.sent-winner-b { background: rgba(223,171,1,0.2); color: var(--theme-amber, #dfab01); }
.sent-stat-row {
    display: flex;
    justify-content: center;
    gap: 30px;
    margin: 8px 0;
    font-size: 0.9em;
}
.sent-stat-item { text-align: center; }
.sent-stat-val { font-size: 1.3em; font-weight: 700; }
.sent-stat-label { color: var(--theme-muted, rgba(255,255,255,.68)); font-size: 0.85em; }
@media (max-width: 900px) {
    .sent-compare { flex-direction: column; }
    .sent-toolbar-row { flex-direction: column !important; justify-content: stretch !important; }
    .sent-toolbar-row > * { width: 100% !important; }
    #sentiment-tab .sent-refresh-btn button,
    #sentiment-tab .sent-action-btn button,
    #sentiment-tab .sent-primary-action button { width: 100% !important; }
}
"""

# Global cache
_review_indexes: dict[str, dict[str, list]] = {}
_sentiment_cache: dict[tuple[str, str], ProductSentiment] = {}
_name_to_ids: dict[str, dict[str, str]] = {}
_domain_maps: dict[str, dict[str, str]] = {}
_metadata_maps: dict[str, dict[str, dict[str, str]]] = {}


def _normalize_source(source: str | None) -> str:
    return "amazon" if (source or "").lower().startswith("amazon") else "yelp"


def _ensure_index(source: str = "yelp"):
    """Load reviews from pipeline and index by product_id."""
    source = _normalize_source(source)
    if source in _review_indexes:
        return
    reviews = get_amazon_reviews() if source == "amazon" else get_reviews()
    _domain_maps[source] = get_business_domains(source)
    _metadata_maps[source] = get_product_metadata(source)
    _review_indexes[source] = defaultdict(list)
    for r in reviews:
        _review_indexes[source][r.product_id].append(r)


def _get_category_choices(source: str = "yelp") -> list[str]:
    """Return sorted list of source-specific category choices."""
    source = _normalize_source(source)
    _ensure_index(source)
    metadata = _metadata_maps[source]
    key = "category" if source == "amazon" else "subcategory"
    return sorted({values.get(key, "") for values in metadata.values() if values.get(key, "")})


def _get_subcategory_choices(source: str, category: str | None) -> list[str]:
    source = _normalize_source(source)
    _ensure_index(source)
    if source != "amazon":
        return []
    metadata = _metadata_maps[source]
    return sorted({
        values.get("subcategory", "")
        for values in metadata.values()
        if values.get("subcategory", "") and (not category or values.get("category") == category)
    })


def _filter_products(source: str, category: str | None, subcategory: str | None = None) -> list[str]:
    """Return product/business names for selected source filters."""
    source = _normalize_source(source)
    _ensure_index(source)
    name_to_id: dict[str, str] = {}
    metadata = _metadata_maps[source]
    category = "" if category in (None, "— All Categories —", "— All Business Types —") else category
    subcategory = "" if subcategory in (None, "— All Subcategories —") else subcategory

    for pid, revs in _review_indexes[source].items():
        values = metadata.get(pid, {})
        if source == "amazon":
            if category and values.get("category") != category:
                continue
            if subcategory and values.get("subcategory") != subcategory:
                continue
        elif category and values.get("subcategory") != category:
            continue
        name_to_id[revs[0].title] = pid

    _name_to_ids[source] = name_to_id
    return sorted(name_to_id.keys())


def _get_or_analyze(selection: str, source: str = "yelp") -> ProductSentiment | None:
    """Resolve a business name to its ProductSentiment, computing if needed."""
    source = _normalize_source(source)
    if not selection:
        return None
    _ensure_index(source)
    if source not in _name_to_ids or not _name_to_ids[source]:
        _filter_products(source, None, None)
    product_id = _name_to_ids[source].get(selection)
    if product_id is None:
        _filter_products(source, None, None)
        product_id = _name_to_ids[source].get(selection)
        if product_id is None:
            return None
    cache_key = (source, product_id)
    if cache_key not in _sentiment_cache:
        reviews = _review_indexes[source].get(product_id, [])
        if not reviews:
            return None
        _sentiment_cache[cache_key] = build_product_sentiment(reviews)
    return _sentiment_cache[cache_key]


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


def _analyze_product(selection: str, source: str = "Yelp") -> str:
    """Run sentiment analysis for the selected business (by name), return HTML."""
    if not selection:
        source_key = _normalize_source(source)
        noun = "Amazon product" if source_key == "amazon" else "Yelp business"
        return f"""
        <div class='sent-card' style='border-left:4px solid var(--theme-amber,#dfab01)'>
            <strong>Select a {noun} first.</strong><br>
            <span style='color:var(--theme-muted,#667085)'>
                Choose an item from the dropdown before running sentiment analysis.
            </span>
        </div>
        """
    source_key = _normalize_source(source)
    ps = _get_or_analyze(selection, source_key)
    if ps is None:
        return "<p style='color:var(--theme-red,#ff7369)'>Business not found.</p>"

    card = _render_product_card(ps, max_reviews=10)
    return f"""
    <div id='sentiment-tab' style='padding:20px'>
        <h2>📊 {ps.product_title}</h2>
        <h4 style='color:var(--theme-muted,rgba(255,255,255,.68));margin-top:-8px'>
            {_metadata_label(source_key, ps.product_id)}
        </h4>
        {card}
    </div>
    """


def _metadata_label(source: str, product_id: str) -> str:
    metadata = _metadata_maps.get(source, {}).get(product_id, {})
    if source == "amazon":
        category = metadata.get("category", "")
        subcategory = metadata.get("subcategory", "")
        return " / ".join(part for part in (category, subcategory) if part)
    return metadata.get("subcategory", _domain_maps.get(source, {}).get(product_id, ""))


def _compare_products(sel_a: str, sel_b: str, source: str = "Yelp") -> str:
    """Render side-by-side comparison of two businesses."""
    if not sel_a or not sel_b:
        return """
        <div class='sent-card' style='border-left:4px solid var(--theme-amber,#dfab01)'>
            <strong>Select two Yelp businesses first.</strong><br>
            <span style='color:var(--theme-muted,#667085)'>
                Choose Selection A and Selection B before comparing sentiment.
            </span>
        </div>
        """
    if sel_a == sel_b:
        return "<p style='color:var(--theme-red,#ff7369)'>Please select two different businesses to compare.</p>"

    source_key = _normalize_source(source)
    ps_a = _get_or_analyze(sel_a, source_key)
    ps_b = _get_or_analyze(sel_b, source_key)
    if ps_a is None or ps_b is None:
        missing = sel_a if ps_a is None else sel_b
        return f"<p style='color:var(--theme-red,#ff7369)'>Business not found: {missing}</p>"

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
            <div class='sent-stat-item' style='color:var(--theme-blue,#1ca0f1)'>
                <div class='sent-stat-val'>{ps_a.avg_rating:.1f}⭐</div>
                <div class='sent-stat-label'>{ps_a.product_title[:20]}</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:var(--theme-muted)'>vs</div>
                <div class='sent-stat-label'>&nbsp;</div>
            </div>
            <div class='sent-stat-item' style='color:var(--theme-amber,#dfab01)'>
                <div class='sent-stat-val'>{ps_b.avg_rating:.1f}⭐</div>
                <div class='sent-stat-label'>{ps_b.product_title[:20]}</div>
            </div>
        </div>
        <div class='sent-stat-row'>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:var(--theme-green,#37c78a)'>{ps_a.positive_pct:.0%}</div>
                <div class='sent-stat-label'>Positive</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:var(--theme-red,#ff7369)'>{ps_a.negative_pct:.0%}</div>
                <div class='sent-stat-label'>Negative</div>
            </div>
            <div class='sent-stat-item' style='opacity:0.5'>
                <div class='sent-stat-val'>{ps_a.total_reviews}</div>
                <div class='sent-stat-label'>Reviews</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:var(--theme-green,#37c78a)'>{ps_b.positive_pct:.0%}</div>
                <div class='sent-stat-label'>Positive</div>
            </div>
            <div class='sent-stat-item'>
                <div class='sent-stat-val' style='color:var(--theme-red,#ff7369)'>{ps_b.negative_pct:.0%}</div>
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
                    {_metadata_label(source_key, ps_a.product_id)} &nbsp;|&nbsp; ⭐{ps_a.avg_rating:.1f} &nbsp;|&nbsp; {ps_a.total_reviews} reviews
                </div>
                {card_a}
            </div>
            <div class='sent-col sent-col-b'>
                <div class='sent-col-title'>📊 {ps_b.product_title}</div>
                <div style='color:var(--theme-muted);font-size:.85em;margin-bottom:12px'>
                    {_metadata_label(source_key, ps_b.product_id)} &nbsp;|&nbsp; ⭐{ps_b.avg_rating:.1f} &nbsp;|&nbsp; {ps_b.total_reviews} reviews
                </div>
                {card_b}
            </div>
        </div>
    </div>
    """


def _dropdown_specs(source: str) -> tuple[dict, dict, dict, dict]:
    """Return source-specific dropdown state without creating Gradio components."""
    source_key = _normalize_source(source)
    category_label = "— All Categories —" if source_key == "amazon" else "— All Business Types —"
    category_choices = [category_label] + _get_category_choices(source_key)
    subcategory_choices = ["— All Subcategories —"] + _get_subcategory_choices(source_key, None)
    product_choices = _filter_products(source_key, "", "")
    category_name = "2. Product Category" if source_key == "amazon" else "2. Business Type"
    subcategory_name = "3. Product Subcategory"
    cat_info = "Electronics review category" if source_key == "amazon" else "Restaurant and local business type"
    sub_info = "Optional Electronics subcategory filter"
    product_info = "Type to search within the selected review source"
    product_a_label = "4. Amazon Product" if source_key == "amazon" else "4. Selection A"
    return (
        {"choices": category_choices, "value": category_label, "label": category_name, "info": cat_info},
        {
            "choices": subcategory_choices,
            "value": "— All Subcategories —" if source_key == "amazon" else None,
            "label": subcategory_name,
            "interactive": source_key == "amazon",
            "visible": source_key == "amazon",
            "info": sub_info,
        },
        {"choices": product_choices, "value": None, "label": product_a_label, "info": product_info},
        {
            "choices": product_choices,
            "value": None,
            "label": "5. Selection B",
            "info": "Yelp comparison only." if source_key == "amazon" else product_info,
            "visible": source_key != "amazon",
        },
    )


def _init_dropdowns(source: str) -> tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown, gr.Dropdown]:
    """Lazy-load dropdown choices for event updates."""
    category, subcategory, product_a, product_b = _dropdown_specs(source)
    return (
        gr.Dropdown(**category),
        gr.Dropdown(**subcategory),
        gr.Dropdown(**product_a),
        gr.Dropdown(**product_b),
    )


def render_sentiment_tab() -> gr.Blocks:
    """Build and return the Product Review Sentiment Analyzer Gradio tab."""
    with gr.Blocks(elem_id="sentiment-tab") as tab:
        gr.Markdown("""
        # Review Sentiment Intelligence
        Analyze Amazon Electronics product reviews by default, or switch to
        Yelp-style local business reviews for side-by-side comparison.
        """)

        with gr.Group(elem_classes=["sent-control-panel"]):
            gr.Markdown("""
            <div class="sent-dataset-note">
                Amazon uses a deployable 1,000-product Electronics review sample.
                Yelp uses the existing local 1,000-business sample and supports comparison.
            </div>
            """)
            dataset_dd = gr.Dropdown(
                choices=["Yelp Style", "Amazon Style"],
                value="Amazon Style",
                label="1. Review Dataset",
                info="Choose local business reviews or Amazon product reviews.",
            )

            initial_category, initial_subcategory, initial_product_a, initial_product_b = _dropdown_specs("Amazon Style")

            with gr.Row():
                category_dd = gr.Dropdown(
                    **initial_category,
                    filterable=True,
                    elem_id="sent-category-dropdown",
                )
                subcategory_dd = gr.Dropdown(
                    **initial_subcategory,
                    filterable=True,
                    elem_id="sent-subcategory-dropdown",
                )

            with gr.Row():
                business_a_dd = gr.Dropdown(
                    **initial_product_a,
                    filterable=True,
                    scale=3,
                    elem_id="sent-business-a-dropdown",
                )
                business_b_dd = gr.Dropdown(
                    **initial_product_b,
                    filterable=True,
                    scale=3,
                    elem_id="sent-business-b-dropdown",
                )

        with gr.Group(elem_classes=["sent-toolbar"]):
            with gr.Row(elem_classes=["sent-toolbar-row"]):
                analyze_a_btn = gr.Button(
                    "Analyze Product",
                    variant="primary",
                    scale=0,
                    min_width=172,
                    elem_classes=["sent-action-btn"],
                )
                compare_btn = gr.Button(
                    "Compare Yelp Businesses",
                    variant="secondary",
                    scale=0,
                    min_width=236,
                    visible=False,
                    elem_classes=["sent-primary-action"],
                )
                analyze_b_btn = gr.Button(
                    "Analyze B",
                    variant="secondary",
                    scale=0,
                    min_width=148,
                    visible=False,
                    elem_classes=["sent-action-btn"],
                )
                load_btn = gr.Button(
                    "Refresh Catalog",
                    variant="secondary",
                    scale=0,
                    min_width=136,
                    elem_classes=["sent-refresh-btn"],
                )

        analyze_output = gr.HTML()

        load_btn.click(
            fn=_init_dropdowns,
            inputs=[dataset_dd],
            outputs=[category_dd, subcategory_dd, business_a_dd, business_b_dd],
            show_progress="minimal",
        )

        def _mode_updates(source: str) -> tuple[gr.Button, gr.Button, gr.Button]:
            source_key = _normalize_source(source)
            if source_key == "amazon":
                return (
                    gr.Button("Analyze Product", variant="primary", elem_classes=["sent-action-btn"], scale=0, min_width=172),
                    gr.Button(visible=False, elem_classes=["sent-primary-action"], scale=0, min_width=236),
                    gr.Button(visible=False, elem_classes=["sent-action-btn"], scale=0, min_width=148),
                )
            return (
                gr.Button("Analyze A", variant="secondary", elem_classes=["sent-action-btn"], scale=0, min_width=148),
                gr.Button("Compare Yelp Businesses", variant="primary", visible=True, elem_classes=["sent-primary-action"], scale=0, min_width=236),
                gr.Button("Analyze B", variant="secondary", visible=True, elem_classes=["sent-action-btn"], scale=0, min_width=148),
            )

        def _on_dataset_change(source: str) -> tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown, gr.Dropdown, gr.Button, gr.Button, gr.Button, str]:
            category, subcategory, product_a, product_b = _init_dropdowns(source)
            analyze_a_mode, compare_mode, analyze_b_mode = _mode_updates(source)
            source_key = _normalize_source(source)
            label = "Amazon Electronics products" if source_key == "amazon" else "Yelp businesses"
            return (
                category,
                subcategory,
                product_a,
                product_b,
                analyze_a_mode,
                compare_mode,
                analyze_b_mode,
                f"<div class='sent-card'><strong>{label} loaded.</strong> Use the filters above to narrow the catalog.</div>",
            )

        dataset_dd.change(
            fn=_on_dataset_change,
            inputs=[dataset_dd],
            outputs=[
                category_dd,
                subcategory_dd,
                business_a_dd,
                business_b_dd,
                analyze_a_btn,
                compare_btn,
                analyze_b_btn,
                analyze_output,
            ],
            show_progress="minimal",
        )

        def _on_category_change(source: str, category: str) -> tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown]:
            source_key = _normalize_source(source)
            clean_category = "" if category in (None, "— All Categories —") else category
            sub_choices = _get_subcategory_choices(source_key, clean_category)
            products = _filter_products(source_key, category, "")
            return (
                gr.Dropdown(
                    choices=["— All Subcategories —"] + sub_choices,
                    value="— All Subcategories —" if source_key == "amazon" else None,
                    label="3. Product Subcategory",
                    interactive=source_key == "amazon",
                    visible=source_key == "amazon",
                    info="Optional Electronics subcategory filter",
                ),
                gr.Dropdown(choices=products, value=None),
                gr.Dropdown(choices=products, value=None, visible=source_key != "amazon"),
            )

        category_dd.change(
            fn=_on_category_change,
            inputs=[dataset_dd, category_dd],
            outputs=[subcategory_dd, business_a_dd, business_b_dd],
            show_progress="minimal",
        )

        def _on_subcategory_change(source: str, category: str, subcategory: str) -> tuple[gr.Dropdown, gr.Dropdown]:
            source_key = _normalize_source(source)
            products = _filter_products(source_key, category, subcategory)
            return (
                gr.Dropdown(choices=products, value=None),
                gr.Dropdown(choices=products, value=None, visible=source_key != "amazon"),
            )

        subcategory_dd.change(
            fn=_on_subcategory_change,
            inputs=[dataset_dd, category_dd, subcategory_dd],
            outputs=[business_a_dd, business_b_dd],
            show_progress="minimal",
        )

        analyze_a_btn.click(
            fn=_analyze_product,
            inputs=[business_a_dd, dataset_dd],
            outputs=[analyze_output],
            show_progress="minimal",
        )

        business_a_dd.change(
            fn=lambda selection: (
                '<div class="sent-loading"><div class="sent-spinner"></div>Analyzing reviews…<br><small>First model inference may take a few seconds</small></div>'
                if selection else ""
            ),
            inputs=[business_a_dd],
            outputs=[analyze_output],
        ).then(
            fn=_analyze_product,
            inputs=[business_a_dd, dataset_dd],
            outputs=[analyze_output],
        )

        analyze_b_btn.click(
            fn=_analyze_product,
            inputs=[business_b_dd, dataset_dd],
            outputs=[analyze_output],
            show_progress="minimal",
        )

        business_b_dd.change(
            fn=lambda selection: (
                '<div class="sent-loading"><div class="sent-spinner"></div>Analyzing reviews…<br><small>First model inference may take a few seconds</small></div>'
                if selection else ""
            ),
            inputs=[business_b_dd],
            outputs=[analyze_output],
        ).then(
            fn=_analyze_product,
            inputs=[business_b_dd, dataset_dd],
            outputs=[analyze_output],
        )

        compare_btn.click(
            fn=lambda: '<div class="sent-loading"><div class="sent-spinner"></div>Comparing selections…<br><small>First model inference may take a few seconds</small></div>',
            outputs=[analyze_output],
        ).then(
            fn=_compare_products,
            inputs=[business_a_dd, business_b_dd, dataset_dd],
            outputs=[analyze_output],
        )

    return tab
