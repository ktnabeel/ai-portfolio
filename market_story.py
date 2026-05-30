"""Shared market-sentiment and technical-analysis helpers for deployment UIs.

The functions in this module intentionally avoid repo-local trading packages so
they can be imported by the self-contained Vercel entrypoint and the Gradio
deployment entrypoint without dragging the full app tree into the bundle.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape, unescape
from statistics import mean
from typing import Any
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


FEAR_GREED_URL = "https://www.cnn.com/markets/fear-and-greed"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d&includePrePost=false&events=div%2Csplits"


@dataclass(slots=True)
class SentimentDriver:
    title: str
    summary: str
    detail: str
    accent: str = "blue"


@dataclass(slots=True)
class SentimentSnapshot:
    value: int
    zone: str
    description: str
    previous_close: int | None
    one_week_ago: int | None
    one_month_ago: int | None
    one_year_ago: int | None
    drivers: list[SentimentDriver] = field(default_factory=list)
    warning: str = ""
    source_url: str = FEAR_GREED_URL
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TechnicalSnapshot:
    symbol: str
    current_price: float | None
    ema_8: float | None
    ema_21: float | None
    high_20: float | None
    low_20: float | None
    average_volume_20: float | None
    volume: float | None
    bullish_stack: bool
    bearish_stack: bool
    breakout_up: bool
    breakdown: bool
    volume_surge: bool
    signal: str
    summary: str
    warning: str = ""
    data_points: int = 0
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SecurityDecision:
    symbol: str
    side: str
    confidence: float
    thesis: str
    rationale: str
    reasons: list[str] = field(default_factory=list)
    sentiment: SentimentSnapshot | None = None
    technical: TechnicalSnapshot | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.sentiment is not None:
            payload["sentiment"] = self.sentiment.to_dict()
        if self.technical is not None:
            payload["technical"] = self.technical.to_dict()
        return payload


def sentiment_snapshot_from_dict(data: dict[str, Any]) -> SentimentSnapshot:
    drivers = [
        driver if isinstance(driver, SentimentDriver) else SentimentDriver(**driver)
        for driver in data.get("drivers", [])
    ]
    return SentimentSnapshot(
        value=int(data.get("value", 50)),
        zone=str(data.get("zone", "Neutral")),
        description=str(data.get("description", "")),
        previous_close=data.get("previous_close"),
        one_week_ago=data.get("one_week_ago"),
        one_month_ago=data.get("one_month_ago"),
        one_year_ago=data.get("one_year_ago"),
        drivers=drivers,
        warning=str(data.get("warning", "")),
        source_url=str(data.get("source_url", FEAR_GREED_URL)),
        fetched_at=str(data.get("fetched_at", datetime.now(timezone.utc).isoformat())),
    )


def technical_snapshot_from_dict(data: dict[str, Any]) -> TechnicalSnapshot:
    return TechnicalSnapshot(
        symbol=str(data.get("symbol", "AAPL")),
        current_price=data.get("current_price"),
        ema_8=data.get("ema_8"),
        ema_21=data.get("ema_21"),
        high_20=data.get("high_20"),
        low_20=data.get("low_20"),
        average_volume_20=data.get("average_volume_20"),
        volume=data.get("volume"),
        bullish_stack=bool(data.get("bullish_stack", False)),
        bearish_stack=bool(data.get("bearish_stack", False)),
        breakout_up=bool(data.get("breakout_up", False)),
        breakdown=bool(data.get("breakdown", False)),
        volume_surge=bool(data.get("volume_surge", False)),
        signal=str(data.get("signal", "Insufficient data")),
        summary=str(data.get("summary", "")),
        warning=str(data.get("warning", "")),
        data_points=int(data.get("data_points", 0)),
        fetched_at=str(data.get("fetched_at", datetime.now(timezone.utc).isoformat())),
    )


_SENTIMENT_DRIVERS = (
    SentimentDriver(
        title="Market momentum",
        summary="S&P 500 vs its 125-day average",
        detail="Higher prices above the rolling average point to positive momentum; weak momentum points to fear.",
        accent="blue",
    ),
    SentimentDriver(
        title="Stock strength",
        summary="New 52-week highs versus lows",
        detail="A broad base of new highs is a bullish signal; crowded lows lean fearful.",
        accent="teal",
    ),
    SentimentDriver(
        title="Breadth",
        summary="McClellan volume summation",
        detail="Breadth improves when rising volume dominates falling volume across the NYSE.",
        accent="amber",
    ),
    SentimentDriver(
        title="Put/call ratio",
        summary="5-day average puts vs calls",
        detail="Rising put demand is bearish; heavily skewed call buying suggests greed.",
        accent="violet",
    ),
    SentimentDriver(
        title="Volatility",
        summary="VIX vs its 50-day average",
        detail="High or rising VIX often reflects fear; subdued volatility tends to support greed.",
        accent="green",
    ),
    SentimentDriver(
        title="Safe haven demand",
        summary="Stocks vs bonds over 20 days",
        detail="When bonds beat stocks, investors are seeking shelter from risk.",
        accent="slate",
    ),
    SentimentDriver(
        title="Junk bond demand",
        summary="Yield spread versus investment grade",
        detail="Tighter spreads signal risk appetite; wider spreads indicate caution.",
        accent="blue",
    ),
)


def _classify_zone(value: int) -> str:
    if value <= 25:
        return "Extreme Fear"
    if value <= 40:
        return "Fear"
    if value <= 60:
        return "Neutral"
    if value <= 75:
        return "Greed"
    return "Extreme Greed"


def _html_to_text(html: str) -> str:
    stripped = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    stripped = re.sub(r"(?s)<[^>]+>", " ", stripped)
    return re.sub(r"\s+", " ", unescape(stripped)).strip()


def _extract_first_int(text: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{1,3})(?!\d)", text)
    if not match:
        return None
    value = int(match.group(1))
    return value if 0 <= value <= 100 else None


def _extract_number_after(label: str, text: str) -> int | None:
    pattern = re.compile(rf"{re.escape(label)}[^0-9]{{0,40}}(\d{{1,3}})", re.I)
    match = pattern.search(text)
    if match:
        value = int(match.group(1))
        return value if 0 <= value <= 100 else None
    return None


def _extract_sentiment_value(text: str) -> int | None:
    patterns = (
        r"Fear\s*&\s*Greed\s*Index[^0-9]{0,60}(\d{1,3})",
        r"Current(?:\s+reading)?[^0-9]{0,60}(\d{1,3})",
        r"(\d{1,3})[^A-Za-z0-9]{0,20}(Extreme\s*Fear|Fear|Neutral|Greed|Extreme\s*Greed)",
        r"(Extreme\s*Fear|Fear|Neutral|Greed|Extreme\s*Greed)[^0-9]{0,20}(\d{1,3})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        for group in match.groups():
            if not group:
                continue
            value = _extract_first_int(group)
            if value is not None:
                return value
    return None


def _fetch_url(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=12) as response:  # noqa: S310 - controlled market-data fetch
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return body.decode(charset, errors="replace")


def fetch_sentiment_snapshot() -> SentimentSnapshot:
    try:
        html = _fetch_url(FEAR_GREED_URL)
        text = _html_to_text(html)
        value = _extract_sentiment_value(text)
        if value is None:
            raise ValueError("Could not parse CNN Fear & Greed value")

        zone = _classify_zone(value)
        description = {
            "Extreme Fear": "Investors are panicking and risk appetite is very low.",
            "Fear": "Investors are cautious and trading defensively.",
            "Neutral": "Market sentiment is balanced with no strong bias.",
            "Greed": "Investors are leaning into risk and momentum.",
            "Extreme Greed": "Investor enthusiasm is stretched and sentiment is hot.",
        }[zone]

        return SentimentSnapshot(
            value=value,
            zone=zone,
            description=description,
            previous_close=_extract_number_after("Previous close", text),
            one_week_ago=_extract_number_after("1 week ago", text),
            one_month_ago=_extract_number_after("1 month ago", text),
            one_year_ago=_extract_number_after("1 year ago", text),
            drivers=list(_SENTIMENT_DRIVERS),
        )
    except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as exc:
        return SentimentSnapshot(
            value=50,
            zone="Neutral",
            description=f"Unable to fetch CNN Fear & Greed Index. Using neutral fallback. ({exc})",
            previous_close=None,
            one_week_ago=None,
            one_month_ago=None,
            one_year_ago=None,
            drivers=list(_SENTIMENT_DRIVERS),
            warning="Live CNN scrape unavailable; neutral fallback is shown.",
        )


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def fetch_technical_snapshot(symbol: str) -> TechnicalSnapshot:
    clean = "".join(ch for ch in symbol.upper().strip() if ch.isalnum() or ch in {".", "-"})
    clean = clean[:12] or "AAPL"
    url = YAHOO_CHART_URL.format(symbol=quote(clean))
    try:
        payload = json.loads(_fetch_url(url))
        chart = (payload.get("chart") or {}).get("result") or []
        if not chart:
            raise ValueError("Yahoo chart response missing result data")

        result = chart[0]
        quotes = (result.get("indicators") or {}).get("quote") or [{}]
        quote_data = quotes[0]
        closes = [float(v) for v in quote_data.get("close", []) if v is not None]
        volumes = [float(v) for v in quote_data.get("volume", []) if v is not None]
        if len(closes) < 21:
            raise ValueError(f"Insufficient price history for {clean}")

        ema_8 = _ema(closes, 8)[-1]
        ema_21 = _ema(closes, 21)[-1]
        current = closes[-1]
        high_20 = max(closes[-20:])
        low_20 = min(closes[-20:])
        avg_volume_20 = mean(volumes[-20:]) if len(volumes) >= 20 else None
        latest_volume = volumes[-1] if volumes else None

        bullish_stack = current > ema_8 > ema_21
        bearish_stack = current < ema_8 < ema_21
        breakout_up = current >= high_20
        breakdown = current <= low_20
        volume_surge = bool(
            avg_volume_20
            and latest_volume
            and latest_volume > avg_volume_20 * 1.2
        )

        if bullish_stack and breakout_up:
            signal = "Bullish breakout"
            summary = "Price is above EMA 8 and EMA 21 and also cleared the recent range high."
        elif bullish_stack:
            signal = "Bullish trend"
            summary = "Price is stacked above EMA 8 and EMA 21, which keeps the trend constructive."
        elif bearish_stack and breakdown:
            signal = "Bearish breakdown"
            summary = "Price is below EMA 8 and EMA 21 and also broke below recent support."
        elif bearish_stack:
            signal = "Bearish trend"
            summary = "Price is stacked below EMA 8 and EMA 21, which keeps the trend weak."
        elif breakout_up:
            signal = "Bullish breakout"
            summary = "Price broke above the 20-day high even though the EMA stack is mixed."
        elif breakdown:
            signal = "Bearish breakdown"
            summary = "Price lost the 20-day range low even though the EMA stack is mixed."
        else:
            signal = "Mixed / sideways"
            summary = "EMA 8 and EMA 21 are not aligned enough to call a clean trend."

        if volume_surge:
            summary += " Volume is elevated, which adds conviction."

        return TechnicalSnapshot(
            symbol=clean,
            current_price=current,
            ema_8=ema_8,
            ema_21=ema_21,
            high_20=high_20,
            low_20=low_20,
            average_volume_20=avg_volume_20,
            volume=latest_volume,
            bullish_stack=bullish_stack,
            bearish_stack=bearish_stack,
            breakout_up=breakout_up,
            breakdown=breakdown,
            volume_surge=volume_surge,
            signal=signal,
            summary=summary,
            data_points=len(closes),
        )
    except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as exc:
        return TechnicalSnapshot(
            symbol=clean,
            current_price=None,
            ema_8=None,
            ema_21=None,
            high_20=None,
            low_20=None,
            average_volume_20=None,
            volume=None,
            bullish_stack=False,
            bearish_stack=False,
            breakout_up=False,
            breakdown=False,
            volume_surge=False,
            signal="Insufficient data",
            summary=f"Unable to fetch live price history for {clean}. ({exc})",
            warning="Live price data unavailable; showing fallback text.",
            data_points=0,
        )


def build_security_decision(
    symbol: str,
    sentiment: SentimentSnapshot | None = None,
    technical: TechnicalSnapshot | None = None,
) -> SecurityDecision:
    sentiment = sentiment or fetch_sentiment_snapshot()
    technical = technical or fetch_technical_snapshot(symbol)

    reasons: list[str] = []
    score = 0.0

    if technical.current_price is None:
        reasons.append("Live price history is unavailable, so the chart signal is limited.")
    else:
        if technical.bullish_stack:
            score += 2.0
            reasons.append(f"Price is above EMA 8 and EMA 21 at ${technical.current_price:.2f}.")
        elif technical.bearish_stack:
            score -= 2.0
            reasons.append(f"Price is below EMA 8 and EMA 21 at ${technical.current_price:.2f}.")

        if technical.breakout_up:
            score += 1.5
            reasons.append("Price broke above the 20-day high, which confirms upside momentum.")
        elif technical.breakdown:
            score -= 1.5
            reasons.append("Price lost the 20-day low, which confirms downside pressure.")

        if technical.volume_surge and technical.breakout_up:
            score += 0.5
            reasons.append("Breakout is backed by heavier-than-average volume.")

    if sentiment.zone in {"Extreme Fear", "Fear"}:
        score += 0.5 if score >= 0 else 0.0
        reasons.append(
            f"CNN Fear & Greed is {sentiment.value}/100 ({sentiment.zone}), which can support a contrarian long if price confirms."
        )
    elif sentiment.zone in {"Greed", "Extreme Greed"}:
        score -= 0.5 if score <= 0 else 0.0
        reasons.append(
            f"CNN Fear & Greed is {sentiment.value}/100 ({sentiment.zone}), which makes upside a little stretched."
        )
    else:
        reasons.append(
            f"CNN Fear & Greed is {sentiment.value}/100 ({sentiment.zone}), so sentiment is neutral and mostly used as confirmation."
        )

    if score >= 0:
        side = "BUY"
        thesis = "Hybrid signal leans long"
    else:
        side = "SELL"
        thesis = "Hybrid signal leans defensive"

    confidence = min(0.95, 0.55 + abs(score) * 0.12)

    if technical.signal == "Insufficient data":
        rationale = (
            f"{side} bias is based primarily on the CNN sentiment reading because live price history was insufficient. "
            f"{' '.join(reasons)}"
        )
        confidence = min(confidence, 0.65)
    else:
        rationale = " ".join(reasons)

    return SecurityDecision(
        symbol=symbol.upper().strip() or "AAPL",
        side=side,
        confidence=round(confidence, 2),
        thesis=thesis,
        rationale=rationale,
        reasons=reasons,
        sentiment=sentiment,
        technical=technical,
    )


def render_sentiment_panel(sentiment: SentimentSnapshot) -> str:
    comparisons = [
        ("Previous close", sentiment.previous_close),
        ("1 week ago", sentiment.one_week_ago),
        ("1 month ago", sentiment.one_month_ago),
        ("1 year ago", sentiment.one_year_ago),
    ]
    comparison_html = "".join(
        f"""
        <div class="sentiment-mini-kpi">
          <span class="label">{escape(label)}</span>
          <span class="value">{value if value is not None else "—"}</span>
        </div>
        """
        for label, value in comparisons
    )
    driver_html = "".join(
        f"""
        <article class="driver-card {escape(driver.accent)}">
          <div class="driver-title">{escape(driver.title)}</div>
          <div class="driver-summary">{escape(driver.summary)}</div>
          <div class="driver-detail">{escape(driver.detail)}</div>
        </article>
        """
        for driver in sentiment.drivers
    )
    warning_html = (
        f'<div class="hint" style="margin-top:12px;">{escape(sentiment.warning)}</div>'
        if sentiment.warning
        else ""
    )
    return f"""
    <section class="panel market-panel">
      <div class="panel-head">
        <div>
          <h2>CNN Fear &amp; Greed</h2>
          <div class="panel-sub">{escape(sentiment.description)}</div>
        </div>
        <div class="market-score">{sentiment.value}<span>{escape(sentiment.zone)}</span></div>
      </div>
      <div class="sentiment-mini-grid">
        {comparison_html}
      </div>
      <div class="driver-grid">
        {driver_html}
      </div>
      {warning_html}
    </section>
    """


def render_technical_panel(decision: SecurityDecision) -> str:
    technical = decision.technical
    if technical is None:
        return ""

    metric_rows = []
    for label, value in (
        ("Price", technical.current_price),
        ("EMA 8", technical.ema_8),
        ("EMA 21", technical.ema_21),
        ("20d High", technical.high_20),
        ("20d Low", technical.low_20),
        ("20d Volume Avg", technical.average_volume_20),
    ):
        metric_rows.append(
            f"""
            <div class="tech-metric">
              <span class="label">{escape(label)}</span>
              <span class="value">{f"${value:,.2f}" if isinstance(value, (int, float)) and value is not None else "—"}</span>
            </div>
            """
        )

    reason_items = "".join(
        f"<li>{escape(reason)}</li>" for reason in decision.reasons
    )
    signal_flags = []
    if technical.bullish_stack:
        signal_flags.append("Above 8/21 EMA")
    if technical.breakout_up:
        signal_flags.append("Breakout confirmed")
    if technical.volume_surge:
        signal_flags.append("Volume support")
    if technical.bearish_stack:
        signal_flags.append("Below 8/21 EMA")
    if technical.breakdown:
        signal_flags.append("Support lost")
    if not signal_flags:
        signal_flags.append("Mixed / sideways")

    chips = "".join(f'<span class="tech-chip">{escape(flag)}</span>' for flag in signal_flags)

    warning_html = (
        f'<div class="hint" style="margin-top:12px;">{escape(technical.warning)}</div>'
        if technical.warning
        else ""
    )

    return f"""
    <section class="panel market-panel">
      <div class="panel-head">
        <div>
          <h2>Security rationale</h2>
          <div class="panel-sub">{escape(technical.summary)}</div>
        </div>
        <div class="decision-pill">{escape(decision.side)}</div>
      </div>
      <div class="tech-grid">
        {''.join(metric_rows)}
      </div>
      <div class="tech-chip-row">
        {chips}
      </div>
      <div class="decision-banner" style="margin-top:14px;">
        <div class="decision-kicker">Why this side</div>
        <div class="decision-meta">{escape(decision.rationale)}</div>
      </div>
      <div class="decision-banner" style="margin-top:12px; background: linear-gradient(180deg, rgba(37,99,235,.04), rgba(255,255,255,.94));">
        <div class="decision-kicker">Key reasons</div>
        <ul class="reason-list">
          {reason_items}
        </ul>
      </div>
      {warning_html}
    </section>
    """
