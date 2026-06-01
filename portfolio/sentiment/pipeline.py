"""Pipeline: fetch review datasets and group them into compact UI samples.

Uses ``yelp_review_full`` (5-star labels, real review text) via the ``datasets``
library.  Reviews are shuffled and partitioned into 1 000 equal-sized groups —
each group becomes a "product" (business) for the sentiment analyzer.

Amazon mode streams public Amazon Reviews 2023 JSONL archives from Hugging
Face. It stores a small local sample of 1,000 Electronics products only, with
category/subcategory metadata.
"""

import json
import os
import random
import urllib.request

from .models import Review

_DATASET_NAME = "yelp_review_full"
_NUM_BUSINESSES = 1000
_NUM_AMAZON_PRODUCTS = 1000
_REVIEWS_PER_AMAZON_PRODUCT = 6
_CACHE_PATH = os.path.join(os.path.dirname(__file__), "_sampled_reviews.json")
_AMAZON_CACHE_PATH = os.path.join(os.path.dirname(__file__), "_amazon_sampled_reviews.json")
_SEED = 42

_AMAZON_HF_BASE = "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw"
_AMAZON_REVIEW_FILES = {
    "Electronics": "Electronics",
}


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
                category="Yelp Business",
                subcategory=business_domains[biz_idx],
                source="Yelp",
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
            "category": r.category,
            "subcategory": r.subcategory,
            "source": r.source,
        }
        for r in reviews
    ]
    # Also cache the domain index: product_id → domain
    domain_map = {f"B{b:04d}": business_domains[b] for b in range(_NUM_BUSINESSES)}
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"reviews": serialised, "domains": domain_map}, f, ensure_ascii=False)

    return reviews


