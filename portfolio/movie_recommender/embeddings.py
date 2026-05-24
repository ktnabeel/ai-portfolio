"""Two-tower embedding model for content-based movie recommendations.

Architecture:
  - Movie tower: encodes genre, overview (TF-IDF), actors, directors, year,
    rating, keywords into a dense feature vector.
  - User tower: encodes user preferences (genres, actors, directors, keywords,
    year range, rating preference) into the same vector space.
  - Similarity: cosine similarity between user and movie vectors.
"""

import math

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Movie, UserPreference

# All known genres for one-hot encoding
ALL_GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Documentary", "Drama", "Family", "Fantasy", "History",
    "Horror", "Music", "Mystery", "Romance", "Science Fiction",
    "Thriller", "War", "Western", "TV Movie",
]
GENRE_TO_INDEX = {g: i for i, g in enumerate(ALL_GENRES)}
NUM_GENRES = len(ALL_GENRES)


class MovieEmbedder:
    """Encodes movies into dense feature vectors (the movie tower)."""

    def __init__(self):
        """Initialize the movie tower with a TF-IDF vectorizer.

        The vectorizer is not fitted until fit() is called with a movie corpus.
        """
        self.tfidf = TfidfVectorizer(max_features=500, stop_words="english")
        self._fitted = False
        self._corpus: list[str] = []

    def fit(self, movies: list[Movie]):
        """Fit TF-IDF on movie overviews + keywords."""
        self._corpus = [
            (m.overview or "") + " " + " ".join(m.keywords)
            for m in movies
        ]
        self.tfidf.fit(self._corpus)
        self._fitted = True

    def encode(self, movie: Movie) -> np.ndarray:
        """Encode a single movie into a feature vector.

        Vector structure:
          [0:NUM_GENRES]        — genre one-hot
          [NUM_GENRES:500+NUM_GENRES] — TF-IDF overview
          [500+NUM_GENRES]      — normalized year
          [501+NUM_GENRES]      — normalized vote average
          [502+NUM_GENRES]      — normalized popularity
          [503+NUM_GENRES]      — has tagline flag
          Total: ~523 dims
        """
        if not self._fitted:
            raise RuntimeError("MovieEmbedder must be fit() before encode().")

        vecs = []

        # Genre one-hot
        genre_vec = np.zeros(NUM_GENRES)
        for g in movie.genres:
            idx = GENRE_TO_INDEX.get(g.value)
            if idx is not None:
                genre_vec[idx] = 1.0
        vecs.append(genre_vec)

        # TF-IDF of overview + keywords
        text = (movie.overview or "") + " " + " ".join(movie.keywords)
        tfidf_vec = self.tfidf.transform([text]).toarray()[0]
        vecs.append(tfidf_vec)

        # Normalized scalar features
        year_norm = max(0.0, min(1.0, (movie.year - 1900) / 130.0))
        rating_norm = movie.vote_average / 10.0
        popularity_norm = min(1.0, math.log1p(movie.popularity) / 10.0)
        tagline_flag = 1.0 if movie.tagline else 0.0

        vecs.append(np.array([year_norm, rating_norm, popularity_norm, tagline_flag]))

        return np.concatenate(vecs)

    def encode_batch(self, movies: list[Movie]) -> np.ndarray:
        """Encode a batch of movies into a feature matrix."""
        return np.stack([self.encode(m) for m in movies])


