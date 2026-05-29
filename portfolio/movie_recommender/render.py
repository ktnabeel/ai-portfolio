"""Gradio UI rendering for the Movie Recommendations tab."""

import gradio as gr

from .recommender import MovieRecommender
from .pipeline import MoviePipeline
from .models import UserPreference

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


def _tmdb_image_url(path: str, size: str = "w780") -> str:
    """Resolve a TMDB image path to a full public CDN URL.

    TMDB images are publicly accessible without an API key.
    Sizes: w92, w154, w185, w342, w500, w780, w1280, original
    """
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/{size}/{path.lstrip('/')}"


MOVIE_CSS = """
#movie-tab {
    background:
        linear-gradient(180deg, rgba(255,255,255,.72), rgba(255,255,255,.92)),
        var(--theme-panel, #ffffff);
    border: 1px solid var(--theme-line, #d9e2ec);
    border-radius: 18px;
    box-shadow: 0 24px 70px var(--theme-shadow, rgba(16,24,40,.08));
    color: var(--theme-ink, rgba(255,255,255,.92));
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 24px;
}
#movie-tab h1, #movie-tab h2, #movie-tab h3 {
    color: var(--theme-blue, #1ca0f1);
}
#movie-tab .movie-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
}
#movie-tab .movie-card {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-radius: 16px;
    min-height: 260px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    transition: transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease, border-color .25s ease;
    background: var(--theme-panel, #373c3f);
}
#movie-tab .movie-card:hover {
    transform: translateY(-6px) scale(1.015);
    border-color: var(--theme-blue, #1ca0f1);
    box-shadow: 0 24px 58px var(--theme-shadow-hover, rgba(0,0,0,.40));
}
#movie-tab .movie-card-bg {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center top;
    background-repeat: no-repeat;
    z-index: 0;
}
#movie-tab .movie-card-bg::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
        180deg,
        rgba(0,0,0,0.15) 0%,
        rgba(0,0,0,0.55) 50%,
        rgba(0,0,0,0.92) 100%
    );
}
#movie-tab .movie-card-content {
    position: relative;
    z-index: 1;
    padding: 20px;
    padding-top: 60px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
}
#movie-tab .movie-card.has-bg .movie-title,
#movie-tab .movie-card.has-bg .movie-crew,
#movie-tab .movie-card.has-bg .movie-overview,
#movie-tab .movie-card.has-bg .explanation {
    color: rgba(255,255,255,.92);
    text-shadow: 0 1px 4px rgba(0,0,0,0.7);
}
#movie-tab .movie-card.has-bg .movie-crew strong {
    color: #9be7c8;
}
#movie-tab .movie-title {
    font-size: 20px;
    font-weight: 800;
    color: var(--theme-ink, rgba(255,255,255,.92));
    margin-bottom: 6px;
    line-height: 1.2;
}
#movie-tab .movie-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 10px;
}
#movie-tab .badge {
    display: inline-flex;
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
    color: var(--theme-muted, rgba(255,255,255,.68));
}
#movie-tab .badge-rating {
    background: var(--theme-amber, #dfab01);
    color: #000;
    border-color: var(--theme-amber, #dfab01);
}
#movie-tab .badge-year {
    background: var(--theme-green, #37c78a);
    color: #000;
    border-color: var(--theme-green, #37c78a);
}
#movie-tab .badge-score {
    background: var(--theme-blue, #1ca0f1);
    color: #000;
    border-color: var(--theme-blue, #1ca0f1);
}
#movie-tab .movie-overview {
    color: var(--theme-muted, rgba(255,255,255,.68));
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 12px;
}
#movie-tab .movie-crew {
    font-size: 13px;
    color: var(--theme-muted, rgba(255,255,255,.68));
    margin-bottom: 4px;
}
#movie-tab .movie-crew strong {
    color: var(--theme-green, #37c78a);
}
#movie-tab .movie-genres {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
}
#movie-tab .genre-tag {
    border-radius: 999px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
    background: var(--theme-tag-bg, #454b4e);
    color: var(--theme-tag-text, rgba(255,255,255,.86));
}
#movie-tab .score-bar {
    height: 6px;
    border-radius: 3px;
    background: var(--theme-line, rgba(255,255,255,.14));
    margin: 8px 0 4px;
    overflow: hidden;
}
#movie-tab .score-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--theme-green, #37c78a), var(--theme-blue, #1ca0f1));
    transition: width .4s ease;
}
#movie-tab .explanation {
    font-size: 12px;
    color: var(--theme-blue, #1ca0f1);
    font-style: italic;
    margin-top: 4px;
}
#movie-tab .stats-bar {
    display: flex;
    gap: 20px;
    margin: 16px 0;
    flex-wrap: wrap;
}
#movie-tab .stat-item {
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-radius: 14px;
    padding: 12px 18px;
    background: var(--theme-panel, #373c3f);
    text-align: center;
}
#movie-tab .stat-value {
    font-size: 24px;
    font-weight: 900;
    color: var(--theme-green, #37c78a);
}
#movie-tab .stat-label {
    font-size: 12px;
    color: var(--theme-muted, rgba(255,255,255,.68));
    text-transform: uppercase;
    font-weight: 700;
}
#movie-tab .pref-section {
    background: var(--theme-surface, #454b4e);
    border: 1px solid var(--theme-line, rgba(255,255,255,.14));
    border-radius: 16px;
    padding: 16px;
    margin: 16px 0;
}
#movie-tab .pref-title {
    font-weight: 800;
    color: var(--theme-blue, #1ca0f1);
    margin-bottom: 8px;
}
#movie-tab .pref-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
#movie-tab .pref-chip {
    border-radius: 999px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 700;
    background: var(--theme-blue, #1ca0f1);
    color: #000;
}
"""

