"""Sentiment analyzer using a pre-trained HuggingFace transformer model."""

import os
import re
from collections import Counter

from .models import ProductSentiment, Review, ReviewSentiment

# Lightweight sentiment model fine-tuned on Twitter/review-style text
_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
_LABEL_MAP = {
    "LABEL_0": "Negative",
    "LABEL_1": "Neutral",
    "LABEL_2": "Positive",
}

# Lazily-loaded pipeline so the model only downloads when first used
_pipeline = None


def _get_pipeline():
    """Return a singleton HuggingFace text-classification pipeline."""
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline
        # Force CPU to avoid GPU memory issues in shared environments
        _pipeline = pipeline(
            "sentiment-analysis",
            model=_MODEL_NAME,
            device=-1,
            truncation=True,
            max_length=512,
        )
    return _pipeline


def analyze_reviews(reviews: list[Review]) -> list[ReviewSentiment]:
    """Run sentiment analysis on a list of reviews, returning scored results."""
    pipe = _get_pipeline()
    texts = [r.text[:512] for r in reviews]  # truncate to model max
    raw = pipe(texts, batch_size=32)

    results: list[ReviewSentiment] = []
    for r, pred in zip(reviews, raw):
        label = _LABEL_MAP.get(pred["label"], pred["label"])
        score = float(pred["score"])
        preview = r.text[:200].replace("\n", " ") + ("…" if len(r.text) > 200 else "")
        results.append(ReviewSentiment(
            review_id=r.review_id,
            label=label,
            score=score,
            review_text=preview,
            rating=r.rating,
        ))
    return results


_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "don", "now", "its", "it", "but", "and", "or",
    "if", "about", "up", "out", "this", "that", "these", "those", "i",
    "my", "me", "we", "our", "you", "your", "he", "she", "his", "her",
    "they", "them", "their", "what", "which", "who", "whom",
}


def _extract_keywords(texts: list[str], top_n: int = 4) -> list[str]:
    """Extract top bigrams/trigrams from a list of review texts."""
    all_words: list[str] = []
    for t in texts:
        words = re.findall(r"[a-zA-Z]{3,}", t.lower())
        all_words.extend(w for w in words if w not in _STOP_WORDS)

    # Count bigrams and trigrams
    bigrams = Counter(
        " ".join(all_words[i : i + 2]) for i in range(len(all_words) - 1)
    )
    trigrams = Counter(
        " ".join(all_words[i : i + 3]) for i in range(len(all_words) - 2)
    )

    combined: list[tuple[str, int]] = []
    for phrase, count in trigrams.most_common(top_n * 2):
        combined.append((phrase, count))
    for phrase, count in bigrams.most_common(top_n * 2):
        combined.append((phrase, count))

    # Deduplicate: skip a bigram if it's fully contained in an already-chosen trigram
    chosen: list[str] = []
    for phrase, _ in sorted(combined, key=lambda x: -x[1]):
        if any(phrase in c for c in chosen):
            continue
        chosen.append(phrase)
        if len(chosen) >= top_n:
            break

    return chosen


def generate_verdict(ps: ProductSentiment) -> str:
    """Synthesise an overall customer review summary from sentiment data."""
    pos_reviews = [s.review_text for s in ps.review_sentiments if s.label == "Positive"]
    neg_reviews = [s.review_text for s in ps.review_sentiments if s.label == "Negative"]

    pos_kw = _extract_keywords(pos_reviews)
    neg_kw = _extract_keywords(neg_reviews)

    # ---- Determine the verdict tone ----
    if ps.positive_pct >= 0.75:
        tone = ("overwhelmingly positive", "rave", "Highly recommended!")
    elif ps.positive_pct >= 0.5:
        tone = ("mostly positive", "praise", "Worth a try.")
    elif ps.positive_pct >= 0.35:
        tone = ("mixed", "note", "Your mileage may vary.")
    else:
        tone = ("mostly critical", "complain", "Approach with caution.")

    rating_stars = "⭐" * round(ps.avg_rating)

    # ---- Build the narrative paragraph ----
    parts: list[str] = []
    parts.append(
        f"Based on {ps.total_reviews} customer reviews ({rating_stars} {ps.avg_rating:.1f}/5 avg), "
        f"the experience at <strong>{ps.product_title}</strong> is {tone[0]}."
    )

    if pos_kw:
        kw_str = ", ".join(f"<em>{k}</em>" for k in pos_kw)
        parts.append(f"Customers {tone[1]} about {kw_str}.")

    if neg_kw:
        kw_str = ", ".join(f"<em>{k}</em>" for k in neg_kw)
        parts.append(f"However, some mention issues with {kw_str}.")

    parts.append(tone[2])

    return " ".join(parts)


def build_product_sentiment(product_reviews: list[Review]) -> ProductSentiment:
    """Aggregate review sentiments into a per-product summary."""
    sentiments = analyze_reviews(product_reviews)
    total = len(sentiments)
    pos = sum(1 for s in sentiments if s.label == "Positive")
    neg = sum(1 for s in sentiments if s.label == "Negative")
    neu = total - pos - neg
    avg_rating = sum(s.rating for s in sentiments) / total if total else 0.0

    return ProductSentiment(
        product_id=product_reviews[0].product_id,
        product_title=product_reviews[0].title,
        total_reviews=total,
        positive_pct=pos / total if total else 0,
        negative_pct=neg / total if total else 0,
        neutral_pct=neu / total if total else 0,
        avg_rating=avg_rating,
        review_sentiments=sentiments,
    )
