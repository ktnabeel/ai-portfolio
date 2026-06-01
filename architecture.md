# Movie Recommendation System — Architecture

> This document covers the **movie recommender** subsystem only. The repo hosts several other systems:
> - **Financial Agent** — see `portfolio/financial/` (5 specialized agents + `DecisionOrchestrator`)
> - **Trading** — see `portfolio/trading/docs/README.md`, `ARCHITECTURE.md`, `FLOWS.md` for the LangGraph trading workflow, hoverable pipeline audit UI, human review gate, and MCP paper execution
> - **TradingAgents Manager** — see `portfolio/trading_agents_manager/` (FastAPI + LangGraph portfolio manager)
> - **Sentiment Analyzer** — see `portfolio/sentiment/`
> - **Claim Processing** — see `portfolio/claim_processing/`
> - **Insurance Underwriting Agent** — see `portfolio/underwriting/` (4-dimension risk assessment agent)
> - **Financial Agent** — see `portfolio/financial/` (5 specialized agents + `DecisionOrchestrator`)

## High-Level Overview

The movie recommender combines three recommendation approaches into a single ensemble:

```
User Query (natural language)
         │
         ▼
┌─────────────────────┐
│  PreferenceParser   │  ← LLM-style NLP (regex + keyword heuristics)
│  extracts: genres,  │
│  actors, directors, │
│  mood, year range,  │
│  min rating, etc.   │
└────────┬────────────┘
         │ UserPreference
         ▼
┌─────────────────────────────────────────────────┐
│              Ensemble Recommender                │
│                                                  │
│  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ Two-Tower Scorer │  │ Collaborative Filter │ │
│  │   (50% weight)   │  │    (35% weight)      │ │
│  │                  │  │                      │ │
│  │ Movie Tower      │  │ SVD on pseudo-       │ │
│  │  ├─ Genre one-hot│  │ ratings matrix:      │ │
│  │  ├─ TF-IDF text  │  │  archetypes × movies │ │
│  │  ├─ Year         │  │  → latent factors    │ │
│  │  ├─ Rating       │  │  → cosine similarity │ │
│  │  └─ Popularity   │  │                      │ │
│  │                  │  │                      │ │
│  │ User Tower       │  │                      │ │
│  │  (same dims)     │  │                      │ │
│  │                  │  │                      │ │
│  │ Cosine Similarity│  │                      │ │
│  └──────────────────┘  └──────────────────────┘ │
│                                                  │
│         + Popularity Boost (15% weight)          │
│                                                  │
│         → Top-K Recommendations                  │
└─────────────────────────────────────────────────┘
```

## Component Details

### 1. Preference Parser (`preference_parser.py`)

Simulates LLM-style parsing without requiring an API key. Swappable with a real LLM call.

**Extraction capabilities:**
- **Genres**: 19 genre categories via keyword matching (e.g., "sci-fi" → Science Fiction)
- **Negation**: Detects "not horror", "no comedy", "dislike romance"
- **People**: Matches known actor/director names + regex for "directed by X", "starring X"
- **Keywords**: Thematic tags (space, heist, coming-of-age, dystopian, etc.)
- **Year range**: "90s", "2000s", "recent", "classic", "after 2010", "between 2000 and 2010"
- **Rating**: "rated above 7", "at least 8/10", "highly rated"
- **Mood**: dark, light, thrilling, inspiring, thoughtful, scary

### 2. Two-Tower Embedding Model (`embeddings.py`)

**Movie Tower** (`MovieEmbedder`):
- Genre one-hot encoding (19 dims)
- TF-IDF of overview + keywords (500 dims, fitted on corpus)
- Normalized scalars: year (0–1), rating (0–1), log-popularity (0–1), tagline flag
- Total: ~523 dimensions

**User Tower** (`UserEmbedder`):
- Same vector structure as movies
- Liked genres → +1, disliked genres → -0.3
- User keywords + actor/director names encoded via same TF-IDF
- Year center from range, rating threshold

**Scoring** (`TwoTowerScorer`):
- Cosine similarity between user vector and all movie vectors
- Post-processing boosts: +0.15 for actor match, +0.20 for director match
- Post-processing penalties: -0.30 for disliked genres, -0.10 for year mismatch, -0.15 for rating below threshold
- Final score scaled to [0, 1]

### 3. Collaborative Filtering (`collaborative.py`)

Uses SVD (TruncatedSVD) on a simulated ratings matrix since real user ratings aren't available.

**Pseudo-ratings construction:**
- 13 genre-based archetypes act as pseudo-users
- Each archetype "rates" movies based on genre match + popularity
- Direct genre match: `vote_average * (0.7 + 0.3 * popularity_weight)`
- No match: `vote_average * 0.3 * popularity_weight`
- Matrix is zero-centered before SVD

**Recommendation:**
- User embedding = average of SVD latent vectors for movies matching liked genres
- Cosine similarity against all indexed movie embeddings
- Scaled to [0, 1]

### 4. Ensemble Recommender (`recommender.py`)

```
final_score = 0.50 * content_score + 0.35 * collaborative_score + 0.15 * popularity_score
```

Weights are configurable per query. Explanations are generated for each recommendation based on which component contributed most.

### 5. Data Pipeline (`pipeline.py`)

**Live mode** (TMDB API key set):
1. Fetch popular movies (configurable pages)
2. Fetch top-rated movies
3. Discover across 9 genre batches for diversity
4. Deduplicate by `tmdb_id`
5. Enrich each movie: full credits (cast + crew), keywords, detailed metadata
6. Collect known actor/director names for the preference parser

**Sample mode** (no API key):
- 15 hand-curated popular movies with real TMDB backdrop/poster CDN paths
- Covers all major genres and directors
- Images display without an API key via TMDB's public CDN

### 6. TMDB Client (`tmdb_client.py`)

- Rate-limited (~4 req/s) to respect TMDB's fair use policy
- Session-based HTTP connection pooling
- Endpoints: `/movie/popular`, `/movie/top_rated`, `/discover/movie`, `/movie/{id}`, `/movie/{id}/credits`, `/movie/{id}/keywords`
- Genre ID → name mapping cached in memory

## Data Flow

```
TMDB API (or sample data)
        │
        ▼
  MoviePipeline.run()
        │
        ▼
  list[Movie] (15–200+ movies)
        │
        ▼
  MovieRecommender.index()
  ├─ MovieEmbedder.fit() → TF-IDF vocabulary
  ├─ TwoTowerScorer.index_movies() → pre-computed movie embeddings
  ├─ CollaborativeFilter.fit() → SVD latent factors
  └─ PreferenceParser.update_known_people() → actor/director names
        │
        ▼
  MovieRecommender.recommend(query)
  ├─ PreferenceParser.parse(query) → UserPreference
  ├─ TwoTowerScorer.score(pref) → content scores
  ├─ CollaborativeFilter.score(pref) → collaborative scores
  └─ Ensemble → top-k RecommendationResult[]
        │
        ▼
  render.py → HTML cards with backdrop images, score bars, preference chips
```

## UI Rendering (`render.py`)

- Gradio `gr.Blocks` tab with `gr.Textbox` + `gr.Slider` + `gr.Button` + `gr.HTML`
- Movie cards: backdrop images with gradient overlay for text readability
- Score bars: animated gradient fill (green → blue)
- Preference chips: parsed genres, actors, directors, keywords, mood, year, rating
- Stats bar: movies indexed, recommendations count, method breakdown
- Example queries shown below the search UI
- All HTML escaped to prevent XSS
