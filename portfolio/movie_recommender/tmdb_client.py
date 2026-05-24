"""TMDB API client for fetching movies, credits, and metadata."""

import os
import time
from typing import Optional

import requests

from .models import Genre, Movie, Person

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# In-memory genre cache
_GENRE_MAP: dict[int, str] = {}


class TMDBClient:
    """Rate-limited client for The Movie Database (TMDB) API.

    Requires TMDB_API_KEY environment variable or pass key to constructor.
    Get a free key at https://www.themoviedb.org/settings/api
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the TMDB client.

        Args:
            api_key: TMDB API key. If None, reads TMDB_API_KEY from environment.
        """
        self.api_key = api_key or os.environ.get("TMDB_API_KEY", "")
        self._last_request = 0.0
        self._min_interval = 0.25  # ~4 req/s to respect rate limits
        self._session = requests.Session()

    @property
    def is_configured(self) -> bool:
        """Whether a valid API key is available (can make live API calls)."""
        return bool(self.api_key)

    # ------------------------------------------------------------------
    # Genre helpers
    # ------------------------------------------------------------------

    def fetch_genres(self) -> dict[int, str]:
        """Fetch TMDB genre list (cached in memory)."""
        global _GENRE_MAP
        if _GENRE_MAP:
            return _GENRE_MAP
        data = self._get("/genre/movie/list")
        _GENRE_MAP = {g["id"]: g["name"] for g in data.get("genres", [])}
        return _GENRE_MAP

    # ------------------------------------------------------------------
    # Movie discovery
    # ------------------------------------------------------------------

    def fetch_popular_movies(self, pages: int = 5) -> list[Movie]:
        """Fetch popular movies across multiple pages."""
        movies: list[Movie] = []
        for page in range(1, pages + 1):
            data = self._get("/movie/popular", params={"page": page, "language": "en-US"})
            for item in data.get("results", []):
                movie = self._parse_movie_brief(item)
                movies.append(movie)
        return movies

    def fetch_top_rated_movies(self, pages: int = 3) -> list[Movie]:
        """Fetch top-rated movies."""
        movies: list[Movie] = []
        for page in range(1, pages + 1):
            data = self._get("/movie/top_rated", params={"page": page, "language": "en-US"})
            for item in data.get("results", []):
                movie = self._parse_movie_brief(item)
                movies.append(movie)
        return movies

    def discover_movies(
        self,
        genres: Optional[list[int]] = None,
        year_from: int = 2000,
        year_to: int = 2025,
        min_votes: int = 100,
        pages: int = 5,
    ) -> list[Movie]:
        """Discover movies by genre + year range using TMDB discover endpoint."""
        movies: list[Movie] = []
        for page in range(1, pages + 1):
            params: dict = {
                "page": page,
                "language": "en-US",
                "sort_by": "popularity.desc",
                "primary_release_date.gte": f"{year_from}-01-01",
                "primary_release_date.lte": f"{year_to}-12-31",
                "vote_count.gte": min_votes,
            }
            if genres:
                params["with_genres"] = ",".join(str(g) for g in genres)
            data = self._get("/discover/movie", params=params)
            for item in data.get("results", []):
                movies.append(self._parse_movie_brief(item))
        return movies

    # ------------------------------------------------------------------
    # Enrichment
    # ------------------------------------------------------------------

    def enrich_movie(self, movie: Movie) -> Movie:
        """Fetch full movie details including credits and keywords."""
        details = self._get(f"/movie/{movie.tmdb_id}", params={"language": "en-US"})
        credits = self._get(f"/movie/{movie.tmdb_id}/credits")
        keywords_data = self._get(f"/movie/{movie.tmdb_id}/keywords")

        # Parse genres from detail
        genres = []
        for g in details.get("genres", []):
            genre = Genre.from_tmdb_id(g["id"])
            if genre:
                genres.append(genre)

        # Parse cast (top 10 actors)
        actors: list[Person] = []
        for cast in credits.get("cast", [])[:10]:
            actors.append(Person(
                tmdb_id=cast["id"],
                name=cast["name"],
                role="Actor",
                character=cast.get("character", ""),
                popularity=cast.get("popularity", 0.0),
                profile_path=cast.get("profile_path", ""),
            ))

        # Parse directors
        directors: list[Person] = []
        for crew in credits.get("crew", []):
            if crew.get("job") == "Director":
                directors.append(Person(
                    tmdb_id=crew["id"],
                    name=crew["name"],
                    role="Director",
                    popularity=crew.get("popularity", 0.0),
                    profile_path=crew.get("profile_path", ""),
                ))

        # Parse keywords
        keywords = [kw["name"] for kw in keywords_data.get("keywords", [])]

        return Movie(
            tmdb_id=movie.tmdb_id,
            title=details.get("title", movie.title),
            overview=details.get("overview", movie.overview),
            release_date=details.get("release_date", movie.release_date),
            genres=genres,
            vote_average=details.get("vote_average", movie.vote_average),
            vote_count=details.get("vote_count", movie.vote_count),
            popularity=details.get("popularity", movie.popularity),
            poster_path=details.get("poster_path", movie.poster_path),
            backdrop_path=details.get("backdrop_path", ""),
            tagline=details.get("tagline", ""),
            runtime=details.get("runtime", 0),
            budget=details.get("budget", 0),
            revenue=details.get("revenue", 0),
            actors=actors,
            directors=directors,
            keywords=keywords,
            language=details.get("original_language", "en"),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rate_limit(self):
        """Ensure we respect TMDB rate limits."""
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to TMDB API."""
        if not self.api_key:
            raise RuntimeError(
                "TMDB_API_KEY not set. Get a free key at "
                "https://www.themoviedb.org/settings/api and set the "
                "TMDB_API_KEY environment variable."
            )
        self._rate_limit()
        url = f"{TMDB_BASE}{path}"
        resp = self._session.get(url, params={"api_key": self.api_key, **(params or {})})
        resp.raise_for_status()
        return resp.json()

    def _parse_movie_brief(self, item: dict) -> Movie:
        """Parse a movie from a search/discover list item (lightweight)."""
        genres = []
        for gid in item.get("genre_ids", []):
            genre = Genre.from_tmdb_id(gid)
            if genre:
                genres.append(genre)
        return Movie(
            tmdb_id=item["id"],
            title=item.get("title", ""),
            overview=item.get("overview", ""),
            release_date=item.get("release_date", ""),
            genres=genres,
            vote_average=item.get("vote_average", 0.0),
            vote_count=item.get("vote_count", 0),
            popularity=item.get("popularity", 0.0),
            poster_path=item.get("poster_path", ""),
            language=item.get("original_language", "en"),
        )