class UserEmbedder:
    """Encodes user preferences into the same vector space as movies."""

    def __init__(self, movie_embedder: MovieEmbedder):
        """Initialize the user tower, sharing the movie tower's TF-IDF vocabulary.

        Args:
            movie_embedder: A fitted MovieEmbedder whose TF-IDF vectorizer
                            is reused to encode user preference text.
        """
        self.movie_embedder = movie_embedder

    def encode(self, pref: UserPreference) -> np.ndarray:
        """Encode user preferences into the movie vector space.

        Uses the same TF-IDF vectorizer (fit on movie corpus) to encode
        the user's keyword/liked text as if it were a movie overview.
        """
        vecs = []

        # Genre one-hot (liked genres = 1, disliked = -0.3)
        genre_vec = np.zeros(NUM_GENRES)
        for g in pref.liked_genres:
            idx = GENRE_TO_INDEX.get(g)
            if idx is not None:
                genre_vec[idx] = 1.0
        for g in pref.disliked_genres:
            idx = GENRE_TO_INDEX.get(g)
            if idx is not None:
                genre_vec[idx] = -0.3
        vecs.append(genre_vec)

        # TF-IDF of user's keywords + actor/director names
        user_text = (
            " ".join(pref.keywords) + " " +
            " ".join(pref.liked_actors) + " " +
            " ".join(pref.liked_directors)
        )
        if user_text.strip():
            tfidf_vec = self.movie_embedder.tfidf.transform([user_text]).toarray()[0]
        else:
            tfidf_vec = np.zeros(len(self.movie_embedder.tfidf.get_feature_names_out()))
        vecs.append(tfidf_vec)

        # Normalized scalar preferences
        year_center = (pref.year_range[0] + pref.year_range[1]) / 2
        year_norm = max(0.0, min(1.0, (year_center - 1900) / 130.0))
        rating_norm = pref.min_rating / 10.0
        popularity_norm = 0.5  # neutral
        tagline_flag = 0.0

        vecs.append(np.array([year_norm, rating_norm, popularity_norm, tagline_flag]))

        return np.concatenate(vecs)


class TwoTowerScorer:
    """Computes cosine similarity between user preferences and movies."""

    def __init__(self, movie_embedder: MovieEmbedder):
        """Initialize the two-tower scorer.

        Args:
            movie_embedder: A fitted MovieEmbedder used for both encoding
                            movies and (via UserEmbedder) user preferences.
        """
        self.movie_embedder = movie_embedder
        self.user_embedder = UserEmbedder(movie_embedder)
        self._movie_matrix: np.ndarray | None = None
        self._movies: list[Movie] = []

    def index_movies(self, movies: list[Movie]):
        """Pre-compute movie embeddings for fast scoring."""
        self._movies = movies
        self._movie_matrix = self.movie_embedder.encode_batch(movies)

    def score(self, pref: UserPreference, top_k: int = 10) -> list[tuple[Movie, float]]:
        """Score all indexed movies against user preferences.

        Returns top_k (movie, score) pairs sorted by descending similarity.
        Also applies hard filters for disliked genres.
        """
        if self._movie_matrix is None or not self._movies:
            return []

        user_vec = self.user_embedder.encode(pref).reshape(1, -1)
        similarities = cosine_similarity(user_vec, self._movie_matrix)[0]

        # Boost: +0.15 for matching liked actors/directors
        # Penalty: -0.30 for disliked genres
        results: list[tuple[Movie, float]] = []
        actor_set = {a.lower() for a in pref.liked_actors}
        director_set = {d.lower() for d in pref.liked_directors}
        disliked_set = {g.lower() for g in pref.disliked_genres}

        for i, movie in enumerate(self._movies):
            score = float(similarities[i])

            # Penalize disliked genres
            movie_genres_lower = {g.value.lower() for g in movie.genres}
            if movie_genres_lower & disliked_set:
                score -= 0.30

            # Boost for matching actors
            for a in movie.actors:
                if a.name.lower() in actor_set:
                    score += 0.15
                    break

            # Boost for matching directors
            for d in movie.directors:
                if d.name.lower() in director_set:
                    score += 0.20
                    break

            # Year range filter (soft)
            if pref.year_range[0] > 0 or pref.year_range[1] < 2030:
                if movie.year < pref.year_range[0] or movie.year > pref.year_range[1]:
                    score -= 0.10

            # Rating filter (soft)
            if movie.vote_average < pref.min_rating:
                score -= 0.15

            results.append((movie, max(0.0, min(1.0, (score + 1.0) / 2.0))))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
