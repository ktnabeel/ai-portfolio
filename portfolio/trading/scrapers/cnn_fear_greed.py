"""CNN Fear & Greed Index scraper.

Scrapes https://www.cnn.com/markets/fear-and-greed to extract:
  - Current Fear & Greed value (0-100)
  - Zone classification (Extreme Fear through Extreme Greed)
  - Historical comparison values
  - Market trend description

Uses httpx for HTTP requests and BeautifulSoup for HTML parsing.
Falls back gracefully if scraping fails.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..models import FearGreedData, FearGreedZone


FEAR_GREED_URL = "https://www.cnn.com/markets/fear-and-greed"


def _classify_zone(value: int) -> FearGreedZone:
    """Classify a 0-100 value into a Fear & Greed zone."""
    if value <= 25:
        return FearGreedZone.EXTREME_FEAR
    elif value <= 40:
        return FearGreedZone.FEAR
    elif value <= 60:
        return FearGreedZone.NEUTRAL
    elif value <= 75:
        return FearGreedZone.GREED
    else:
        return FearGreedZone.EXTREME_GREED


def _extract_number(text: str) -> Optional[int]:
    """Extract the first number from a text string."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def fetch_fear_greed() -> FearGreedData:
    """Fetch the current CNN Fear & Greed Index.

    Returns:
        FearGreedData with the current value, zone, and description.

    On failure, returns a default neutral value (50) with a warning.
    """
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(
                FEAR_GREED_URL,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            response.raise_for_status()
    except Exception as e:
        return FearGreedData(
            value=50,
            zone=FearGreedZone.NEUTRAL,
            description=f"Unable to fetch CNN Fear & Greed Index: {e}. Using neutral default.",
        )

    soup = BeautifulSoup(response.text, "html.parser")

    # Try multiple strategies to find the current value
    value: Optional[int] = None
    description = ""

    # Strategy 1: Look for a prominent number (the Fear & Greed gauge typically
    # shows a big number)
    gauge_candidates = soup.find_all(
        ["div", "span"],
        class_=re.compile(r"(fear|greed|gauge|meter|score|value|index)", re.I),
    )
    for el in gauge_candidates:
        text = el.get_text(strip=True)
        num = _extract_number(text)
        if num is not None and 0 <= num <= 100:
            value = num
            break

    # Strategy 2: Fallback — find any number 0-100 near "fear" or "greed"
    if value is None:
        body_text = soup.get_text()
        # Look for patterns like "Fear & Greed Index: 65" or "65 - Greed"
        patterns = [
            r"Fear\s*[&]\s*Greed.*?(\d{1,3})",
            r"(\d{1,3})\s*[-–]\s*(Extreme\s*Fear|Fear|Neutral|Greed|Extreme\s*Greed)",
            r"(Extreme\s*Fear|Fear|Neutral|Greed|Extreme\s*Greed).*?(\d{1,3})",
        ]
        for pattern in patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                for g in groups:
                    num = _extract_number(g) if g and not g.isalpha() else None
                    if num is not None and 0 <= num <= 100:
                        value = num
                        break
            if value is not None:
                break

    # Strategy 3: Extract the page's JSON-LD or meta description for the value
    if value is None:
        for meta in soup.find_all("meta", attrs={"name": re.compile(r"(description|title)", re.I)}):
            content = meta.get("content", "")
            if "fear" in content.lower() or "greed" in content.lower():
                num = _extract_number(content)
                if num is not None and 0 <= num <= 100:
                    value = num
                    break

    # Final fallback
    if value is None:
        return FearGreedData(
            value=50,
            zone=FearGreedZone.NEUTRAL,
            description="Could not parse CNN Fear & Greed value. Using neutral default (50).",
        )

    zone = _classify_zone(value)

    # Build description from the page content
    zone_descriptions = {
        FearGreedZone.EXTREME_FEAR: "Investors are panicking. Historically, this can signal a buying opportunity.",
        FearGreedZone.FEAR: "Investors are cautious and risk-averse. Markets may be undervalued.",
        FearGreedZone.NEUTRAL: "Market sentiment is balanced. No strong directional bias.",
        FearGreedZone.GREED: "Investors are optimistic and taking on more risk. Momentum is positive.",
        FearGreedZone.EXTREME_GREED: "Investors are euphoric. Historically, this can signal a market top.",
    }
    description = zone_descriptions.get(zone, "")

    # Try to extract historical values from the page
    prev_close: Optional[int] = None
    week_ago: Optional[int] = None
    month_ago: Optional[int] = None
    year_ago: Optional[int] = None

    # Look for comparison table
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            num = _extract_number(cells[1].get_text(strip=True))
            if num is not None:
                if "previous" in label or "prev" in label:
                    prev_close = num
                elif "week" in label:
                    week_ago = num
                elif "month" in label:
                    month_ago = num
                elif "year" in label:
                    year_ago = num

    return FearGreedData(
        value=value,
        zone=zone,
        description=description,
        previous_close=prev_close,
        one_week_ago=week_ago,
        one_month_ago=month_ago,
        one_year_ago=year_ago,
        timestamp=datetime.now(),
    )
