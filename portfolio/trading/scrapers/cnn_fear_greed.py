"""CNN Fear & Greed Index scraper.

Fetches https://www.cnn.com/markets/fear-and-greed and extracts:
  - Current Fear & Greed value (0-100)
  - Zone classification (Extreme Fear through Extreme Greed)
  - Historical comparison values
  - Market trend description

The primary path uses a Playwright browser because CNN's data endpoint
returns bot protection responses to direct HTTP clients. The HTTP/BeautifulSoup
parser remains as a graceful fallback for environments without browser support.
"""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime
from typing import Any, Mapping, Optional

import httpx
from bs4 import BeautifulSoup

from ..models import FearGreedData, FearGreedZone


FEAR_GREED_URL = "https://www.cnn.com/markets/fear-and-greed"
FEAR_GREED_DATA_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
_CACHE_TTL_SECONDS = 600
_CACHE_LOCK = threading.Lock()
_CACHE_VALUE: FearGreedData | None = None
_CACHE_AT: float = 0.0

try:  # Playwright is optional at import time for lighter deployments.
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - exercised when Playwright is absent.
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None  # type: ignore[assignment]


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


def _zone_from_rating(rating: Any, value: int) -> FearGreedZone:
    """Map CNN's rating label to the local enum, falling back to score bands."""
    normalized = str(rating or "").strip().lower().replace("_", " ")
    mapping = {
        "extreme fear": FearGreedZone.EXTREME_FEAR,
        "fear": FearGreedZone.FEAR,
        "neutral": FearGreedZone.NEUTRAL,
        "greed": FearGreedZone.GREED,
        "extreme greed": FearGreedZone.EXTREME_GREED,
    }
    return mapping.get(normalized, _classify_zone(value))


def _zone_description(zone: FearGreedZone) -> str:
    """Human-readable interpretation for each Fear & Greed zone."""
    zone_descriptions = {
        FearGreedZone.EXTREME_FEAR: "Investors are panicking. Historically, this can signal a buying opportunity.",
        FearGreedZone.FEAR: "Investors are cautious and risk-averse. Markets may be undervalued.",
        FearGreedZone.NEUTRAL: "Market sentiment is balanced. No strong directional bias.",
        FearGreedZone.GREED: "Investors are optimistic and taking on more risk. Momentum is positive.",
        FearGreedZone.EXTREME_GREED: "Investors are euphoric. Historically, this can signal a market top.",
    }
    return zone_descriptions.get(zone, "")


def _extract_number(text: str) -> Optional[int]:
    """Extract the first number from a text string."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def _to_int(value: Any) -> Optional[int]:
    """Convert CNN numeric payload values to the model's integer score."""
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: Any) -> datetime:
    """Parse CNN timestamps from ISO strings or millisecond epoch values."""
    if value is None:
        return datetime.now()
    if isinstance(value, (int, float)):
        # CNN graph history timestamps are milliseconds.
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000
        return datetime.fromtimestamp(raw)
    text = str(value).strip()
    if not text:
        return datetime.now()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now()


def _parse_graph_payload(payload: Mapping[str, Any], source_method: str) -> FearGreedData | None:
    """Parse CNN's browser-loaded graphdata payload."""
    current = payload.get("fear_and_greed")
    if not isinstance(current, Mapping):
        return None

    raw_score = current.get("score")
    value = _to_int(raw_score)
    if value is None:
        return None

    zone = _zone_from_rating(current.get("rating"), value)
    timestamp = _parse_timestamp(current.get("timestamp"))
    return FearGreedData(
        value=value,
        zone=zone,
        description=_zone_description(zone),
        previous_close=_to_int(current.get("previous_close")),
        one_week_ago=_to_int(current.get("previous_1_week")),
        one_month_ago=_to_int(current.get("previous_1_month")),
        one_year_ago=_to_int(current.get("previous_1_year")),
        timestamp=timestamp,
        raw_score=float(raw_score) if raw_score is not None else None,
        source_url=FEAR_GREED_URL,
        source_method=source_method,
    )


def _response_json(response: Any) -> Mapping[str, Any] | None:
    """Read a Playwright response body as JSON."""
    try:
        payload = response.json()
    except Exception:
        try:
            payload = json.loads(response.text())
        except Exception:
            return None
    return payload if isinstance(payload, Mapping) else None


def _fetch_with_playwright() -> FearGreedData | None:
    """Fetch CNN's current payload through a headless browser session."""
    if sync_playwright is None:
        return None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 900},
            )

            payloads: list[Mapping[str, Any]] = []

            def capture_graphdata(response: Any) -> None:
                if FEAR_GREED_DATA_URL not in response.url:
                    return
                payload = _response_json(response)
                if payload is not None:
                    payloads.append(payload)

            page.on("response", capture_graphdata)
            page.goto(FEAR_GREED_URL, wait_until="domcontentloaded", timeout=30_000)

            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightTimeoutError:
                pass

            if not payloads:
                page.wait_for_timeout(2_000)

            for payload in payloads:
                parsed = _parse_graph_payload(payload, "playwright-browser")
                if parsed is not None:
                    return parsed
            return None
        finally:
            browser.close()


def _fetch_with_httpx() -> FearGreedData:
    """Fetch and parse the public page with HTTP as a graceful fallback.

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
            source_url=FEAR_GREED_URL,
            source_method="fallback-neutral",
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
            source_url=FEAR_GREED_URL,
            source_method="fallback-neutral",
        )

    zone = _classify_zone(value)
    description = _zone_description(zone)

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
        raw_score=float(value),
        source_url=FEAR_GREED_URL,
        source_method="httpx-html-fallback",
    )


def _get_cached_result() -> FearGreedData | None:
    """Return the most recent scraped value if it is still fresh."""
    with _CACHE_LOCK:
        if _CACHE_VALUE is None or _CACHE_AT <= 0:
            return None
        if (time.monotonic() - _CACHE_AT) > _CACHE_TTL_SECONDS:
            return None
        return _CACHE_VALUE.model_copy(deep=True)


def _store_cached_result(result: FearGreedData) -> FearGreedData:
    """Store the latest scraped value in memory and return a safe copy."""
    with _CACHE_LOCK:
        global _CACHE_VALUE, _CACHE_AT
        _CACHE_VALUE = result.model_copy(deep=True)
        _CACHE_AT = time.monotonic()
        return _CACHE_VALUE.model_copy(deep=True)


def fetch_fear_greed() -> FearGreedData:
    """Fetch the current CNN Fear & Greed Index.

    The current page loads its data from a browser-only endpoint. We use
    Playwright first, then fall back to the legacy HTML parser to keep the
    application usable in constrained deployments.
    """
    cached = _get_cached_result()
    if cached is not None:
        return cached

    try:
        browser_result = _fetch_with_playwright()
        if browser_result is not None:
            return _store_cached_result(browser_result)
    except Exception as e:
        browser_error = str(e)
    else:
        browser_error = "Playwright unavailable or CNN data response missing."

    fallback = _fetch_with_httpx()
    if fallback.source_method == "fallback-neutral":
        fallback.description = (
            f"{fallback.description} Playwright browser fetch was not usable: {browser_error}"
        )
    return _store_cached_result(fallback)
