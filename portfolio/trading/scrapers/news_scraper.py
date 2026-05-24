"""World news scraper for market-impacting headlines.

Fetches recent financial/market news from multiple sources to feed
into the Risk/Sentiment Agent for broader market context analysis.
"""

from __future__ import annotations

import httpx

from ..models import WorldNewsItem


# Free RSS/API endpoints for financial news
NEWS_SOURCES = [
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
        "category": "markets",
    },
    {
        "name": "Reuters",
        "url": "https://www.reuters.com/arc/outboundfeeds/v3/all/?outputType=xml",
        "category": "general",
    },
    {
        "name": "CNBC",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000398",
        "category": "markets",
    },
]

# Keywords that indicate market-moving news
MARKET_MOVING_KEYWORDS = [
    "fed", "federal reserve", "interest rate", "inflation", "cpi",
    "gdp", "recession", "earnings", "merger", "acquisition",
    "ipo", "layoff", "tariff", "trade war", "sanctions",
    "oil", "energy crisis", "bank", "default", "bailout",
    "ecb", "boe", "boj", "pboc", "central bank",
    "geopolitical", "war", "conflict", "election", "policy",
    "regulation", "sec", "crypto", "bitcoin", "volatility",
    "bull", "bear", "rally", "selloff", "crash",
    "yield", "treasury", "bond", "currency", "dollar",
    "jobs", "unemployment", "payroll", "consumer", "retail",
]


def _classify_impact(headline: str) -> str:
    """Classify a headline's market impact based on keywords."""
    lower = headline.lower()

    positive_words = [
        "rally", "surge", "jump", "gain", "rise", "bull", "beat",
        "growth", "profit", "record", "upgrade", "expansion", "recovery",
        "optimism", "boost", "strong", "outperform",
    ]
    negative_words = [
        "crash", "plunge", "tumble", "selloff", "decline", "drop",
        "bear", "recession", "crisis", "downgrade", "loss", "fear",
        "warn", "risk", "turmoil", "panic", "weak", "underperform",
    ]

    pos_count = sum(1 for w in positive_words if w in lower)
    neg_count = sum(1 for w in negative_words if w in lower)

    if pos_count > neg_count:
        return "Positive"
    elif neg_count > pos_count:
        return "Negative"
    return "Neutral"


def fetch_world_news(max_items: int = 8) -> list[WorldNewsItem]:
    """Fetch world news headlines relevant to financial markets.

    Args:
        max_items: Maximum number of news items to return.

    Returns:
        List of WorldNewsItem objects. Empty on failure.
    """
    items: list[WorldNewsItem] = []

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        for source in NEWS_SOURCES:
            if len(items) >= max_items:
                break
            try:
                response = client.get(
                    source["url"],
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (compatible; TradingBot/1.0; "
                            "+https://ai-portfolio.example.com)"
                        ),
                        "Accept": "application/xml, application/rss+xml, text/xml",
                    },
                )
                if response.status_code != 200:
                    continue

                # Simple XML parsing for RSS feeds
                text = response.text
                # Extract <item> blocks
                item_blocks = text.split("<item>")[1:] if "<item>" in text else []

                for block in item_blocks:
                    if len(items) >= max_items:
                        break

                    # Extract title
                    title_match = block.split("<title>")
                    title = ""
                    if len(title_match) > 1:
                        title = title_match[1].split("</title>")[0]
                        # Decode HTML entities
                        title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                        title = title.replace("&quot;", '"').replace("&#39;", "'").replace("&apos;", "'")

                    if not title or len(title) < 10:
                        continue

                    # Check if market-moving
                    if not any(kw in title.lower() for kw in MARKET_MOVING_KEYWORDS):
                        continue

                    # Extract link
                    link = ""
                    link_match = block.split("<link>")
                    if len(link_match) > 1:
                        link = link_match[1].split("</link>")[0]

                    items.append(WorldNewsItem(
                        headline=title.strip(),
                        source=source["name"],
                        url=link.strip() if link else "",
                        impact=_classify_impact(title),
                        category=source["category"],
                        summary="",
                    ))

            except Exception:
                continue

    # If we couldn't fetch any news, provide a fallback
    if not items:
        items.append(WorldNewsItem(
            headline="Unable to fetch live news — market data feeds unavailable",
            source="System",
            impact="Neutral",
            category="system",
            summary="News scraping failed. This may be due to network issues or rate limiting.",
        ))

    return items[:max_items]
