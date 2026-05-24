"""Pipeline: fetch Yelp reviews from HuggingFace and group into 1 000 businesses.

Uses ``yelp_review_full`` (5-star labels, real review text) via the ``datasets``
library.  Reviews are shuffled and partitioned into 1 000 equal-sized groups —
each group becomes a "product" (business) for the sentiment analyzer.
"""

import json
import os
import random

from .models import Review

_DATASET_NAME = "yelp_review_full"
_NUM_BUSINESSES = 1000
_CACHE_PATH = os.path.join(os.path.dirname(__file__), "_sampled_reviews.json")
_SEED = 42


def _download_and_group() -> list[Review]:
    """Download *yelp_review_full*, shuffle, and split into 1 000 businesses."""
    from datasets import load_dataset

    # Load the training split (650 000 reviews)
    ds = load_dataset(_DATASET_NAME, split="train")
    total = len(ds)

    # Shuffle indices deterministically
    rng = random.Random(_SEED)
    indices = list(range(total))
    rng.shuffle(indices)

    # Take enough reviews so each business gets at least 10
    needed = _NUM_BUSINESSES * 10
    indices = indices[:needed]

    reviews: list[Review] = []
    business_names, business_domains = _build_business_names(_NUM_BUSINESSES, _SEED)
    for biz_idx in range(_NUM_BUSINESSES):
        biz_id = f"B{biz_idx:04d}"
        biz_name = business_names[biz_idx]

        for r in range(10):
            row_idx = indices[biz_idx * 10 + r]
            row = ds[int(row_idx)]
            stars = int(row["label"]) + 1  # dataset labels are 0-4 → 1-5 stars
            text = row["text"].replace("\n", " ").strip()

            reviews.append(Review(
                review_id=f"R{biz_idx:04d}_{r:02d}",
                product_id=biz_id,
                title=biz_name,
                text=text,
                rating=float(stars),
                helpful_votes=0,
            ))

    # Cache to disk (include domain per business for quick lookup)
    serialised = [
        {
            "review_id": r.review_id,
            "product_id": r.product_id,
            "title": r.title,
            "text": r.text,
            "rating": r.rating,
            "helpful_votes": r.helpful_votes,
        }
        for r in reviews
    ]
    # Also cache the domain index: product_id → domain
    domain_map = {f"B{b:04d}": business_domains[b] for b in range(_NUM_BUSINESSES)}
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"reviews": serialised, "domains": domain_map}, f, ensure_ascii=False)

    return reviews


def get_business_domains() -> dict[str, str]:
    """Return {product_id: domain} for all 1 000 businesses.

    Loads from cache if available, otherwise triggers a fresh download.
    """
    if os.path.exists(_CACHE_PATH):
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and "domains" in raw:
            return raw["domains"]
    # Force rebuild with domain-aware cache
    _download_and_group()
    return get_business_domains()


_DOMAINS = [
    "Grill", "Café", "Bistro", "Diner", "Pizzeria", "Kitchen", "Bakery",
    "Restaurant", "Sushi Bar", "Steakhouse", "Tavern", "Brewery", "Pub",
    "Deli", "Patio", "Lounge", "Eatery", "Chop House", "BBQ",
    "Oyster Bar", "Noodle House", "Ramen Shop", "Taco Stand", "Burrito Bar",
    "Gelato Shop", "Coffee House", "Tea Room", "Wine Bar", "Cocktail Bar",
]


def _build_business_names(n: int = 1000, seed: int = 42) -> tuple[list[str], list[str]]:
    """Generate *n* realistic restaurant names and their domains.

    Returns (names, domains) — parallel lists where domain is the business
    type (e.g. "Grill", "Café", "Pizzeria").
    """
    rng = random.Random(seed)

    prefixes = [
        "The", "Blue", "Red", "Green", "Golden", "Silver", "Black", "White",
        "Little", "Big", "Happy", "Lucky", "Royal", "Crystal", "Diamond",
        "Pearl", "Ocean", "Mountain", "Urban", "Vintage", "Rustic", "Sunset",
        "Sunrise", "Harbor", "Copper", "Iron", "Velvet", "Amber", "Jade",
    ]
    nouns = [
        "Oak", "Maple", "Pine", "Cedar", "Rose", "Lily", "Harbor", "Summit",
        "Valley", "Garden", "River", "Lake", "Moon", "Star", "Sun", "Dragon",
        "Phoenix", "Eagle", "Lion", "Tiger", "Willow", "Birch", "Sage",
        "Thyme", "Basil", "Olive", "Fig", "Berry", "Plum",
    ]
    types = _DOMAINS
    locations = [
        "on Main", "Downtown", "on 5th", "on Elm", "Bayside", "Midtown",
        "Uptown", "Waterfront", "Market", "Plaza", "on Broadway", "Village",
        "West End", "East Side", "Harbor", "", "", "", "", "", "",
    ]

    # Build all combos, shuffle, take *n*
    combos: list[tuple[str, str]] = []
    for prefix in prefixes:
        for noun in nouns:
            for typ in types:
                combo = (f"{prefix} {noun} {typ}", typ)
                combos.append(combo)

    rng.shuffle(combos)
    names: list[str] = []
    domains: list[str] = []
    for i, (name, domain) in enumerate(combos):
        if len(names) >= n:
            break
        loc = rng.choice(locations)
        if loc:
            name = f"{name} {loc}"
        names.append(name)
        domains.append(domain)

    return names, domains


def get_reviews(force_refresh: bool = False) -> list[Review]:
    """Return the sampled reviews (cached after first download from HuggingFace).

    Set *force_refresh* to ``True`` to re-download and re-sample.
    """
    if not force_refresh and os.path.exists(_CACHE_PATH):
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        reviews_raw = raw["reviews"] if isinstance(raw, dict) and "reviews" in raw else raw
        return [
            Review(
                review_id=r["review_id"],
                product_id=r["product_id"],
                title=r["title"],
                text=r["text"],
                rating=float(r["rating"]),
                helpful_votes=int(r.get("helpful_votes", 0)),
            )
            for r in reviews_raw
        ]

    return _download_and_group()
