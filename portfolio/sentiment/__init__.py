"""Product Review Sentiment Analyzer — AI-powered sentiment analysis on Amazon reviews."""

from .models import ProductSentiment, Review, ReviewSentiment
from .pipeline import get_reviews
from .analyzer import analyze_reviews, build_product_sentiment
from .render import render_sentiment_tab, SENTIMENT_CSS

__all__ = [
    "ProductSentiment",
    "Review",
    "ReviewSentiment",
    "get_reviews",
    "analyze_reviews",
    "build_product_sentiment",
    "render_sentiment_tab",
    "SENTIMENT_CSS",
]
