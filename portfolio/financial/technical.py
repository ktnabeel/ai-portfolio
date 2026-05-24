"""Technical Analysis Agent - RSI, MACD, SMA, Bollinger Bands."""

from typing import Optional

import numpy as np

from .models import AgentSignal, SignalType


class TechnicalAnalysisAgent:
    """Computes RSI, MACD, moving averages, and Bollinger Bands."""

    NAME = "Technical Analysis"

    def analyze(self, ticker: str, info: dict, history) -> AgentSignal:
        if history is None or history.empty or len(history) < 26:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary=f"Insufficient price data for {ticker}.",
            )

        close = history["Close"].values
        current_price = float(close[-1])

        rsi = self._compute_rsi(close, period=14)
        macd_line, signal_line, macd_histogram = self._compute_macd(close)
        sma_50 = float(np.mean(close[-min(50, len(close)):]))
        sma_200 = float(np.mean(close[-min(200, len(close)):])) if len(close) >= 200 else sma_50
        bb_upper, bb_middle, bb_lower, bb_position = self._compute_bollinger(close, period=20)

        scores = []
        if rsi is not None:
            if rsi < 30:
                scores.append(1.0)
            elif rsi > 70:
                scores.append(-1.0)
            else:
                scores.append(0.0)
        if macd_histogram is not None:
            if macd_histogram > 0:
                scores.append(0.7)
            elif macd_histogram < 0:
                scores.append(-0.7)
        if sma_50 and sma_200:
            if current_price > sma_50 > sma_200:
                scores.append(1.0)
            elif current_price < sma_50 < sma_200:
                scores.append(-1.0)
            elif current_price > sma_50:
                scores.append(0.5)
            elif current_price < sma_50:
                scores.append(-0.5)
        if bb_position is not None:
            if bb_position < 0.2:
                scores.append(1.0)
            elif bb_position > 0.8:
                scores.append(-1.0)

        if not scores:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.3,
                summary="Insufficient indicator data.",
                metrics={"rsi": rsi, "sma_50": sma_50, "sma_200": sma_200},
            )

        composite = float(np.mean(scores))
        confidence = min(0.85, abs(composite) + 0.15)

        if composite > 0.25:
            signal = SignalType.BULLISH
        elif composite < -0.25:
            signal = SignalType.BEARISH
        else:
            signal = SignalType.NEUTRAL

        details = []
        if rsi is not None:
            details.append(f"RSI={rsi:.0f}")
        if macd_line is not None:
            up = "\u25b2" if macd_histogram and macd_histogram > 0 else "\u25bc"
            details.append(f"MACD={up}")

        return AgentSignal(
            agent_name=self.NAME,
            signal=signal,
            confidence=confidence,
            summary=f"Technical composite: {composite:+.2f} | " + ", ".join(details),
            metrics={
                "rsi": round(rsi, 1) if rsi is not None else None,
                "macd": round(float(macd_line), 2) if macd_line is not None else None,
                "macd_signal": round(float(signal_line), 2) if signal_line is not None else None,
                "macd_histogram": round(float(macd_histogram), 4) if macd_histogram is not None else None,
                "sma_50": round(sma_50, 2),
                "sma_200": round(sma_200, 2),
                "bb_upper": round(bb_upper, 2) if bb_upper is not None else None,
                "bb_middle": round(bb_middle, 2) if bb_middle is not None else None,
                "bb_lower": round(bb_lower, 2) if bb_lower is not None else None,
                "bb_position": round(bb_position, 2) if bb_position is not None else None,
                "composite_score": round(composite, 3),
            },
        )

    @staticmethod
    def _compute_rsi(prices, period=14):
        if len(prices) < period + 1:
            return None
        deltas = np.diff(prices[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _compute_macd(prices, fast=12, slow=26, signal=9):
        if len(prices) < slow + signal:
            return None, None, None
        ema_fast = TechnicalAnalysisAgent._ema(prices, fast)
        ema_slow = TechnicalAnalysisAgent._ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalAnalysisAgent._ema(macd_line, signal)
        histogram = macd_line[-1] - signal_line[-1]
        return macd_line[-1], signal_line[-1], histogram

    @staticmethod
    def _ema(data, period):
        alpha = 2.0 / (period + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    @staticmethod
    def _compute_bollinger(prices, period=20, num_std=2.0):
        if len(prices) < period:
            return None, None, None, None
        window = prices[-period:]
        middle = float(np.mean(window))
        std = float(np.std(window))
        upper = middle + num_std * std
        lower = middle - num_std * std
        position = (prices[-1] - lower) / (upper - lower) if upper != lower else 0.5
        return upper, middle, lower, position
