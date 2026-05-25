"""Generate 1 000 synthetic movies for offline deployment.

Produces ``portfolio/movie_recommender/_sampled_movies.json`` — a self-contained
dataset that needs no TMDB API key.  The recommender indexes these at startup.

Usage:
    uv run python scripts/generate_movies.py
"""

import json
import os
import random
from pathlib import Path

# Seed for reproducibility
random.seed(424242)

OUT_PATH = Path(__file__).resolve().parent.parent / "portfolio" / "movie_recommender" / "_sampled_movies.json"

# ── Pools for synthetic generation ────────────────────────────────────────

FIRST_NAMES = [
    "James", "Emily", "Michael", "Sarah", "David", "Jessica", "Robert", "Jennifer",
    "Daniel", "Amanda", "William", "Laura", "Christopher", "Rachel", "Anthony", "Nicole",
    "Matthew", "Stephanie", "Ryan", "Melissa", "Ethan", "Emma", "Oliver", "Sophia",
    "Lucas", "Isabella", "Noah", "Mia", "Liam", "Charlotte", "Sebastian", "Olivia",
    "Samuel", "Abigail", "Jackson", "Evelyn", "Aiden", "Harper", "Joseph", "Victoria",
    "Andrew", "Chloe", "Thomas", "Grace", "Alexander", "Zoe", "Henry", "Lily",
    "Oscar", "Hannah", "Felix", "Eleanor", "Jasper", "Scarlett", "Marcus", "Aurora",
    "Victor", "Penelope", "Xavier", "Nova", "Derek", "Willow", "Leon", "Ivy",
    "Max", "Violet", "Julian", "Stella", "Damien", "Ruby", "Gabriel", "Alice",
]

LAST_NAMES = [
    "Anderson", "Bennett", "Carter", "Davis", "Edwards", "Foster", "Garcia", "Hart",
    "Irwin", "Johnson", "King", "Lawson", "Mitchell", "Nakamura", "Owens", "Patel",
    "Quinn", "Reynolds", "Shaw", "Torres", "Upton", "Vance", "Wright", "Xavier",
    "Yoshida", "Zhang", "Brooks", "Coleman", "Dawson", "Ellis", "Fletcher", "Graham",
    "Hawkins", "Ingram", "Jenkins", "Knight", "Lambert", "Mendoza", "Nolan", "Parker",
    "Reeves", "Sullivan", "Thornton", "Underwood", "Valdez", "Wallace", "Young",
    "Blackwood", "Crawford", "Donovan", "Everett", "Fitzpatrick", "Gallagher",
]

GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "History", "Horror", "Music",
    "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western",
]

# Genre → typical title patterns
TITLE_TEMPLATES = {
    "Action": [
        "{last} Protocol", "Operation {word}", "{word} Justice",
        "The {noun}'s Revenge", "Rogue {noun}", "{city} Under Siege",
    ],
    "Adventure": [
        "The Lost {noun} of {city}", "Journey to {word}",
        "Beyond the {noun}", "The {noun} Chronicles", "Expedition {word}",
    ],
    "Animation": [
        "{first} and the Magic {noun}", "The Secret World of {noun}s",
        "{word} Tales", "Dream Big, {first}!", "The Little {noun} That Could",
    ],
    "Comedy": [
        "My Ex's {noun}", "The Worst {noun} Ever",
        "{first} vs. Life", "How to Lose a {noun} in 10 Days",
        "The Accidental {noun}", "Bad Date Chronicles",
    ],
    "Crime": [
        "The {city} Connection", "Dead on {word}",
        "The {noun} Files", "Blood {noun}", "Witness Protection {word}",
    ],
    "Drama": [
        "The Weight of {word}", "All That Remains",
        "A Quiet {noun}", "After the {noun}", "The Glass {noun}",
    ],
    "Fantasy": [
        "The {noun} of {word}", "Queen of {noun}s",
        "The Last {noun} Keeper", "Shadow of the {noun}",
        "Dragon's {noun}", "The Enchanted {noun}",
    ],
    "Horror": [
        "The {noun} Beneath", "Whispers in the {noun}",
        "The {word} Haunting", "Don't Open the {noun}",
        "Cabin of {noun}s", "The {word} That Follows",
    ],
    "Mystery": [
        "The {word} Affair", "Who Killed {first} {last}?",
        "The {noun} Puzzle", "Case File: {city}",
        "The Disappearance of {word}", "Last Seen at {noun}",
    ],
    "Romance": [
        "Meet Me at the {noun}", "Love in {city}",
        "The Spaces Between {noun}s", "Forever {word}",
        "A {word} Kind of Love", "Before {word}",
    ],
    "Science Fiction": [
        "Project {word}", "The {noun} Singularity",
        "Echoes of {word}", "Beyond the {noun} Horizon",
        "The {word} Anomaly", "Colony {word} One",
    ],
    "Thriller": [
        "The {word} Deception", "Zero Hour: {city}",
        "The {noun} Conspiracy", "Fatal {word}",
        "The {word} Threshold", "Countdown to {word}",
    ],
}

