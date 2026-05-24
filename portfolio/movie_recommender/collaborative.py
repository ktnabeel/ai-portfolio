"""Collaborative filtering via SVD matrix factorization.

Since we don't have real user ratings, we simulate a ratings matrix using:
  - TMDB vote_average as the base rating
  - Popularity-weighted confidence
  - Genre affinity as pseudo-user-item interactions
"""

import numpy as np
from sklearn.decomposition import TruncatedSVD

from .models import Movie, UserPreference


class CollaborativeFilter:
    """Lightweight collaborative filtering using SVD on a simulated ratings matrix.

    Constructs a pseudo user-item matrix where:
      - "Users" are genre-based archetypes (action-lover, drama-fan, etc.)
      - "Items" are movies
      - Ratings are simulated as: vote_average * genre_match * popularity_weight

    The SVD latent factors capture which movies are "similar" across
    these archetypes, enabling recommendation even when a user's exact
    genre combination hasn't been seen.
    """

    def __init__(self, n_components: int = 20):
        """Initialize the collaborative filtering model.

        Args:
            n_components: Number of latent dimensions for SVD factorization.
                          Reduced automatically if fewer movies are available.
        """
        self.n_components = n_components
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._movie_embeddings: np.ndarray | None = None
        self._movies: list[Movie] = []
        self._fitted = False

    def fit(self, movies: list[Movie]):
        """Build pseudo ratings matrix and fit SVD."""
        self._movies = movies
        if len(movies) < self.n_components:
            self.n_components = max(1, len(movies) // 2)

        # Define genre archetypes as pseudo-users
        archetypes = [
            "Action", "Comedy", "Drama", "Horror", "Science Fiction",
            "Thriller", "Romance", "Documentary", "Animation", "Fantasy",
            "Mystery", "Adventure", "Crime",
        ]

        # Build pseudo ratings matrix: archetypes × movies
        n_users = len(archetypes)
        n_items = len(movies)
        ratings = np.zeros((n_users, n_items))

        for j, movie in enumerate(movies):
            movie_genres = {g.value for g in movie.genres}
            base_rating = movie.vote_average
            pop_weight = min(1.0, np.log1p(movie.popularity) / 8.0)

            for i, archetype in enumerate(archetypes):
                if archetype in movie_genres:
                    # Direct genre match: high rating
                    ratings[i, j] = base_rating * (0.7 + 0.3 * pop_weight)
                else:
                    # No match: lower base, but popular movies still get some score
                    ratings[i, j] = base_rating * 0.3 * pop_weight

        # Zero-center
        row_means = ratings.mean(axis=1, keepdims=True)
        ratings_centered = ratings - row_means

        # Fit SVD
        self.svd = TruncatedSVD(n_components=self.n_components, random_state=42)
        self.svd.fit(ratings_centered)
        self._movie_embeddings = self.svd.components_.T  # (n_items, n_components)

        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(self._movie_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._movie_embeddings = self._movie_embeddings / norms

        self._fitted = True

    def score(self, pref: UserPreference, top_k: int = 10) -> list[tuple[Movie, float]]:
        """Score movies via collaborative filtering.

        Builds a user embedding by averaging the SVD latent vectors of
        movies matching the user's genre preferences, then computes
        cosine similarity against all indexed movies.
        """
        if not self._fitted or self._movie_embeddings is None:
            return []

        liked = {g.lower() for g in pref.liked_genres}

        # Build user embedding from movies matching liked genres
        matching_indices = []
        for i, movie in enumerate(self._movies):
            movie_genres = {g.value.lower() for g in movie.genres}
            if movie_genres & liked:
                matching_indices.append(i)

        if matching_indices:
            user_embedding = self._movie_embeddings[matching_indices].mean(axis=0)
        else:
            # No matching genres — use a uniform vector
            user_embedding = np.ones(self._movie_embeddings.shape[1]) * 0.3

        # Normalize
        norm = np.linalg.norm(user_embedding)
        if norm > 0:
            user_embedding = user_embedding / norm

        # Cosine similarity with all movie embeddings
        similarities = self._movie_embeddings @ user_embedding  # (n_items,)

        results: list[tuple[Movie, float]] = []
        for i, movie in enumerate(self._movies):
            score = float((similarities[i] + 1.0) / 2.0)  # scale to [0, 1]
            results.append((movie, max(0.0, min(1.0, score))))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