# Singleton recommender (initialized lazily)
_recommender: MovieRecommender | None = None


def _get_recommender() -> MovieRecommender:
    """Lazy-init the recommender with sample data (or TMDB if key is set)."""
    global _recommender
    if _recommender is not None:
        return _recommender

    pipeline = MoviePipeline()
    try:
        if pipeline.client.is_configured:
            movies = pipeline.run(pages=3, enrich=True)
        else:
            movies = pipeline.run_sample()
    except Exception:
        movies = pipeline.run_sample()

    rec = MovieRecommender()
    rec.index(movies)
    _recommender = rec
    return _recommender


def _render_recommendations(query: str, top_k: int) -> str:
    """Process a recommendation query and return HTML."""
    if not query or not query.strip():
        return "<p style='color:var(--theme-red,#ff7369)'>Please describe what kind of movies you're looking for.</p>"

    try:
        rec = _get_recommender()
        result = rec.recommend(query, top_k=top_k)
    except Exception as e:
        return f"<p style='color:var(--theme-red,#ff7369)'>Error: {escape_html(str(e))}</p>"

    # Preferences section
    pref_html = _render_preferences(result.preferences)

    # Stats
    stats_html = f"""
    <div class='stats-bar'>
        <div class='stat-item'>
            <div class='stat-value'>{result.total_movies_indexed}</div>
            <div class='stat-label'>Movies Indexed</div>
        </div>
        <div class='stat-item'>
            <div class='stat-value'>{len(result.recommendations)}</div>
            <div class='stat-label'>Recommendations</div>
        </div>
        <div class='stat-item'>
            <div class='stat-value' style='font-size:14px'>{result.method_breakdown}</div>
            <div class='stat-label'>Method</div>
        </div>
    </div>
    """

    # Movie cards
    cards = ""
    for i, r in enumerate(result.recommendations):
        m = r.movie
        stars = "★" * max(1, round(m.vote_average / 2))
        director_names = ", ".join(d.name for d in m.directors[:2])
        actor_names = ", ".join(a.name for a in m.actors[:3])

        genres_html = "".join(
            f"<span class='genre-tag'>{g.value}</span>"
            for g in m.genres[:4]
        )

        score_pct = int(r.final_score * 100)

        # Build backdrop image if available
        backdrop_url = _tmdb_image_url(m.backdrop_path, "w780") or _tmdb_image_url(m.poster_path, "w780")
        has_bg_class = " has-bg" if backdrop_url else ""
        bg_div = f"<div class='movie-card-bg' style='background-image:url({escape_html(backdrop_url)})'></div>" if backdrop_url else ""

        cards += f"""
        <div class='movie-card{has_bg_class}'>
            {bg_div}
            <div class='movie-card-content'>
                <div class='movie-title'>#{i+1} {escape_html(m.title)}</div>
                <div class='movie-meta'>
                    <span class='badge badge-rating'>{stars} {m.vote_average:.1f}</span>
                    <span class='badge badge-year'>{m.year}</span>
                    <span class='badge badge-score'>Match {score_pct}%</span>
                </div>
                <div class='movie-overview'>{escape_html(m.overview[:200])}{'...' if len(m.overview) > 200 else ''}</div>
                <div class='score-bar'>
                    <div class='score-fill' style='width:{score_pct}%'></div>
                </div>
                <div class='movie-crew'>
                    <strong>Content:</strong> {r.content_score:.0%} &nbsp;
                    <strong>Collab:</strong> {r.collaborative_score:.0%}
                </div>
                <div class='explanation'>{escape_html(r.explanation)}</div>
                {f'<div class="movie-crew" style="margin-top:8px"><strong>Director:</strong> {escape_html(director_names)}</div>' if director_names else ''}
                {f'<div class="movie-crew"><strong>Cast:</strong> {escape_html(actor_names)}</div>' if actor_names else ''}
                <div class='movie-genres'>{genres_html}</div>
            </div>
        </div>
        """

    return f"""
    <div id='movie-tab'>
        {pref_html}
        {stats_html}
        <div class='movie-grid'>{cards}</div>
    </div>
    """


