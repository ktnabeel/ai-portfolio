"""Ensemble recommender combining two-tower, collaborative, and LLM approaches."""

from .models import Movie, RecommendationResponse, RecommendationResult, UserPreference
from .embeddings import MovieEmbedder, TwoTowerScorer
from .collaborative import CollaborativeFilter
from .preference_parser import PreferenceParser

ENSEMBLE_WEIGHTS = {
    "content": 0.50,       # two-tower similarity
    "collaborative": 0.35, # SVD collaborative filtering
    "popularity": 0.15,    # TMDB popularity boost
}


class MovieRecommender:
    """End-to-end movie recommendation engine.

    Pipeline:
      1. Parse natural language → UserPreference (LLM-style parser)
      2. Score all movies via two-tower (content-based) model
      3. Score all movies via collaborative filtering (SVD)
      4. Ensemble scores with popularity boost
      5. Return top-k with explanations

    Usage:
        rec = MovieRecommender()
        rec.index(movies)
        result = rec.recommend("I love dark sci-fi movies like Inception, directed by Christopher Nolan")
    """

    def __init__(self):
        """Initialize the ensemble recommender.

        Components are lazy — call index(movies) to build
        the two-tower embedder and collaborative filtering model.
        """
        self.movies: list[Movie] = []
        self.parser = PreferenceParser()
        self.content_scorer: TwoTowerScorer | None = None
        self.cf_model = CollaborativeFilter()
        self._indexed = False

    def index(self, movies: list[Movie]):
        """Index a collection of movies for recommendation.

        Trains the two-tower embedder and collaborative filtering model.
        """
        self.movies = movies

        # Collect known people for preference parser
        all_names: set[str] = set()
        for m in movies:
            for a in m.actors:
                all_names.add(a.name)
            for d in m.directors:
                all_names.add(d.name)
        self.parser.update_known_people(all_names)

        # Train content-based embedder
        embedder = MovieEmbedder()
        embedder.fit(movies)
        self.content_scorer = TwoTowerScorer(embedder)
        self.content_scorer.index_movies(movies)

        # Train collaborative filtering
        self.cf_model.fit(movies)

        self._indexed = True

    def recommend(
        self,
        query: str,
        top_k: int = 10,
        weights: dict[str, float] | None = None,
    ) -> RecommendationResponse:
        """Recommend movies based on natural language query.

        Args:
            query: Natural language like "dark sci-fi movies like Inception directed by Nolan"
            top_k: Number of recommendations to return
            weights: Optional ensemble weights override
        """
        if not self._indexed:
            raise RuntimeError("No movies indexed. Call index() first.")

        w = weights or ENSEMBLE_WEIGHTS

        # Step 1 — Parse preferences
        pref = self.parser.parse(query)

        # Step 2 — Content-based scoring
        content_results = self.content_scorer.score(pref, top_k=len(self.movies))
        content_map = {movie.tmdb_id: score for movie, score in content_results}

        # Step 3 — Collaborative filtering scoring
        cf_results = self.cf_model.score(pref, top_k=len(self.movies))
        cf_map = {movie.tmdb_id: score for movie, score in cf_results}

        # Step 4 — Ensemble
        max_pop = max((m.popularity for m in self.movies), default=1.0)
        results: list[RecommendationResult] = []

        for movie in self.movies:
            content_score = content_map.get(movie.tmdb_id, 0.0)
            cf_score = cf_map.get(movie.tmdb_id, 0.0)
            pop_score = min(1.0, movie.popularity / max_pop) if max_pop > 0 else 0.0

            final = (
                w["content"] * content_score +
                w["collaborative"] * cf_score +
                w["popularity"] * pop_score
            )

            # Build explanation
            parts = []
            if content_score > 0.6:
                parts.append("strong content match")
            elif content_score > 0.4:
                parts.append("decent content match")
            if cf_score > 0.6:
                parts.append("high collaborative affinity")
            elif cf_score > 0.4:
                parts.append("moderate collaborative fit")
            if movie.year >= pref.year_range[0] and movie.year <= pref.year_range[1]:
                pass  # in range
            else:
                parts.append("outside preferred years")
            if movie.vote_average >= 7.5:
                parts.append("highly rated")
            if not parts:
                parts.append("general recommendation")

            results.append(RecommendationResult(
                movie=movie,
                content_score=round(content_score, 3),
                collaborative_score=round(cf_score, 3),
                final_score=round(final, 3),
                explanation="; ".join(parts),
            ))

        # Sort by final score descending
        results.sort(key=lambda r: r.final_score, reverse=True)
        top = results[:top_k]

        return RecommendationResponse(
            preferences=pref,
            recommendations=top,
            total_movies_indexed=len(self.movies),
            method_breakdown=(
                f"Content-based ({w['content']:.0%}) + "
                f"Collaborative ({w['collaborative']:.0%}) + "
                f"Popularity ({w['popularity']:.0%})"
            ),
        )
