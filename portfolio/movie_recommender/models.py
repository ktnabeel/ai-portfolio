"""Data models for the movie recommendation system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Genre(str, Enum):
    """TMDB genre IDs mapped to readable names."""
    ACTION = "Action"
    ADVENTURE = "Adventure"
    ANIMATION = "Animation"
    COMEDY = "Comedy"
    CRIME = "Crime"
    DOCUMENTARY = "Documentary"
    DRAMA = "Drama"
    FAMILY = "Family"
    FANTASY = "Fantasy"
    HISTORY = "History"
    HORROR = "Horror"
    MUSIC = "Music"
    MYSTERY = "Mystery"
    ROMANCE = "Romance"
    SCIENCE_FICTION = "Science Fiction"
    THRILLER = "Thriller"
    WAR = "War"
    WESTERN = "Western"
    TV_MOVIE = "TV Movie"

    @classmethod
    def from_tmdb_id(cls, genre_id: int) -> Optional["Genre"]:
        """Map a TMDB numeric genre ID to a Genre enum member.

        Returns None if the genre_id is not recognized.
        """
        mapping = {
            28: cls.ACTION,
            12: cls.ADVENTURE,
            16: cls.ANIMATION,
            35: cls.COMEDY,
            80: cls.CRIME,
            99: cls.DOCUMENTARY,
            18: cls.DRAMA,
            10751: cls.FAMILY,
            14: cls.FANTASY,
            36: cls.HISTORY,
            27: cls.HORROR,
            10402: cls.MUSIC,
            9648: cls.MYSTERY,
            10749: cls.ROMANCE,
            878: cls.SCIENCE_FICTION,
            53: cls.THRILLER,
            10752: cls.WAR,
            37: cls.WESTERN,
            10770: cls.TV_MOVIE,
        }
        return mapping.get(genre_id)


@dataclass(frozen=True)
class Person:
    """An actor, director, or crew member."""
    tmdb_id: int
    name: str
    role: str  # "Actor", "Director", etc.
    character: str = ""  # character name for actors
    popularity: float = 0.0
    profile_path: str = ""


@dataclass(frozen=True)
class Movie:
    """A movie with full metadata from TMDB."""
    tmdb_id: int
    title: str
    overview: str
    release_date: str  # YYYY-MM-DD
    genres: list[Genre] = field(default_factory=list)
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    poster_path: str = ""
    backdrop_path: str = ""
    tagline: str = ""
    runtime: int = 0  # minutes
    budget: int = 0
    revenue: int = 0
    actors: list[Person] = field(default_factory=list)
    directors: list[Person] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    language: str = "en"

    @property
    def year(self) -> int:
        """Extract the release year from the YYYY-MM-DD release date."""
        try:
            return int(self.release_date[:4])
        except (ValueError, IndexError):
            return 0

    @property
    def genre_names(self) -> list[str]:
        """Genre enum values as plain strings for display."""
        return [g.value for g in self.genres]


@dataclass(frozen=True)
class UserPreference:
    """Parsed user preferences from natural language input."""
    raw_text: str
    liked_genres: list[str] = field(default_factory=list)
    disliked_genres: list[str] = field(default_factory=list)
    liked_actors: list[str] = field(default_factory=list)
    liked_directors: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    year_range: tuple[int, int] = (1900, 2030)
    min_rating: float = 0.0
    mood: str = ""  # "dark", "light", "thrilling", "inspiring", etc.


@dataclass
class RecommendationResult:
    """A single movie recommendation with scores."""
    movie: Movie
    content_score: float = 0.0  # two-tower similarity
    collaborative_score: float = 0.0  # collaborative filtering score
    final_score: float = 0.0  # ensemble score
    explanation: str = ""


@dataclass
class RecommendationResponse:
    """Full recommendation response for the UI."""
    preferences: UserPreference
    recommendations: list[RecommendationResult] = field(default_factory=list)
    total_movies_indexed: int = 0
    method_breakdown: str = ""
