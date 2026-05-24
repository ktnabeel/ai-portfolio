"""Sentiment Analysis Agent - news sentiment scoring."""

import yfinance as yf

from .models import AgentSignal, SignalType


POSITIVE_WORDS = {
    "beat", "growth", "profit", "record", "surge", "gain", "upgrade",
    "bullish", "outperform", "strong", "positive", "rise", "rally",
    "expansion", "innovation", "launch", "approval", "partnership",
    "dividend", "buyback", "raised", "target", "exceed", "momentum",
}

NEGATIVE_WORDS = {
    "miss", "decline", "loss", "drop", "downgrade", "bearish",
    "underperform", "weak", "negative", "fall", "selloff", "crash",
    "layoff", "lawsuit", "investigation", "fine", "penalty", "debt",
    "bankruptcy", "risk", "warning", "cut", "reduce", "slowdown",
    "volatility", "uncertainty", "headwind", "concern",
}


class SentimentAnalysisAgent:
    """Analyzes recent news headlines for sentiment scoring."""

    NAME = "Sentiment Analysis"
    MAX_ARTICLES = 10

    def analyze(self, ticker: str, info: dict, history) -> AgentSignal:
        try:
            stock = yf.Ticker(ticker)
            news = stock.news or []
        except Exception as e:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary=f"Failed to fetch news for {ticker}: {e}",
                metrics={"articles_analyzed": 0},
            )

        if not news:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary=f"No recent news found for {ticker}.",
                metrics={"articles_analyzed": 0},
            )

        articles = news[:self.MAX_ARTICLES]
        scores = []
        for article in articles:
            title = (article.get("title") or "").lower()
            summary_text = (article.get("summary") or "").lower()
            text = f"{title} {summary_text}"

            pos_count = sum(1 for word in POSITIVE_WORDS if word in text)
            neg_count = sum(1 for word in NEGATIVE_WORDS if word in text)

            if pos_count + neg_count > 0:
                article_score = (pos_count - neg_count) / (pos_count + neg_count)
            else:
                article_score = 0.0
            scores.append(article_score)

        avg_score = float(sum(scores) / len(scores))
        confidence = min(0.75, abs(avg_score) + 0.2)
        positive_count = sum(1 for s in scores if s > 0.1)
        negative_count = sum(1 for s in scores if s < -0.1)
        neutral_count = len(scores) - positive_count - negative_count

        if avg_score > 0.15:
            signal = SignalType.BULLISH
        elif avg_score < -0.15:
            signal = SignalType.BEARISH
        else:
            signal = SignalType.NEUTRAL

        return AgentSignal(
            agent_name=self.NAME,
            signal=signal,
            confidence=confidence,
            summary=(
                f"Analyzed {len(scores)} articles: "
                f"{positive_count}\u25b2 {negative_count}\u25bc {neutral_count}\u2500 | "
                f"Score: {avg_score:+.2f}"
            ),
            metrics={
                "articles_analyzed": len(scores),
                "sentiment_score": round(avg_score, 3),
                "positive_articles": positive_count,
                "negative_articles": negative_count,
                "neutral_articles": neutral_count,
            },
        )
