"""Risk & Sentiment Agent — CNN Fear & Greed + World News Analysis.

Responsibility:
  1. Fetch CNN Fear & Greed Index
  2. Scrape world news headlines for market context
  3. Analyze overall market sentiment and risk levels
  4. Provide risk assessment for options trading context

Uses:
  - CNN Fear & Greed scraper
  - World news scraper
  - OpenAI GPT-4o to synthesize sentiment and risk analysis
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from .._llm import create_llm
from ..models import FearGreedData, RiskSentimentOutput, WorldNewsItem
from ..scrapers.cnn_fear_greed import fetch_fear_greed
from ..scrapers.news_scraper import fetch_world_news


SYSTEM_PROMPT = """You are the Risk & Sentiment Agent in a multi-agent trading system.

Your responsibilities:
1. Interpret the CNN Fear & Greed Index value (0-100 scale)
2. Analyze world news headlines for market-moving events
3. Assess the overall market risk environment
4. Provide a clear market trend assessment

The Fear & Greed Index:
- 0-25: Extreme Fear — investors panicking, potential buying opportunity
- 25-40: Fear — cautious, risk-averse environment
- 40-60: Neutral — balanced sentiment
- 60-75: Greed — optimistic, momentum-driven
- 75-100: Extreme Greed — euphoric, potential market top

For the given fear/greed data and news headlines, provide:
1. Market Trend: a 2-3 sentence summary of the current market trend
2. Risk Assessment: LOW, MODERATE, or HIGH risk for options trading
3. Key Factors: what's driving the current sentiment (list 3-5 factors)

Be concise and data-driven. This will feed into the Regime and Decision agents."""


class RiskSentimentAgent:
    """Agent #2: Fear & Greed + World News Analysis."""

    NAME = "Risk & Sentiment"

    def __init__(self, llm: BaseChatModel | None = None):
        self.llm = llm  # None → deterministic / rule-based fallback

    def analyze(self) -> RiskSentimentOutput:
        """Fetch and analyze market sentiment data.

        Returns:
            RiskSentimentOutput with fear/greed data, news, and analysis.
        """
        # Fetch data
        fear_greed = fetch_fear_greed()
        news_items = fetch_world_news(max_items=8)

        # Deterministic fallback (no LLM → structured rules)
        deterministic_analysis = (
            f"MARKET TREND: Based on Fear & Greed at {fear_greed.value}/100 "
            f"({fear_greed.zone.value}), the market is showing "
            f"{'positive' if fear_greed.value > 50 else 'negative'} sentiment. "
            f"{fear_greed.description}\n"
            f"RISK LEVEL: {'HIGH' if fear_greed.value < 30 or fear_greed.value > 70 else 'MODERATE'}\n"
            f"KEY FACTORS:\n"
            f"  - Fear & Greed Index at {fear_greed.value}/100 ({fear_greed.zone.value}) "
            f"via {fear_greed.source_method or 'CNN page fetch'}\n"
            f"  - {len(news_items)} news headlines analyzed\n"
            + "".join(f"  - {n.headline[:100]}...\n" for n in news_items[:3])
        )

        if self.llm is None:
            analysis = deterministic_analysis
        else:
            # Build context for LLM
            fg_context = f"""
CNN Fear & Greed Index: {fear_greed.value}/100
Zone: {fear_greed.zone.value}
Source: {fear_greed.source_url or 'https://www.cnn.com/markets/fear-and-greed'}
Fetch Method: {fear_greed.source_method or 'browser/http fallback'}
Last Updated: {fear_greed.timestamp.isoformat()}
Description: {fear_greed.description}
"""

            if fear_greed.previous_close:
                fg_context += f"Previous Close: {fear_greed.previous_close}\n"
            if fear_greed.one_week_ago:
                fg_context += f"1 Week Ago: {fear_greed.one_week_ago}\n"
            if fear_greed.one_month_ago:
                fg_context += f"1 Month Ago: {fear_greed.one_month_ago}\n"

            news_context = "World News Headlines:\n"
            for i, news in enumerate(news_items, 1):
                news_context += f"  {i}. [{news.impact}] {news.headline} (source: {news.source})\n"

            prompt = f"""
Analyze the current market environment based on this data:

{fg_context}

{news_context}

Provide:
1. MARKET TREND: A clear 2-3 sentence summary of the current market trend.
2. RISK LEVEL: LOW, MODERATE, or HIGH for options trading.
3. KEY FACTORS: 3-5 bullet points on what's driving the current sentiment.
"""
            try:
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
                response = self.llm.invoke(messages)
                analysis = str(response.content) if hasattr(response, 'content') else str(response)
            except Exception:
                analysis = deterministic_analysis

        # Parse the analysis into sections
        market_trend = ""
        risk_assessment = ""

        for line in analysis.split("\n"):
            line_stripped = line.strip()
            if line_stripped.upper().startswith("MARKET TREND"):
                market_trend = line_stripped.split(":", 1)[-1].strip() if ":" in line_stripped else line_stripped
            elif line_stripped.upper().startswith("RISK LEVEL"):
                risk_assessment = line_stripped.split(":", 1)[-1].strip() if ":" in line_stripped else line_stripped

        if not market_trend:
            market_trend = f"Fear & Greed at {fear_greed.value}/100 ({fear_greed.zone.value}). {fear_greed.description}"
        if not risk_assessment:
            risk_assessment = "MODERATE"

        return RiskSentimentOutput(
            fear_greed=fear_greed,
            top_news=news_items,
            market_trend=market_trend,
            risk_assessment=risk_assessment,
            reasoning=analysis,
        )
