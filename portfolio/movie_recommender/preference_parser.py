"""Natural language preference parser.

Extracts structured movie preferences from free-text user input.
Uses keyword matching and heuristics to simulate LLM-style parsing
without requiring an API key. Designed to be swappable with a real
LLM call (e.g. OpenAI, Anthropic) in the future.
"""

import re
from typing import Optional

from .models import Genre, UserPreference

# Genre keywords for fuzzy matching
GENRE_PATTERNS: dict[str, list[str]] = {
    "Action": ["action", "fight", "explosions", "combat", "stunt"],
    "Adventure": ["adventure", "journey", "quest", "expedition", "exploration"],
    "Animation": ["animation", "animated", "cartoon", "pixar", "ghibli", "anime"],
    "Comedy": ["comedy", "funny", "humor", "hilarious", "laugh", "comedic", "satire"],
    "Crime": ["crime", "mafia", "heist", "gangster", "robbery", "criminal"],
    "Documentary": ["documentary", "docu", "true story", "biography", "biopic"],
    "Drama": ["drama", "emotional", "tearjerker", "character", "serious"],
    "Family": ["family", "kids", "children", "disney", "wholesome"],
    "Fantasy": ["fantasy", "magic", "wizard", "dragon", "mythical", "supernatural", "fairy tale"],
    "History": ["history", "historical", "period piece", "war", "ancient"],
    "Horror": ["horror", "scary", "terror", "frightening", "creepy", "haunted", "gore", "slasher"],
    "Music": ["music", "musical", "concert", "band", "singer"],
    "Mystery": ["mystery", "whodunit", "detective", "puzzle", "investigation", "suspenseful"],
    "Romance": ["romance", "love", "romantic", "heartwarming", "relationship", "dating"],
    "Science Fiction": ["sci-fi", "scifi", "science fiction", "futuristic", "space", "alien", "robot", "cyberpunk", "dystopian", "time travel"],
    "Thriller": ["thriller", "tense", "suspense", "edge of your seat", "gripping", "psychological"],
    "War": ["war", "battle", "military", "soldier", "combat"],
    "Western": ["western", "cowboy", "wild west", "frontier"],
    "TV Movie": ["tv movie", "made for tv"],
}

# Mood keywords
MOOD_PATTERNS: dict[str, list[str]] = {
    "dark": ["dark", "gritty", "noir", "bleak", "grim", "violent"],
    "light": ["light", "feel-good", "uplifting", "cheerful", "wholesome", "fun"],
    "thrilling": ["thrilling", "exciting", "intense", "adrenaline", "fast-paced"],
    "inspiring": ["inspiring", "motivational", "uplifting", "heartwarming", "moving"],
    "thoughtful": ["thoughtful", "deep", "philosophical", "mind-bending", "cerebral"],
    "scary": ["scary", "horror", "terrifying", "frightening", "chilling"],
}

# Known director names (expanded during ingestion)
KNOWN_PEOPLE: set[str] = set()