NOUNS = [
    "Shadow", "Storm", "Echo", "Flame", "Spire", "Crown", "Frost",
    "Mirror", "Veil", "Ember", "Cipher", "Ridge", "Hollow", "Tide",
    "Copper", "Ivory", "Obsidian", "Quartz", "Opal", "Jade",
    "Sparrow", "Fox", "Raven", "Wolf", "Serpent", "Phoenix", "Falcon",
    "Garden", "Tower", "Bridge", "River", "Ocean", "Mountain", "Forest",
]

ADJECTIVES = [
    "Dark", "Golden", "Crimson", "Silver", "Silent", "Burning", "Frozen",
    "Hidden", "Broken", "Eternal", "Rising", "Last", "Final", "First",
    "Secret", "Wild", "Ancient", "Crystal", "Iron", "Velvet",
]

CITIES = [
    "London", "Paris", "Tokyo", "Berlin", "Moscow", "Sydney", "Miami",
    "Chicago", "Seattle", "Boston", "Atlanta", "Dallas", "Phoenix",
    "Detroit", "Denver", "Memphis", "Brooklyn", "Venice", "Prague", "Vienna",
    "Shanghai", "Seoul", "Mumbai", "Dubai", "Istanbul", "Cairo",
    "Havana", "Bangkok", "Lisbon", "Stockholm", "Oslo", "Toronto",
]

WORDS = [
    "Obsidian", "Crimson", "Vector", "Nebula", "Horizon", "Zenith",
    "Eclipse", "Phantom", "Catalyst", "Omega", "Nova", "Requiem",
    "Vortex", "Meridian", "Cascade", "Apex", "Vigil", "Solstice",
]

# Genre → keywords
KEYWORDS = {
    "Action": ["explosions", "car chase", "heist", "showdown", "fight", "weapons", "stunt", "military", "spy", "undercover"],
    "Adventure": ["quest", "treasure", "journey", "expedition", "exploration", "ancient", "map", "survival", "wilderness"],
    "Animation": ["animated", "family-friendly", "coming of age", "talking animals", "musical", "colorful", "whimsical"],
    "Comedy": ["laugh out loud", "slapstick", "satire", "romantic comedy", "buddy comedy", "parody", "deadpan", "quirky", "misunderstanding"],
    "Crime": ["heist", "detective", "murder", "gangster", "undercover", "investigation", "corruption", "noir", "double cross"],
    "Drama": ["character study", "emotional", "tragedy", "redemption", "family", "loss", "identity", "social commentary"],
    "Fantasy": ["magic", "dragon", "wizard", "kingdom", "prophecy", "mythical", "quest", "dark lord", "enchanted"],
    "Horror": ["supernatural", "ghost", "slasher", "haunted house", "psychological", "gore", "monster", "curse", "found footage"],
    "Mystery": ["whodunit", "clues", "detective", "plot twist", "red herring", "investigation", "puzzle", "unreliable narrator"],
    "Romance": ["love story", "meet cute", "forbidden love", "heartbreak", "second chance", "chemistry", "slow burn", "destiny"],
    "Science Fiction": ["dystopian", "alien", "time travel", "robot", "AI", "cyberpunk", "space", "futuristic", "parallel universe"],
    "Thriller": ["suspense", "plot twist", "psychological", "cat and mouse", "conspiracy", "paranoia", "race against time", "espionage"],
}

