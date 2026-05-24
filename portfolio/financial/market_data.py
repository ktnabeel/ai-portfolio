"""Market Data Agent - price trends, volume, market cap."""

from .models import AgentSignal, SignalType


class MarketDataAgent:
    """Fetches price history, volume, fundamentals, and market data."""

    NAME = "Market Data"

    def analyze(self, ticker: str, info: dict, history) -> AgentSignal:
        if history is None or history.empty:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary=f"No market data available for {ticker}.",
            )

        close = history["Close"]
        current_price = float(close.iloc[-1])
        hist_len = len(close)

        price_50d_ago = float(close.iloc[-min(50, hist_len)])
        price_200d_ago = float(close.iloc[-min(200, hist_len)]) if hist_len >= 200 else price_50d_ago
        same_period = hist_len < 200

        short_term_change = (current_price - price_50d_ago) / price_50d_ago
        long_term_change = (current_price - price_200d_ago) / price_200d_ago

        avg_volume = float(history["Volume"].tail(20).mean())
        recent_volume = float(history["Volume"].tail(5).mean())
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0

        if short_term_change > 0.05 and long_term_change > 0.10:
            signal = SignalType.BULLISH
            confidence = min(0.8, 0.5 + abs(short_term_change))
        elif short_term_change < -0.05 and long_term_change < -0.10:
            signal = SignalType.BEARISH
            confidence = min(0.8, 0.5 + abs(short_term_change))
        else:
            signal = SignalType.NEUTRAL
            confidence = 0.4

        trend_note = " (limited history)" if same_period else ""
        up50 = "\u25b2" if short_term_change >= 0 else "\u25bc"
        up200 = "\u25b2" if long_term_change >= 0 else "\u25bc"
        summary = (
            f"{ticker} @ ${current_price:.2f} | "
            f"{up50}{abs(short_term_change):.1%} (50d), "
            f"{up200}{abs(long_term_change):.1%} (200d){trend_note}"
        )

        return AgentSignal(
            agent_name=self.NAME,
            signal=signal,
            confidence=confidence,
            summary=summary,
            metrics={
                "current_price": current_price,
                "short_term_change": short_term_change,
                "long_term_change": long_term_change,
                "avg_volume_20d": int(avg_volume),
                "volume_ratio": volume_ratio,
                "market_cap": info.get("marketCap"),
                "beta": info.get("beta", 1.0),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
            },
        )