def _read_cache(cache_path: str) -> tuple[list[Review], dict[str, str], dict[str, dict[str, str]]]:
    with open(cache_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    reviews_raw = raw["reviews"] if isinstance(raw, dict) and "reviews" in raw else raw
    reviews = [
        Review(
            review_id=r["review_id"],
            product_id=r["product_id"],
            title=r["title"],
            text=r["text"],
            rating=float(r["rating"]),
            helpful_votes=int(r.get("helpful_votes", 0)),
            category=str(r.get("category", "")),
            subcategory=str(r.get("subcategory", "")),
            source=str(r.get("source", "Yelp")),
        )
        for r in reviews_raw
    ]

    domains = raw.get("domains", {}) if isinstance(raw, dict) else {}
    metadata = raw.get("metadata", {}) if isinstance(raw, dict) else {}
    if not metadata:
        metadata = {
            r.product_id: {
                "category": r.category or domains.get(r.product_id, ""),
                "subcategory": r.subcategory or domains.get(r.product_id, ""),
                "source": r.source,
            }
            for r in reviews
        }
    return reviews, domains, metadata


def get_business_domains(source: str = "yelp") -> dict[str, str]:
    """Return {product_id: domain} for all sampled Yelp businesses.

    Loads from cache if available, otherwise triggers a fresh download.
    """
    if source == "amazon":
        return {
            pid: values.get("subcategory") or values.get("category", "")
            for pid, values in get_product_metadata("amazon").items()
        }
    if os.path.exists(_CACHE_PATH):
        _, domains, _ = _read_cache(_CACHE_PATH)
        if domains:
            return domains
    # Force rebuild with domain-aware cache
    _download_and_group()
    return get_business_domains()


def get_product_metadata(source: str = "yelp") -> dict[str, dict[str, str]]:
    """Return product metadata used by UI filters."""
    if source == "amazon":
        if not os.path.exists(_AMAZON_CACHE_PATH):
            _download_amazon_sample()
        _, _, metadata = _read_cache(_AMAZON_CACHE_PATH)
        return metadata

    if not os.path.exists(_CACHE_PATH):
        _download_and_group()
    _, domains, metadata = _read_cache(_CACHE_PATH)
    if metadata:
        return metadata
    return {
        pid: {"category": "Yelp Business", "subcategory": domain, "source": "Yelp"}
        for pid, domain in domains.items()
    }


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
        reviews, _, _ = _read_cache(_CACHE_PATH)
        return reviews

    return _download_and_group()


def _amazon_subcategory(title: str, category: str) -> str:
    lower = title.lower()
    keyword_groups = [
        ("Headphones & Audio", ("headphone", "earbud", "speaker", "audio", "bluetooth")),
        ("Chargers & Cables", ("charger", "cable", "adapter", "usb", "power")),
        ("Cases & Covers", ("case", "cover", "sleeve", "protector")),
        ("Skin Care", ("cream", "serum", "lotion", "moistur", "cleanser")),
        ("Hair Care", ("shampoo", "conditioner", "hair", "brush")),
        ("Kitchen Tools", ("knife", "pan", "pot", "bowl", "spatula", "kitchen")),
        ("Storage & Organization", ("storage", "organizer", "shelf", "rack", "container")),
        ("Outdoor Gear", ("tent", "camp", "hiking", "outdoor", "backpack")),
        ("Toys & Games", ("toy", "game", "puzzle", "doll", "lego")),
        ("Books & Reading", ("book", "novel", "guide", "paperback", "kindle")),
    ]
    for label, keywords in keyword_groups:
        if any(keyword in lower for keyword in keywords):
            return label
    return f"{category} General"


def _amazon_review_url(slug: str) -> str:
    return f"{_AMAZON_HF_BASE}/review_categories/{slug}.jsonl"


def _amazon_meta_url(slug: str) -> str:
    return f"{_AMAZON_HF_BASE}/meta_categories/meta_{slug}.jsonl"


def _hydrate_amazon_titles(
    slug: str,
    category: str,
    selected_asins: set[str],
    metadata: dict[str, dict[str, str]],
) -> None:
    """Fill product titles/subcategories from Amazon metadata when available."""
    if not selected_asins:
        return
    remaining = set(selected_asins)
    try:
        with urllib.request.urlopen(_amazon_meta_url(slug), timeout=60) as response:
            for line in response:
                if not remaining:
                    break
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                asin = str(row.get("parent_asin") or "").strip()
                if asin not in remaining or asin not in metadata:
                    continue
                title = str(row.get("title") or "").strip()
                if title:
                    metadata[asin]["title"] = title[:120]
                    metadata[asin]["subcategory"] = _amazon_subcategory(title, category)
                remaining.remove(asin)
    except Exception:
        return


def _download_amazon_sample() -> list[Review]:
    """Download a compact Amazon Customer Reviews sample and cache it locally.

    The source files are public JSONL archives from Amazon Reviews 2023 on
    Hugging Face. We stream category files and keep only 1,000 products plus a
    few reviews per product to avoid storing the full corpus.
    """
    per_category = max(1, _NUM_AMAZON_PRODUCTS // len(_AMAZON_REVIEW_FILES))
    metadata: dict[str, dict[str, str]] = {}
    reviews_by_asin: dict[str, list[Review]] = {}

    for category, slug in _AMAZON_REVIEW_FILES.items():
        category_count = 0
        selected_asins: set[str] = set()
        try:
            with urllib.request.urlopen(_amazon_review_url(slug), timeout=60) as response:
                for line in response:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    asin = str(row.get("parent_asin") or row.get("asin") or "").strip()
                    text = str(row.get("text") or "").replace("\n", " ").strip()
                    if not asin or len(text) < 40:
                        continue
                    if asin not in metadata:
                        if category_count >= per_category or len(metadata) >= _NUM_AMAZON_PRODUCTS:
                            continue
                        product_id = f"A{len(metadata):04d}"
                        fallback_title = f"{category} Product {asin[-6:]}"
                        metadata[asin] = {
                            "product_id": product_id,
                            "title": fallback_title,
                            "category": category,
                            "subcategory": _amazon_subcategory(fallback_title, category),
                            "source": "Amazon",
                        }
                        reviews_by_asin[asin] = []
                        selected_asins.add(asin)
                        category_count += 1

                    bucket = reviews_by_asin[asin]
                    if len(bucket) >= _REVIEWS_PER_AMAZON_PRODUCT:
                        continue
                    meta = metadata[asin]
                    review_title = str(row.get("title") or "").strip()
                    if review_title:
                        text = f"{review_title}. {text}"
                    bucket.append(Review(
                        review_id=f"{meta['product_id']}_{len(bucket):02d}",
                        product_id=meta["product_id"],
                        title=meta["title"],
                        text=text,
                        rating=float(row.get("rating") or 0.0),
                        helpful_votes=int(row.get("helpful_vote") or 0),
                        category=meta["category"],
                        subcategory=meta["subcategory"],
                        source="Amazon",
                    ))
                    if category_count >= per_category and all(
                        len(reviews_by_asin[asin]) >= 1
                        for asin, meta in metadata.items()
                        if meta["category"] == category
                    ):
                        break
        except Exception:
            continue
        _hydrate_amazon_titles(slug, category, selected_asins, metadata)
        if len(metadata) >= _NUM_AMAZON_PRODUCTS:
            break

    reviews = [review for bucket in reviews_by_asin.values() for review in bucket]
    if not reviews:
        raise RuntimeError("Amazon review sample could not be downloaded.")

    titles_by_product_id = {meta["product_id"]: meta["title"] for meta in metadata.values()}
    subcategories_by_product_id = {meta["product_id"]: meta["subcategory"] for meta in metadata.values()}
    for review in reviews:
        review.title = titles_by_product_id.get(review.product_id, review.title)
        review.subcategory = subcategories_by_product_id.get(review.product_id, review.subcategory)

    product_metadata = {
        meta["product_id"]: {
            "category": meta["category"],
            "subcategory": meta["subcategory"],
            "source": "Amazon",
        }
        for asin, meta in metadata.items()
        if reviews_by_asin.get(asin)
    }
    domains = {pid: data["subcategory"] for pid, data in product_metadata.items()}
    serialised = [
        {
            "review_id": r.review_id,
            "product_id": r.product_id,
            "title": r.title,
            "text": r.text,
            "rating": r.rating,
            "helpful_votes": r.helpful_votes,
            "category": r.category,
            "subcategory": r.subcategory,
            "source": r.source,
        }
        for r in reviews
    ]
    with open(_AMAZON_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"reviews": serialised, "domains": domains, "metadata": product_metadata},
            f,
            ensure_ascii=False,
        )
    return reviews


def get_amazon_reviews(force_refresh: bool = False) -> list[Review]:
    """Return the compact Amazon Customer Reviews sample."""
    if not force_refresh and os.path.exists(_AMAZON_CACHE_PATH):
        reviews, _, _ = _read_cache(_AMAZON_CACHE_PATH)
        return reviews
    return _download_amazon_sample()