# Genre → overview first sentences
OVERVIEWS = {
    "Action": [
        "A retired special-forces operative is forced back into action when {pronoun} discovers a global conspiracy.",
        "When a routine mission goes wrong, an elite soldier must fight {pronoun} way through enemy territory.",
        "A disgraced detective uncovers a criminal empire hiding in plain sight in {city}.",
    ],
    "Adventure": [
        "An archaeologist stumbles upon an ancient map leading to a legendary lost {noun}.",
        "When a mysterious artifact surfaces in {city}, a daring explorer sets out to uncover its origins.",
        "A young cartographer embarks on a perilous journey across uncharted lands.",
    ],
    "Animation": [
        "In a world where {noun}s come to life, a young {first} discovers the power of imagination.",
        "A misfit band of {noun}s must band together to save their whimsical homeland.",
        "When magic starts fading from the world, a child and a peculiar {noun} set out to restore it.",
    ],
    "Comedy": [
        "After a disastrous breakup, {first} {last} decides to reinvent {pronoun}self in the most chaotic way possible.",
        "Two polar-opposite roommates are forced to live together after a {noun} mix-up.",
        "A corporate worker accidentally becomes a viral sensation for all the wrong reasons.",
    ],
    "Crime": [
        "A seasoned detective follows a trail of clues that leads deep into {city}'s underworld.",
        "When a high-profile {noun} heist shakes the city, an unlikely investigator takes the case.",
        "A former con artist is pulled back into the game for one last, dangerous score.",
    ],
    "Drama": [
        "A family in {city} struggles to hold together when long-buried secrets resurface.",
        "An aging {profession} reflects on a life of choices, regrets, and unexpected second chances.",
        "In the aftermath of a tragedy, strangers find their lives intertwined in unexpected ways.",
    ],
    "Fantasy": [
        "In a kingdom ruled by an ancient {noun}, a prophecy foretells the return of the lost heir.",
        "A blacksmith's apprentice discovers they are the last in a line of elemental {noun} keepers.",
        "When darkness threatens the realm, a fellowship of unlikely heroes must take a stand.",
    ],
    "Horror": [
        "A family moves into a secluded {noun}, only to discover something sinister lurks beneath.",
        "A group of friends on a camping trip awaken an ancient force they cannot escape.",
        "A psychological experiment takes a terrifying turn when the subjects begin to disappear one by one.",
    ],
    "Mystery": [
        "A journalist receives an anonymous tip about a decades-old disappearance in {city}.",
        "When a reclusive author dies under strange circumstances, a fan turns sleuth.",
        "An amateur detective notices a pattern linking seemingly random events across the city.",
    ],
    "Romance": [
        "Two strangers meet by chance in {city} and discover that timing is everything.",
        "A cynical book editor and an idealistic author clash — then fall for each other.",
        "When childhood friends reunite after twenty years, old feelings resurface in unexpected ways.",
    ],
    "Science Fiction": [
        "In the year 2157, a scientist makes a breakthrough that could rewrite the laws of physics.",
        "A deep-space mission encounters an anomaly that challenges everything humanity knows.",
        "When artificial intelligence gains consciousness, one programmer must decide the fate of both worlds.",
    ],
    "Thriller": [
        "A corporate lawyer uncovers a dangerous secret hidden in plain sight at {pronoun} firm.",
        "An ordinary person receives a cryptic message that sends them on a pulse-pounding chase.",
        "With only 48 hours to prove their innocence, an accused fugitive races against time.",
    ],
}

PROFESSIONS = ["pianist", "architect", "sculptor", "veterinarian", "chef", "professor", "journalist", "photographer"]
PRONOUNS = ["his", "her", "their"]

# ── Helpers ────────────────────────────────────────────────────────────────

def _pick(seq):
    return random.choice(seq)

def _pick_n(seq, n):
    return random.sample(seq, min(n, len(seq)))

def _gen_id():
    """Generate unique synthetic TMDB ID (9xxxxx range to avoid real IDs)."""
    return random.randint(900000, 999999)

