"""AI-powered movie recommendation system.

Combines two-tower neural embeddings, collaborative filtering (SVD),
and LLM-style natural language preference extraction to deliver
personalized movie recommendations from TMDB data.
"""

from .models import (
    Genre,
    Movie,
    Person,
    UserPreference,
    RecommendationResult,
    RecommendationResponse,
)
from .tmdb_client import TMDBClient
from .pipeline import MoviePipeline
from .embeddings import MovieEmbedder, UserEmbedder, TwoTowerScorer
from .collaborative import CollaborativeFilter
from .preference_parser import PreferenceParser
from .recommender import MovieRecommender
from .render import render_movie_tab, MOVIE_CSS

__all__ = [
    # Models
    "Genre",
    "Movie",
    "Person",
    "UserPreference",
    "RecommendationResult",
    "RecommendationResponse",
    # Pipeline & Client
    "TMDBClient",
    "MoviePipeline",
    # ML Components
    "MovieEmbedder",
    "UserEmbedder",
    "TwoTowerScorer",
    "CollaborativeFilter",
    "PreferenceParser",
    # Recommender
    "MovieRecommender",
    # UI
    "render_movie_tab",
    "MOVIE_CSS",
]