def _render_preferences(pref: UserPreference) -> str:
    """Render the extracted preferences as chips."""
    chips = ""

    if pref.liked_genres:
        chips += "".join(f"<span class='pref-chip'>{escape_html(g)}</span>" for g in pref.liked_genres[:6])
    if pref.liked_actors:
        chips += "".join(f"<span class='pref-chip'>🎭 {escape_html(a)}</span>" for a in pref.liked_actors[:3])
    if pref.liked_directors:
        chips += "".join(f"<span class='pref-chip'>🎬 {escape_html(d)}</span>" for d in pref.liked_directors[:3])
    if pref.keywords:
        chips += "".join(f"<span class='pref-chip'>🏷 {escape_html(k)}</span>" for k in pref.keywords[:5])
    if pref.mood:
        chips += f"<span class='pref-chip'>🎯 Mood: {escape_html(pref.mood)}</span>"
    if pref.min_rating > 0:
        chips += f"<span class='pref-chip'>⭐ ≥{pref.min_rating:.0f}/10</span>"
    if pref.year_range != (1900, 2030):
        chips += f"<span class='pref-chip'>📅 {pref.year_range[0]}–{pref.year_range[1]}</span>"
    if pref.disliked_genres:
        chips += "".join(f"<span class='pref-chip' style='background:var(--theme-red,#ff7369)'>🚫 {escape_html(g)}</span>" for g in pref.disliked_genres[:3])

    if not chips.strip():
        chips = "<span class='pref-chip'>No preferences detected — showing top picks</span>"

    return f"""
    <div class='pref-section'>
        <div class='pref-title'>🧠 Parsed Preferences</div>
        <div class='pref-chips'>{chips}</div>
    </div>
    """


def escape_html(text: str) -> str:
    """Escape special HTML characters to prevent XSS in rendered output."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_movie_tab() -> gr.Blocks:
    """Build and return the Movie Recommendations Gradio tab."""
    with gr.Blocks(elem_id="movie-tab") as tab:
        gr.Markdown("""
        # 🎬 AI Movie Recommendations
        Describe what you're in the mood for — genres, actors, directors, era, vibe — and get
        personalized picks powered by **two-tower neural embeddings**, **collaborative filtering**,
        and **LLM-style preference understanding**.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What kind of movie are you looking for?",
                placeholder="e.g. I want dark sci-fi movies like Inception and Interstellar, directed by Christopher Nolan, with mind-bending plots — nothing before 2005, rated 7.5+",
                lines=3,
                scale=4,
            )
            with gr.Column(scale=1, min_width=120):
                top_k = gr.Slider(
                    label="Results",
                    minimum=3,
                    maximum=20,
                    value=8,
                    step=1,
                )
                search_btn = gr.Button("🔍 Find Movies", variant="primary", size="lg")

        output = gr.HTML()

        search_btn.click(
            fn=_render_recommendations,
            inputs=[query_input, top_k],
            outputs=[output],
        )

        gr.Markdown("""
        ---
        ### 💡 Try these queries:
        - *"Feel-good animated movies for family movie night"*
        - *"Dark psychological thrillers like Fight Club, with a twist ending"*
        - *"Sci-fi epics from the 2010s directed by Christopher Nolan or Denis Villeneuve"*
        - *"Crime dramas with Al Pacino or Robert De Niro, similar to The Godfather"*
        - *"Inspiring true-story movies about overcoming adversity, rated above 8"*
        - *"Indie coming-of-age films from the 90s, not too dark"*
        """)

    return tab