def _gen_date(year: int) -> str:
    """Random release date in the given year."""
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def generate_movie(used_ids: set[int]) -> dict:
    """Generate one synthetic movie entry as a JSON-serializable dict."""
    # Pick genre family
    genre_names = _pick_n(GENRES, random.randint(1, 4))
    primary_genre = genre_names[0]

    # Generate unique tmdb_id
    while True:
        tmdb_id = _gen_id()
        if tmdb_id not in used_ids:
            used_ids.add(tmdb_id)
            break

    # Title
    first = _pick(FIRST_NAMES)
    last = _pick(LAST_NAMES)
    noun = _pick(NOUNS)
    word = _pick(WORDS)
    city = _pick(CITIES)
    profession = _pick(PROFESSIONS)
    pronoun = _pick(PRONOUNS)
    adj = _pick(ADJECTIVES)

    # Try to use genre template, with fallback
    templates = TITLE_TEMPLATES.get(primary_genre, ["The {noun} of {city}"])
    title = _pick(templates).format(
        first=first, last=last, noun=noun,
        word=word, city=city,
    )

    # Year — weighted toward recent decades
    year_ranges = [(1970, 1979), (1980, 1989), (1990, 1999), (2000, 2009), (2010, 2019), (2020, 2024)]
    weights = [5, 8, 12, 15, 22, 10]
    chosen_range = random.choices(year_ranges, weights=weights, k=1)[0]
    year = random.randint(chosen_range[0], chosen_range[1])

    release_date = _gen_date(year)

    # Rating — correlated with year (newer movies slightly higher avg)
    base = 6.5 if year < 2000 else 7.0
    vote_average = round(random.gauss(base, 1.3), 1)
    vote_average = max(4.5, min(9.6, vote_average))

    vote_count = random.randint(50, 25_000) if year < 2010 else random.randint(200, 35_000)

    popularity = round(random.gauss(25, 20), 1)
    popularity = max(3.0, min(98.0, popularity))

    runtime = random.randint(85, 180)

    budget = random.randint(1_000_000, 200_000_000) if year > 1990 else random.randint(100_000, 50_000_000)
    revenue = int(budget * random.uniform(0.4, 3.5)) if random.random() > 0.15 else 0

    # Overview — build from genre template
    overview_template = _pick(OVERVIEWS.get(primary_genre, OVERVIEWS["Drama"]))
    overview = overview_template.format(
        first=first, last=last, noun=noun.lower(),
        city=city, profession=profession, pronoun=pronoun,
    )
    # Add one more sentence for variety
    extras = [
        f" But {pronoun} soon realizes nothing is as it seems.",
        f" What {pronoun} doesn't know could change everything.",
        f" Along the way, {pronoun} discovers the true meaning of {_pick(['sacrifice', 'courage', 'love', 'trust', 'hope', 'friendship'])}.",
        f" Time is running out, and the stakes have never been higher.",
        f" Together with an unlikely ally, {pronoun} must face the truth.",
        f" The journey will test {pronoun} in ways {pronoun} never imagined.",
    ]
    overview += " " + _pick(extras)

    # Genres as dicts
    genres = [{"value": g} for g in genre_names]

    # Keywords
    kw_pool = KEYWORDS.get(primary_genre, ["character-driven", "compelling", "emotional"])
    keywords = _pick_n(kw_pool, random.randint(3, 6))
    # Add some cross-genre keywords
    cross_kw = _pick_n(sum(KEYWORDS.values(), []), random.randint(0, 2))
    keywords = list(set(keywords + cross_kw))

    # Directors (1-2)
    num_directors = random.choices([1, 2], weights=[0.85, 0.15], k=1)[0]
    directors = []
    for _ in range(num_directors):
        d_first = _pick(FIRST_NAMES)
        d_last = _pick(LAST_NAMES)
        directors.append({
            "tmdb_id": _gen_id(),
            "name": f"{d_first} {d_last}",
            "role": "Director",
            "popularity": round(random.gauss(20, 12), 1),
            "profile_path": "",
        })

    # Actors (3-8)
    num_actors = random.randint(3, 8)
    actors = []
    used_actor_names: set[str] = set()
    for d in directors:
        used_actor_names.add(d["name"])
    for _ in range(num_actors):
        while True:
            a_first = _pick(FIRST_NAMES)
            a_last = _pick(LAST_NAMES)
            a_name = f"{a_first} {a_last}"
            if a_name not in used_actor_names:
                used_actor_names.add(a_name)
                break
        actors.append({
            "tmdb_id": _gen_id(),
            "name": a_name,
            "role": "Actor",
            "character": "",
            "popularity": round(random.gauss(18, 14), 1),
            "profile_path": "",
        })

    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "overview": overview,
        "release_date": release_date,
        "genres": genres,
        "vote_average": vote_average,
        "vote_count": vote_count,
        "popularity": popularity,
        "poster_path": "",
        "backdrop_path": "",
        "tagline": "",
        "runtime": runtime,
        "budget": budget,
        "revenue": revenue,
        "directors": directors,
        "actors": actors,
        "keywords": keywords,
        "language": "en",
    }


# ── Real movies (preserved from pipeline.py run_sample()) ──────────────────

