"""Data ingestion pipeline — fetch movies from TMDB, enrich, and build index."""

import logging
from collections import Counter

from .models import Genre, Movie, Person
from .tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


class MoviePipeline:
    """Orchestrates data ingestion from TMDB API.

    Usage:
        pipeline = MoviePipeline(api_key="...")
        movies = pipeline.run(pages=5, enrich=True)
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the ingestion pipeline.

        Args:
            api_key: TMDB API key. Falls back to sample data if not set.
        """
        self.client = TMDBClient(api_key)
        self.movies: list[Movie] = []
        self.all_actors: set[str] = set()
        self.all_directors: set[str] = set()

    def run(
        self,
        pages: int = 5,
        enrich: bool = True,
        include_top_rated: bool = True,
    ) -> list[Movie]:
        """Run the full ingestion pipeline.

        Args:
            pages: Number of pages to fetch per source (popular, discover, etc.)
            enrich: Whether to fetch full credits + keywords for each movie.
            include_top_rated: Also fetch top-rated movies.
        """
        logger.info("Starting movie ingestion pipeline...")

        # Step 1 — Fetch brief movie lists
        raw: list[Movie] = []
        raw.extend(self.client.fetch_popular_movies(pages=pages))

        if include_top_rated:
            raw.extend(self.client.fetch_top_rated_movies(pages=pages))

        # Also discover across key genres to get diversity
        genre_batches = [
            [28, 12],        # Action, Adventure
            [35],            # Comedy
            [18],            # Drama
            [27, 53],        # Horror, Thriller
            [878, 14],       # Sci-Fi, Fantasy
            [10749, 35],     # Romance, Comedy
            [80, 9648],      # Crime, Mystery
            [99],            # Documentary
            [16, 10751],     # Animation, Family
        ]
        for batch in genre_batches:
            try:
                discovered = self.client.discover_movies(
                    genres=batch,
                    pages=max(1, pages // 3),
                )
                raw.extend(discovered)
            except Exception as e:
                logger.warning(f"Discover batch {batch} failed: {e}")

        # Deduplicate by tmdb_id
        seen: set[int] = set()
        unique: list[Movie] = []
        for m in raw:
            if m.tmdb_id not in seen:
                seen.add(m.tmdb_id)
                unique.append(m)
        raw = unique
        logger.info(f"Fetched {len(raw)} unique movies (brief)")

        # Step 2 — Enrich with full details
        if enrich:
            enriched: list[Movie] = []
            total = len(raw)
            for i, movie in enumerate(raw):
                try:
                    full = self.client.enrich_movie(movie)
                    enriched.append(full)

                    # Collect known people
                    for a in full.actors:
                        self.all_actors.add(a.name)
                    for d in full.directors:
                        self.all_directors.add(d.name)

                    if (i + 1) % 20 == 0:
                        logger.info(f"Enriched {i + 1}/{total} movies...")
                except Exception as e:
                    logger.warning(f"Failed to enrich movie {movie.tmdb_id} '{movie.title}': {e}")
                    enriched.append(movie)  # keep the brief version
            self.movies = enriched
        else:
            self.movies = raw

        logger.info(
            f"Ingestion complete: {len(self.movies)} movies, "
            f"{len(self.all_actors)} actors, {len(self.all_directors)} directors"
        )
        return self.movies

    def run_sample(self) -> list[Movie]:
        """Return a curated sample dataset when TMDB API is not available.

        This provides a fallback for demo/offline use with hand-picked
        popular movies across genres. Backdrop and poster paths are from
        TMDB's public CDN (no API key needed to display images).
        """
        sample = [
            Movie(
                tmdb_id=27205, title="Inception",
                overview="A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
                release_date="2010-07-15",
                genres=_g("Action", "Science Fiction", "Adventure"),
                vote_average=8.4, vote_count=35000, popularity=95.0,
                backdrop_path="/8ZTVqvKGkA28l427CMGkYRxFf7n.jpg",
                poster_path="/9gk7adHYeDWC0GZ2hFL4GZNG5wv.jpg",
                directors=[Person(tmdb_id=525, name="Christopher Nolan", role="Director", popularity=60.0)],
                actors=[Person(tmdb_id=6193, name="Leonardo DiCaprio", role="Actor", popularity=70.0),
                        Person(tmdb_id=2524, name="Tom Hardy", role="Actor", popularity=55.0),
                        Person(tmdb_id=27578, name="Ken Watanabe", role="Actor", popularity=30.0)],
                keywords=["dream", "heist", "mind-bending", "architecture", "subconscious"],
            ),
            Movie(
                tmdb_id=155, title="The Dark Knight",
                overview="Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations.",
                release_date="2008-07-16",
                genres=_g("Action", "Crime", "Drama", "Thriller"),
                vote_average=8.5, vote_count=32000, popularity=90.0,
                backdrop_path="/nMKdUUepR0i5zn0y1T4CsSB5ezu.jpg",
                poster_path="/qJ2tW6WMUDs911OhJGghJpNaJrO.jpg",
                directors=[Person(tmdb_id=525, name="Christopher Nolan", role="Director", popularity=60.0)],
                actors=[Person(tmdb_id=3894, name="Christian Bale", role="Actor", popularity=50.0),
                        Person(tmdb_id=1810, name="Heath Ledger", role="Actor", popularity=40.0),
                        Person(tmdb_id=126169, name="Aaron Eckhart", role="Actor", popularity=25.0)],
                keywords=["superhero", "vigilante", "chaos", "gritty", "noir"],
            ),
            Movie(
                tmdb_id=680, title="Pulp Fiction",
                overview="A burger-loving hit man, his philosophical partner, a drug-addled gangster's moll and a washed-up boxer converge in this sprawling, comedic crime caper.",
                release_date="1994-10-14",
                genres=_g("Crime", "Thriller"),
                vote_average=8.5, vote_count=27000, popularity=75.0,
                backdrop_path="/suaEOtk1N1sgg2M7M5BVpFfqu3T.jpg",
                poster_path="/d5iIlFn5s0ImszYzBPbMq8Jdd5S.jpg",
                directors=[Person(tmdb_id=138, name="Quentin Tarantino", role="Director", popularity=55.0)],
                actors=[Person(tmdb_id=8891, name="John Travolta", role="Actor", popularity=45.0),
                        Person(tmdb_id=139, name="Samuel L. Jackson", role="Actor", popularity=60.0),
                        Person(tmdb_id=2231, name="Uma Thurman", role="Actor", popularity=40.0)],
                keywords=["non-linear", "dark comedy", "hitman", "crime", "cult classic"],
            ),
            Movie(
                tmdb_id=550, title="Fight Club",
                overview="An insomniac office worker and a devil-may-care soap maker form an underground fight club that evolves into much more.",
                release_date="1999-10-15",
                genres=_g("Drama"),
                vote_average=8.4, vote_count=28000, popularity=80.0,
                backdrop_path="/hZkgoQYus5L7pGE1g5eQ7JFwRYT.jpg",
                poster_path="/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
                directors=[Person(tmdb_id=7467, name="David Fincher", role="Director", popularity=50.0)],
                actors=[Person(tmdb_id=819, name="Brad Pitt", role="Actor", popularity=65.0),
                        Person(tmdb_id=287, name="Edward Norton", role="Actor", popularity=40.0),
                        Person(tmdb_id=1283, name="Helena Bonham Carter", role="Actor", popularity=35.0)],
                keywords=["insomnia", "alter ego", "cult", "mind-bending", "twist ending"],
            ),
            Movie(
                tmdb_id=238, title="The Godfather",
                overview="The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant youngest son.",
                release_date="1972-03-14",
                genres=_g("Drama", "Crime"),
                vote_average=8.7, vote_count=20000, popularity=85.0,
                backdrop_path="/tmU7GeKVybMWFButWEGl2M4GeiP.jpg",
                poster_path="/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
                directors=[Person(tmdb_id=1776, name="Francis Ford Coppola", role="Director", popularity=45.0)],
                actors=[Person(tmdb_id=3084, name="Marlon Brando", role="Actor", popularity=35.0),
                        Person(tmdb_id=1158, name="Al Pacino", role="Actor", popularity=55.0),
                        Person(tmdb_id=3085, name="James Caan", role="Actor", popularity=25.0)],
                keywords=["mafia", "family", "crime", "classic", "organized crime"],
            ),
            Movie(
                tmdb_id=278, title="The Shawshank Redemption",
                overview="A banker convicted of uxoricide forms a friendship over a quarter century with a hardened convict, while maintaining his innocence and trying to escape.",
                release_date="1994-09-23",
                genres=_g("Drama"),
                vote_average=8.7, vote_count=26000, popularity=88.0,
                backdrop_path="/z6q2Qj6CZ8FuajsdNv4pF1kNTk4.jpg",
                poster_path="/9cqNxx0GxF0bflZmeSMuL5tnGzO.jpg",
                directors=[Person(tmdb_id=1106, name="Frank Darabont", role="Director", popularity=20.0)],
                actors=[Person(tmdb_id=201, name="Tim Robbins", role="Actor", popularity=30.0),
                        Person(tmdb_id=202, name="Morgan Freeman", role="Actor", popularity=60.0)],
                keywords=["prison", "friendship", "hope", "escape", "redemption"],
            ),
            Movie(
                tmdb_id=244786, title="Whiplash",
                overview="Under the direction of a ruthless instructor, a talented young drummer begins to pursue perfection at any cost.",
                release_date="2014-10-10",
                genres=_g("Drama", "Music"),
                vote_average=8.4, vote_count=15000, popularity=50.0,
                backdrop_path="/6O1mO0XpImXy3AYp9Ioh0arTqdi.jpg",
                poster_path="/7fn621jOHwUQFQHqJYK0NEjwcIR.jpg",
                directors=[Person(tmdb_id=136495, name="Damien Chazelle", role="Director", popularity=30.0)],
                actors=[Person(tmdb_id=156476, name="Miles Teller", role="Actor", popularity=35.0),
                        Person(tmdb_id=16861, name="J.K. Simmons", role="Actor", popularity=40.0)],
                keywords=["music", "jazz", "drumming", "obsession", "teacher-student"],
            ),
            Movie(
                tmdb_id=157336, title="Interstellar",
                overview="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
                release_date="2014-11-05",
                genres=_g("Science Fiction", "Adventure", "Drama"),
                vote_average=8.4, vote_count=34000, popularity=92.0,
                backdrop_path="/rAiYTfKGqDXaqyHwEZ4Bq2SJwYL.jpg",
                poster_path="/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
                directors=[Person(tmdb_id=525, name="Christopher Nolan", role="Director", popularity=60.0)],
                actors=[Person(tmdb_id=10297, name="Matthew McConaughey", role="Actor", popularity=50.0),
                        Person(tmdb_id=83002, name="Anne Hathaway", role="Actor", popularity=45.0),
                        Person(tmdb_id=1892, name="Matt Damon", role="Actor", popularity=55.0)],
                keywords=["space", "wormhole", "survival", "time dilation", "family"],
            ),
            Movie(
                tmdb_id=106646, title="The Wolf of Wall Street",
                overview="Based on the true story of Jordan Belfort, from his rise to a wealthy stock-broker living the high life to his fall involving crime, corruption and the federal government.",
                release_date="2013-12-25",
                genres=_g("Crime", "Comedy", "Drama"),
                vote_average=8.0, vote_count=23000, popularity=70.0,
                backdrop_path="/aKZz5tLe5pT7iHOYQJTC4fEKeEQ.jpg",
                poster_path="/34m2tyKAY9ahYBA6S4Mxnf4txmS.jpg",
                directors=[Person(tmdb_id=37, name="Martin Scorsese", role="Director", popularity=50.0)],
                actors=[Person(tmdb_id=6193, name="Leonardo DiCaprio", role="Actor", popularity=70.0),
                        Person(tmdb_id=11196, name="Jonah Hill", role="Actor", popularity=35.0),
                        Person(tmdb_id=6384, name="Margot Robbie", role="Actor", popularity=55.0)],
                keywords=["wall street", "excess", "true story", "corruption", "drugs"],
            ),
            Movie(
                tmdb_id=77338, title="The Intouchables",
                overview="After he becomes a quadriplegic from a paragliding accident, an aristocrat hires a young man from the projects to be his caregiver.",
                release_date="2011-11-02",
                genres=_g("Drama", "Comedy"),
                vote_average=8.3, vote_count=17000, popularity=55.0,
                backdrop_path="/ihWaJZC4Lk6qGMm7tJ7rvEniBfT.jpg",
                poster_path="/1QU7HKgsQbGpzsJbOdHCwtkM3Qa.jpg",
                directors=[Person(tmdb_id=64573, name="Olivier Nakache", role="Director", popularity=15.0)],
                actors=[Person(tmdb_id=24045, name="François Cluzet", role="Actor", popularity=20.0),
                        Person(tmdb_id=193652, name="Omar Sy", role="Actor", popularity=25.0)],
                keywords=["friendship", "disability", "true story", "uplifting", "heartwarming"],
            ),
            Movie(
                tmdb_id=489, title="Good Will Hunting",
                overview="Will Hunting, a janitor at M.I.T., has a gift for mathematics, but needs help from a psychologist to find direction in his life.",
                release_date="1997-12-05",
                genres=_g("Drama"),
                vote_average=8.1, vote_count=12000, popularity=45.0,
                backdrop_path="/bE2oGBLWNYKIPRY7GhkIP7FPZfi.jpg",
                poster_path="/bABCBKYBK7A5G1x0FzoeYDfD5cY.jpg",
                directors=[Person(tmdb_id=777, name="Gus Van Sant", role="Director", popularity=25.0)],
                actors=[Person(tmdb_id=1892, name="Matt Damon", role="Actor", popularity=55.0),
                        Person(tmdb_id=235, name="Robin Williams", role="Actor", popularity=50.0),
                        Person(tmdb_id=1893, name="Ben Affleck", role="Actor", popularity=45.0)],
                keywords=["genius", "therapy", "mathematics", "coming of age", "friendship"],
            ),
            Movie(
                tmdb_id=769, title="GoodFellas",
                overview="The story of Henry Hill and his life in the mafia, covering his relationship with his wife Karen Hill and his mob partners.",
                release_date="1990-09-12",
                genres=_g("Crime", "Drama"),
                vote_average=8.4, vote_count=13000, popularity=50.0,
                backdrop_path="/sw7mordbZxgITU877yTpZCud90M.jpg",
                poster_path="/aKuFiU82s5ISJDxUbBs8Iq0d5f5.jpg",
                directors=[Person(tmdb_id=37, name="Martin Scorsese", role="Director", popularity=50.0)],
                actors=[Person(tmdb_id=380, name="Robert De Niro", role="Actor", popularity=60.0),
                        Person(tmdb_id=1146, name="Ray Liotta", role="Actor", popularity=25.0),
                        Person(tmdb_id=1147, name="Joe Pesci", role="Actor", popularity=30.0)],
                keywords=["mafia", "crime", "rise and fall", "true story", "organized crime"],
            ),
            Movie(
                tmdb_id=11216, title="Cinema Paradiso",
                overview="A filmmaker recalls his childhood when falling in love with the pictures at the cinema of his home village and forms a deep friendship with the cinema's projectionist.",
                release_date="1988-11-17",
                genres=_g("Drama", "Romance"),
                vote_average=8.4, vote_count=5000, popularity=35.0,
                backdrop_path="/gUqz1Vaq4iUIEOQbGqCY6HP24o4.jpg",
                poster_path="/8SRj3R2gL5V3q3dQHfMmHzU4SSS.jpg",
                directors=[Person(tmdb_id=5289, name="Giuseppe Tornatore", role="Director", popularity=18.0)],
                actors=[Person(tmdb_id=29460, name="Philippe Noiret", role="Actor", popularity=22.0),
                        Person(tmdb_id=29461, name="Salvatore Cascio", role="Actor", popularity=10.0)],
                keywords=["cinema", "nostalgia", "friendship", "coming of age", "italy"],
            ),
            Movie(
                tmdb_id=399566, title="Godzilla vs. Kong",
                overview="In a time when monsters walk the Earth, humanity's fight for its future sets Godzilla and Kong on a collision course.",
                release_date="2021-03-31",
                genres=_g("Action", "Science Fiction", "Thriller"),
                vote_average=7.8, vote_count=9000, popularity=65.0,
                backdrop_path="/inJjDhCjfhh3RtrJWBmmDqeuSYC.jpg",
                poster_path="/pgqgaUx1cJb5oZQQ5v5tNARBuBk.jpg",
                directors=[Person(tmdb_id=108231, name="Adam Wingard", role="Director", popularity=20.0)],
                actors=[Person(tmdb_id=505, name="Alexander Skarsgård", role="Actor", popularity=35.0),
                        Person(tmdb_id=1142, name="Millie Bobby Brown", role="Actor", popularity=50.0)],
                keywords=["monster", "kaiju", "giant monster", "showdown", "epic"],
            ),
            Movie(
                tmdb_id=419430, title="Get Out",
                overview="Chris and his girlfriend Rose go upstate to visit her parents for the weekend. At first, Chris reads the family's overly accommodating behavior as nervous attempts to deal with their daughter's interracial relationship, but as the weekend progresses, a series of increasingly disturbing discoveries lead him to a truth that he never could have imagined.",
                release_date="2017-02-24",
                genres=_g("Horror", "Mystery", "Thriller"),
                vote_average=7.8, vote_count=16000, popularity=55.0,
                backdrop_path="/8Y43mQwI0BUKpQUCyIoFSKkPhPs.jpg",
                poster_path="/tFXcEccSQMf3lfhfXKSU9iVBpaI.jpg",
                directors=[Person(tmdb_id=58728, name="Jordan Peele", role="Director", popularity=35.0)],
                actors=[Person(tmdb_id=1754048, name="Daniel Kaluuya", role="Actor", popularity=40.0),
                        Person(tmdb_id=25366, name="Allison Williams", role="Actor", popularity=25.0)],
                keywords=["social thriller", "race", "horror", "mind-bending", "twist"],
            ),
        ]
        self.movies = sample
        for m in sample:
            for a in m.actors:
                self.all_actors.add(a.name)
            for d in m.directors:
                self.all_directors.add(d.name)
        return sample


def _g(*names: str):
    """Helper to create Genre enums from names."""
    result = []
    for n in names:
        try:
            result.append(Genre(n))
        except ValueError:
            pass
    return result
