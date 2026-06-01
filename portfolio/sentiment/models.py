"""Data models for the Product Review Sentiment Analyzer."""

from dataclasses import dataclass, field


@dataclass
class Review:
    """A single customer review for a product."""
    review_id: str
    product_id: str
    title: str
    text: str
    rating: float          # 1.0–5.0 star rating
    helpful_votes: int = 0
    category: str = ""
    subcategory: str = ""
    source: str = "Yelp"


@dataclass
class ReviewSentiment:
    """The sentiment result for one review."""
    review_id: str
    label: str             # "Positive", "Negative", or "Neutral"
    score: float           # confidence 0.0–1.0
    review_text: str       # truncated preview for display
    rating: float


@dataclass
class ProductSentiment:
    """Aggregated sentiment for a single product."""
    product_id: str
    product_title: str
    total_reviews: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    avg_rating: float
    review_sentiments: list[ReviewSentiment] = field(default_factory=list)