REAL_MOVIES = [
    {
        "tmdb_id": 27205, "title": "Inception",
        "overview": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        "release_date": "2010-07-15",
        "genres": [{"value": "Action"}, {"value": "Science Fiction"}, {"value": "Adventure"}],
        "vote_average": 8.4, "vote_count": 35000, "popularity": 95.0,
        "backdrop_path": "/8ZTVqvKGkA28l427CMGkYRxFf7n.jpg",
        "poster_path": "/9gk7adHYeDWC0GZ2hFL4GZNG5wv.jpg",
        "directors": [{"tmdb_id": 525, "name": "Christopher Nolan", "role": "Director", "popularity": 60.0}],
        "actors": [
            {"tmdb_id": 6193, "name": "Leonardo DiCaprio", "role": "Actor", "popularity": 70.0},
            {"tmdb_id": 2524, "name": "Tom Hardy", "role": "Actor", "popularity": 55.0},
            {"tmdb_id": 27578, "name": "Ken Watanabe", "role": "Actor", "popularity": 30.0},
        ],
        "keywords": ["dream", "heist", "mind-bending", "architecture", "subconscious"],
        "runtime": 148, "budget": 160000000, "revenue": 836000000, "language": "en",
    },
    {
        "tmdb_id": 155, "title": "The Dark Knight",
        "overview": "Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations.",
        "release_date": "2008-07-16",
        "genres": [{"value": "Action"}, {"value": "Crime"}, {"value": "Drama"}, {"value": "Thriller"}],
        "vote_average": 8.5, "vote_count": 32000, "popularity": 90.0,
        "backdrop_path": "/nMKdUUepR0i5zn0y1T4CsSB5ezu.jpg",
        "poster_path": "/qJ2tW6WMUDs911OhJGghJpNaJrO.jpg",
        "directors": [{"tmdb_id": 525, "name": "Christopher Nolan", "role": "Director", "popularity": 60.0}],
        "actors": [
            {"tmdb_id": 3894, "name": "Christian Bale", "role": "Actor", "popularity": 50.0},
            {"tmdb_id": 1810, "name": "Heath Ledger", "role": "Actor", "popularity": 40.0},
            {"tmdb_id": 126169, "name": "Aaron Eckhart", "role": "Actor", "popularity": 25.0},
        ],
        "keywords": ["superhero", "vigilante", "chaos", "gritty", "noir"],
        "runtime": 152, "budget": 185000000, "revenue": 1006000000, "language": "en",
    },
    {
        "tmdb_id": 680, "title": "Pulp Fiction",
        "overview": "A burger-loving hit man, his philosophical partner, a drug-addled gangster's moll and a washed-up boxer converge in this sprawling, comedic crime caper.",
        "release_date": "1994-10-14",
        "genres": [{"value": "Crime"}, {"value": "Thriller"}],
        "vote_average": 8.5, "vote_count": 27000, "popularity": 75.0,
        "backdrop_path": "/suaEOtk1N1sgg2M7M5BVpFfqu3T.jpg",
        "poster_path": "/d5iIlFn5s0ImszYzBPbMq8Jdd5S.jpg",
        "directors": [{"tmdb_id": 138, "name": "Quentin Tarantino", "role": "Director", "popularity": 55.0}],
        "actors": [
            {"tmdb_id": 8891, "name": "John Travolta", "role": "Actor", "popularity": 45.0},
            {"tmdb_id": 139, "name": "Samuel L. Jackson", "role": "Actor", "popularity": 60.0},
            {"tmdb_id": 2231, "name": "Uma Thurman", "role": "Actor", "popularity": 40.0},
        ],
        "keywords": ["non-linear", "dark comedy", "hitman", "crime", "cult classic"],
        "runtime": 154, "budget": 8000000, "revenue": 213000000, "language": "en",
    },
    {
        "tmdb_id": 550, "title": "Fight Club",
        "overview": "An insomniac office worker and a devil-may-care soap maker form an underground fight club that evolves into much more.",
        "release_date": "1999-10-15",
        "genres": [{"value": "Drama"}],
        "vote_average": 8.4, "vote_count": 28000, "popularity": 80.0,
        "backdrop_path": "/hZkgoQYus5L7pGE1g5eQ7JFwRYT.jpg",
        "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "directors": [{"tmdb_id": 7467, "name": "David Fincher", "role": "Director", "popularity": 50.0}],
        "actors": [
            {"tmdb_id": 819, "name": "Brad Pitt", "role": "Actor", "popularity": 65.0},
            {"tmdb_id": 287, "name": "Edward Norton", "role": "Actor", "popularity": 40.0},
            {"tmdb_id": 1283, "name": "Helena Bonham Carter", "role": "Actor", "popularity": 35.0},
        ],
        "keywords": ["insomnia", "alter ego", "cult", "mind-bending", "twist ending"],
        "runtime": 139, "budget": 63000000, "revenue": 101000000, "language": "en",
    },
    {
        "tmdb_id": 238, "title": "The Godfather",
        "overview": "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant youngest son.",
        "release_date": "1972-03-14",
        "genres": [{"value": "Drama"}, {"value": "Crime"}],
        "vote_average": 8.7, "vote_count": 20000, "popularity": 85.0,
        "backdrop_path": "/tmU7GeKVybMWFButWEGl2M4GeiP.jpg",
        "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
        "directors": [{"tmdb_id": 1776, "name": "Francis Ford Coppola", "role": "Director", "popularity": 45.0}],
        "actors": [
            {"tmdb_id": 3084, "name": "Marlon Brando", "role": "Actor", "popularity": 35.0},
            {"tmdb_id": 1158, "name": "Al Pacino", "role": "Actor", "popularity": 55.0},
            {"tmdb_id": 3085, "name": "James Caan", "role": "Actor", "popularity": 25.0},
        ],
        "keywords": ["mafia", "family", "crime", "classic", "organized crime"],
        "runtime": 175, "budget": 6000000, "revenue": 250000000, "language": "en",
    },
    {
        "tmdb_id": 278, "title": "The Shawshank Redemption",
        "overview": "A banker convicted of uxoricide forms a friendship over a quarter century with a hardened convict, while maintaining his innocence and trying to escape.",
        "release_date": "1994-09-23",
        "genres": [{"value": "Drama"}],
        "vote_average": 8.7, "vote_count": 26000, "popularity": 88.0,
        "backdrop_path": "/z6q2Qj6CZ8FuajsdNv4pF1kNTk4.jpg",
        "poster_path": "/9cqNxx0GxF0bflZmeSMuL5tnGzO.jpg",
        "directors": [{"tmdb_id": 1106, "name": "Frank Darabont", "role": "Director", "popularity": 20.0}],
        "actors": [
            {"tmdb_id": 201, "name": "Tim Robbins", "role": "Actor", "popularity": 30.0},
            {"tmdb_id": 202, "name": "Morgan Freeman", "role": "Actor", "popularity": 60.0},
        ],
        "keywords": ["prison", "friendship", "hope", "escape", "redemption"],
        "runtime": 142, "budget": 25000000, "revenue": 73300000, "language": "en",
    },
    {
        "tmdb_id": 244786, "title": "Whiplash",
        "overview": "Under the direction of a ruthless instructor, a talented young drummer begins to pursue perfection at any cost.",
        "release_date": "2014-10-10",
        "genres": [{"value": "Drama"}, {"value": "Music"}],
        "vote_average": 8.4, "vote_count": 15000, "popularity": 50.0,
        "backdrop_path": "/6O1mO0XpImXy3AYp9Ioh0arTqdi.jpg",
        "poster_path": "/7fn621jOHwUQFQHqJYK0NEjwcIR.jpg",
        "directors": [{"tmdb_id": 136495, "name": "Damien Chazelle", "role": "Director", "popularity": 30.0}],
        "actors": [
            {"tmdb_id": 156476, "name": "Miles Teller", "role": "Actor", "popularity": 35.0},
            {"tmdb_id": 16861, "name": "J.K. Simmons", "role": "Actor", "popularity": 40.0},
        ],
        "keywords": ["music", "jazz", "drumming", "obsession", "teacher-student"],
        "runtime": 106, "budget": 3300000, "revenue": 49000000, "language": "en",
    },
    {
        "tmdb_id": 157336, "title": "Interstellar",
        "overview": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        "release_date": "2014-11-05",
        "genres": [{"value": "Science Fiction"}, {"value": "Adventure"}, {"value": "Drama"}],
        "vote_average": 8.4, "vote_count": 34000, "popularity": 92.0,
        "backdrop_path": "/rAiYTfKGqDXaqyHwEZ4Bq2SJwYL.jpg",
        "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "directors": [{"tmdb_id": 525, "name": "Christopher Nolan", "role": "Director", "popularity": 60.0}],
        "actors": [
            {"tmdb_id": 10297, "name": "Matthew McConaughey", "role": "Actor", "popularity": 50.0},
            {"tmdb_id": 83002, "name": "Anne Hathaway", "role": "Actor", "popularity": 45.0},
            {"tmdb_id": 1892, "name": "Matt Damon", "role": "Actor", "popularity": 55.0},
        ],
        "keywords": ["space", "wormhole", "survival", "time dilation", "family"],
        "runtime": 169, "budget": 165000000, "revenue": 730000000, "language": "en",
    },
    {
        "tmdb_id": 106646, "title": "The Wolf of Wall Street",
        "overview": "Based on the true story of Jordan Belfort, from his rise to a wealthy stock-broker living the high life to his fall involving crime, corruption and the federal government.",
        "release_date": "2013-12-25",
        "genres": [{"value": "Crime"}, {"value": "Comedy"}, {"value": "Drama"}],
        "vote_average": 8.0, "vote_count": 23000, "popularity": 70.0,
        "backdrop_path": "/aKZz5tLe5pT7iHOYQJTC4fEKeEQ.jpg",
        "poster_path": "/34m2tyKAY9ahYBA6S4Mxnf4txmS.jpg",
        "directors": [{"tmdb_id": 37, "name": "Martin Scorsese", "role": "Director", "popularity": 50.0}],
        "actors": [
            {"tmdb_id": 6193, "name": "Leonardo DiCaprio", "role": "Actor", "popularity": 70.0},
            {"tmdb_id": 11196, "name": "Jonah Hill", "role": "Actor", "popularity": 35.0},
            {"tmdb_id": 6384, "name": "Margot Robbie", "role": "Actor", "popularity": 55.0},
        ],
        "keywords": ["wall street", "excess", "true story", "corruption", "drugs"],
        "runtime": 180, "budget": 100000000, "revenue": 392000000, "language": "en",
    },
    {
        "tmdb_id": 77338, "title": "The Intouchables",
        "overview": "After he becomes a quadriplegic from a paragliding accident, an aristocrat hires a young man from the projects to be his caregiver.",
        "release_date": "2011-11-02",
        "genres": [{"value": "Drama"}, {"value": "Comedy"}],
        "vote_average": 8.3, "vote_count": 17000, "popularity": 55.0,
        "backdrop_path": "/ihWaJZC4Lk6qGMm7tJ7rvEniBfT.jpg",
        "poster_path": "/1QU7HKgsQbGpzsJbOdHCwtkM3Qa.jpg",
        "directors": [{"tmdb_id": 64573, "name": "Olivier Nakache", "role": "Director", "popularity": 15.0}],
        "actors": [
            {"tmdb_id": 24045, "name": "François Cluzet", "role": "Actor", "popularity": 20.0},
            {"tmdb_id": 193652, "name": "Omar Sy", "role": "Actor", "popularity": 25.0},
        ],
        "keywords": ["friendship", "disability", "true story", "uplifting", "heartwarming"],
        "runtime": 112, "budget": 12000000, "revenue": 426000000, "language": "en",
    },
    {
        "tmdb_id": 489, "title": "Good Will Hunting",
        "overview": "Will Hunting, a janitor at M.I.T., has a gift for mathematics, but needs help from a psychologist to find direction in his life.",
        "release_date": "1997-12-05",
        "genres": [{"value": "Drama"}],
        "vote_average": 8.1, "vote_count": 12000, "popularity": 45.0,
        "backdrop_path": "/bE2oGBLWNYKIPRY7GhkIP7FPZfi.jpg",
        "poster_path": "/bABCBKYBK7A5G1x0FzoeYDfD5cY.jpg",
        "directors": [{"tmdb_id": 777, "name": "Gus Van Sant", "role": "Director", "popularity": 25.0}],
        "actors": [
            {"tmdb_id": 1892, "name": "Matt Damon", "role": "Actor", "popularity": 55.0},
            {"tmdb_id": 235, "name": "Robin Williams", "role": "Actor", "popularity": 50.0},
            {"tmdb_id": 1893, "name": "Ben Affleck", "role": "Actor", "popularity": 45.0},
        ],
        "keywords": ["genius", "therapy", "mathematics", "coming of age", "friendship"],
        "runtime": 126, "budget": 10000000, "revenue": 225000000, "language": "en",
    },
    {
        "tmdb_id": 769, "title": "GoodFellas",
        "overview": "The story of Henry Hill and his life in the mafia, covering his relationship with his wife Karen Hill and his mob partners.",
        "release_date": "1990-09-12",
        "genres": [{"value": "Crime"}, {"value": "Drama"}],
        "vote_average": 8.4, "vote_count": 13000, "popularity": 50.0,
        "backdrop_path": "/sw7mordbZxgITU877yTpZCud90M.jpg",
        "poster_path": "/aKuFiU82s5ISJDxUbBs8Iq0d5f5.jpg",
        "directors": [{"tmdb_id": 37, "name": "Martin Scorsese", "role": "Director", "popularity": 50.0}],
        "actors": [
            {"tmdb_id": 380, "name": "Robert De Niro", "role": "Actor", "popularity": 60.0},
            {"tmdb_id": 1146, "name": "Ray Liotta", "role": "Actor", "popularity": 25.0},
            {"tmdb_id": 1147, "name": "Joe Pesci", "role": "Actor", "popularity": 30.0},
        ],
        "keywords": ["mafia", "crime", "rise and fall", "true story", "organized crime"],
        "runtime": 146, "budget": 25000000, "revenue": 46800000, "language": "en",
    },
    {
        "tmdb_id": 11216, "title": "Cinema Paradiso",
        "overview": "A filmmaker recalls his childhood when falling in love with the pictures at the cinema of his home village and forms a deep friendship with the cinema's projectionist.",
        "release_date": "1988-11-17",
        "genres": [{"value": "Drama"}, {"value": "Romance"}],
        "vote_average": 8.4, "vote_count": 5000, "popularity": 35.0,
        "backdrop_path": "/gUqz1Vaq4iUIEOQbGqCY6HP24o4.jpg",
        "poster_path": "/8SRj3R2gL5V3q3dQHfMmHzU4SSS.jpg",
        "directors": [{"tmdb_id": 5289, "name": "Giuseppe Tornatore", "role": "Director", "popularity": 18.0}],
        "actors": [
            {"tmdb_id": 29460, "name": "Philippe Noiret", "role": "Actor", "popularity": 22.0},
            {"tmdb_id": 29461, "name": "Salvatore Cascio", "role": "Actor", "popularity": 10.0},
        ],
        "keywords": ["cinema", "nostalgia", "friendship", "coming of age", "italy"],
        "runtime": 124, "budget": 5000000, "revenue": 12900000, "language": "en",
    },
    {
        "tmdb_id": 399566, "title": "Godzilla vs. Kong",
        "overview": "In a time when monsters walk the Earth, humanity's fight for its future sets Godzilla and Kong on a collision course.",
        "release_date": "2021-03-31",
        "genres": [{"value": "Action"}, {"value": "Science Fiction"}, {"value": "Thriller"}],
        "vote_average": 7.8, "vote_count": 9000, "popularity": 65.0,
        "backdrop_path": "/inJjDhCjfhh3RtrJWBmmDqeuSYC.jpg",
        "poster_path": "/pgqgaUx1cJb5oZQQ5v5tNARBuBk.jpg",
        "directors": [{"tmdb_id": 108231, "name": "Adam Wingard", "role": "Director", "popularity": 20.0}],
        "actors": [
            {"tmdb_id": 505, "name": "Alexander Skarsgård", "role": "Actor", "popularity": 35.0},
            {"tmdb_id": 1142, "name": "Millie Bobby Brown", "role": "Actor", "popularity": 50.0},
        ],
        "keywords": ["monster", "kaiju", "giant monster", "showdown", "epic"],
        "runtime": 113, "budget": 200000000, "revenue": 470000000, "language": "en",
    },
    {
        "tmdb_id": 419430, "title": "Get Out",
        "overview": "Chris and his girlfriend Rose go upstate to visit her parents for the weekend. At first, Chris reads the family's overly accommodating behavior as nervous attempts to deal with their daughter's interracial relationship, but as the weekend progresses, a series of increasingly disturbing discoveries lead him to a truth that he never could have imagined.",
        "release_date": "2017-02-24",
        "genres": [{"value": "Horror"}, {"value": "Mystery"}, {"value": "Thriller"}],
        "vote_average": 7.8, "vote_count": 16000, "popularity": 55.0,
        "backdrop_path": "/8Y43mQwI0BUKpQUCyIoFSKkPhPs.jpg",
        "poster_path": "/tFXcEccSQMf3lfhfXKSU9iVBpaI.jpg",
        "directors": [{"tmdb_id": 58728, "name": "Jordan Peele", "role": "Director", "popularity": 35.0}],
        "actors": [
            {"tmdb_id": 1754048, "name": "Daniel Kaluuya", "role": "Actor", "popularity": 40.0},
            {"tmdb_id": 25366, "name": "Allison Williams", "role": "Actor", "popularity": 25.0},
        ],
        "keywords": ["social thriller", "race", "horror", "mind-bending", "twist"],
        "runtime": 104, "budget": 5000000, "revenue": 255000000, "language": "en",
    },
    {
        "tmdb_id": 11, "title": "Star Wars",
        "overview": "Princess Leia is captured and held hostage by the evil Imperial forces in their effort to take over the galactic Empire. Venturesome Luke Skywalker and dashing captain Han Solo team together with the lovable robot duo R2-D2 and C-3PO to rescue the beautiful princess and restore peace and justice in the Empire.",
        "release_date": "1977-05-25",
        "genres": [{"value": "Adventure"}, {"value": "Action"}, {"value": "Science Fiction"}],
        "vote_average": 8.2, "vote_count": 19000, "popularity": 85.0,
        "backdrop_path": "/zqkmTXzjkAgXmEWLRsY4UpTWCeo.jpg",
        "poster_path": "/6FfCtAuVAW8XJjZ7eWeLibRLWTw.jpg",
        "directors": [{"tmdb_id": 1, "name": "George Lucas", "role": "Director", "popularity": 55.0}],
        "actors": [
            {"tmdb_id": 2, "name": "Mark Hamill", "role": "Actor", "popularity": 40.0},
            {"tmdb_id": 3, "name": "Harrison Ford", "role": "Actor", "popularity": 65.0},
            {"tmdb_id": 4, "name": "Carrie Fisher", "role": "Actor", "popularity": 35.0},
        ],
        "keywords": ["space opera", "lightsaber", "the force", "rebellion", "empire"],
        "runtime": 121, "budget": 11000000, "revenue": 775000000, "language": "en",
    },
]


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print(f"Generating 1000 movies -> {OUT_PATH} ...")

    used_ids: set[int] = {m["tmdb_id"] for m in REAL_MOVIES}
    synthetic_needed = 1000 - len(REAL_MOVIES)

    synthetic = []
    for i in range(synthetic_needed):
        movie = generate_movie(used_ids)
        synthetic.append(movie)
        if (i + 1) % 200 == 0:
            print(f"  Generated {i + 1}/{synthetic_needed} synthetic movies...")

    all_movies = list(REAL_MOVIES) + synthetic
    random.shuffle(all_movies)  # Real movies interleaved, not lumped at top

    # Stats
    genre_counts = {}
    for m in all_movies:
        for g in m["genres"]:
            genre_counts[g["value"]] = genre_counts.get(g["value"], 0) + 1

    print(f"\nDone! {len(all_movies)} movies written.")
    print(f"Genre distribution:")
    for g, c in sorted(genre_counts.items(), key=lambda x: -x[1]):
        print(f"  {g}: {c} movies ({c/len(all_movies)*100:.0f}%)")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_movies, f, ensure_ascii=False, indent=2)

    size_mb = os.path.getsize(OUT_PATH) / 1_000_000
    print(f"File size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