class PreferenceParser:
    """Extract structured movie preferences from natural language.

    Usage:
        parser = PreferenceParser()
        prefs = parser.parse("I love sci-fi movies like Inception and Interstellar, especially ones directed by Christopher Nolan")
    """

    def __init__(self, known_people: Optional[set[str]] = None):
        """Initialize the preference parser.

        Args:
            known_people: Optional set of known actor/director names for
                          fuzzy matching in free-text queries.
        """
        self.known_people = known_people or KNOWN_PEOPLE

    def update_known_people(self, names: set[str]):
        """Add to the set of known actor/director names for matching."""
        self.known_people |= names

    def parse(self, text: str) -> UserPreference:
        """Parse natural language text into structured UserPreference."""
        text_lower = text.lower()

        # Extract genres
        liked_genres, disliked_genres = self._extract_genres(text_lower)

        # Extract people (actors / directors) — use original text for regex patterns
        liked_actors = self._extract_people(text, self.known_people)
        liked_directors = self._extract_directors(text, self.known_people)

        # Extract keywords
        keywords = self._extract_keywords(text, text_lower)

        # Extract year range
        year_range = self._extract_year_range(text)

        # Extract minimum rating
        min_rating = self._extract_rating(text_lower)

        # Extract mood
        mood = self._extract_mood(text_lower)

        return UserPreference(
            raw_text=text,
            liked_genres=liked_genres,
            disliked_genres=disliked_genres,
            liked_actors=liked_actors,
            liked_directors=liked_directors,
            keywords=keywords,
            year_range=year_range,
            min_rating=min_rating,
            mood=mood,
        )

    # ------------------------------------------------------------------
    # Internal extractors
    # ------------------------------------------------------------------

    def _extract_genres(self, text_lower: str) -> tuple[list[str], list[str]]:
        """Parse genre preferences from lowercased user text.

        Returns:
            Tuple of (liked_genres, disliked_genres).
        """
        liked: list[str] = []
        disliked: list[str] = []

        # Detect negation patterns like "not horror", "no comedy", "don't like romance"
        neg_pattern = re.compile(
            r"(?:not|no|don't like|dislike|hate|avoid|without)\s+([a-z\s]+?)(?:,|\.|$|but|and|or|with)",
        )
        neg_matches = neg_pattern.findall(text_lower)
        for match in neg_matches:
            for genre, keywords in GENRE_PATTERNS.items():
                if any(kw in match.strip() for kw in keywords):
                    if genre not in disliked:
                        disliked.append(genre)

        # Detect positive genre mentions
        for genre, keywords in GENRE_PATTERNS.items():
            if genre in disliked:
                continue
            # Check full genre name first
            if genre.lower() in text_lower:
                liked.append(genre)
                continue
            # Check keywords
            if any(kw in text_lower for kw in keywords):
                liked.append(genre)

        return liked, disliked

    def _extract_people(self, text: str, known: set[str]) -> list[str]:
        """Extract known actor/director names from text."""
        text_lower = text.lower()
        found: list[str] = []
        # Match capitalized proper names
        # First check known names
        for name in known:
            if name.lower() in text_lower:
                found.append(name)
        # Also try to extract "starring X", "featuring X", "with X" using original case
        extra_patterns = [
            r"(?:starring|featuring|with|actors? like|casts? like)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
            r"(?:directed by|director|from director)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
            r"(?:like|similar to)\s+\"?'?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        ]
        for pattern in extra_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                found.append(m.strip().title())
        return list(set(found))[:10]

    def _extract_directors(self, text: str, known: set[str]) -> list[str]:
        """Extract director names specifically."""
        text_lower = text.lower()
        found: list[str] = []
        # "directed by X", "X film", "X movie"
        dir_patterns = [
            r"directed by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
            r"director[s]?\s+(?:like\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
            r"films? (?:by|of|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        ]
        for pattern in dir_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                found.append(m.strip().title())

        for name in known:
            if name.lower() in text_lower:
                found.append(name)

        # Remove names also found as actors unless specifically "directed by"
        # For now, include all
        return list(set(found))[:5]

    def _extract_keywords(self, text: str, text_lower: str) -> list[str]:
        """Extract thematic keywords from the text."""
        keywords: list[str] = []

        # Movie-specific keyword patterns
        keyword_patterns = {
            "space": ["space", "planet", "galaxy", "interstellar", "cosmic"],
            "time travel": ["time travel", "time loop", "time machine"],
            "superhero": ["superhero", "hero", "marvel", "dc comics"],
            "zombie": ["zombie", "undead", "apocalypse"],
            "heist": ["heist", "robbery", "theft", "con artist"],
            "coming of age": ["coming of age", "teen", "adolescent", "growing up"],
            "based on true story": ["true story", "based on real", "real events"],
            "underdog": ["underdog", "against all odds", "triumph"],
            "revenge": ["revenge", "vengeance", "retribution"],
            "survival": ["survival", "stranded", "wilderness", "castaway"],
            "artificial intelligence": ["ai", "artificial intelligence", "robot", "machine learning"],
            "dystopian": ["dystopian", "dystopia", "post-apocalyptic"],
            "noir": ["noir", "film noir", "neo-noir"],
            "mind-bending": ["mind-bending", "psychological", "twist ending", "surreal"],
            "epic": ["epic", "saga", "grand", "sweeping"],
            "indie": ["indie", "independent", "arthouse", "auteur"],
        }

        for theme, kws in keyword_patterns.items():
            if any(kw in text_lower for kw in kws):
                keywords.append(theme)

        # Extract quoted phrases as keywords
        quoted = re.findall(r'"([^"]+)"', text)
        keywords.extend(quoted[:3])

        return keywords[:10]

    def _extract_year_range(self, text: str) -> tuple[int, int]:
        """Extract preferred year range."""
        # "movies from the 90s", "recent movies", "classics", "80s movies"
        # Match decade patterns like "90s", "1980s"
        decade_match = re.search(r"\b((?:19|20)?(\d)0)s\b", text.lower())
        if decade_match:
            suffix = int(decade_match.group(2))  # e.g., 9 for "90s" or "1990s"
            decade_start = 1900 + suffix * 10
            return (decade_start, decade_start + 9)

        # "recent" / "new" → last 5 years
        if re.search(r"\b(recent|new|latest|modern|current)\b", text.lower()):
            return (2020, 2026)

        # "classic" / "old" → pre-2000
        if re.search(r"\b(classic|old|vintage|golden age|retro)\b", text.lower()):
            return (1930, 2000)

        # "after 2010", "before 2000", "between 2000 and 2010"
        range_match = re.search(r"between\s+(\d{4})\s+and\s+(\d{4})", text.lower())
        if range_match:
            return (int(range_match.group(1)), int(range_match.group(2)))

        after_match = re.search(r"after\s+(\d{4})", text.lower())
        if after_match:
            return (int(after_match.group(1)), 2030)

        before_match = re.search(r"before\s+(\d{4})", text.lower())
        if before_match:
            return (1900, int(before_match.group(1)))

        # Default: all years
        return (1900, 2030)

    def _extract_rating(self, text_lower: str) -> float:
        """Extract minimum rating preference."""
        # "rated above 7", "at least 8/10", "highly rated"
        rating_match = re.search(r"(?:rated?\s*(?:above|over|at least|>=?)\s*)?(\d+(?:\.\d+)?)\s*(?:/10|out of 10|stars)?", text_lower)
        if rating_match:
            val = float(rating_match.group(1))
            if val > 10:
                val = val / 10.0  # percentage
            if 0 < val <= 10:
                return val

        if re.search(r"\b(highly rated|top rated|best|great|excellent)\b", text_lower):
            return 7.0

        return 0.0  # no minimum

    def _extract_mood(self, text_lower: str) -> str:
        """Extract mood preference."""
        best_mood = ""
        best_count = 0
        for mood, keywords in MOOD_PATTERNS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_mood = mood
        return best_mood
