"""Regime Detection Agent — Bull/Bear/Neutral market classification.

Responsibility:
  1. Analyze S&P 500 trend data (moving averages, RSI, volatility)
  2. Combine with Fear & Greed and sentiment data
  3. Classify the current market regime: Bull, Bear, or Neutral
  4. Provide confidence score and supporting indicators

Uses:
  - yfinance for SPY (S&P 500 ETF) market data
  - Technical indicators (SMA, RSI, volatility)
  - OpenAI GPT-4o for regime classification reasoning
  - Takes RiskSentimentOutput as additional context
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import yfinance as yf
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from .._llm import create_llm
from ..mcp.trading_server import MCPTradingServer
from ..models import MarketRegime, RegimeOutput, RiskSentimentOutput


SYSTEM_PROMPT = """You are the Regime Detection Agent in a multi-agent trading system.

Your responsibilities:
1. Analyze S&P 500 market data and technical indicators
2. Combine with Fear & Greed Index and news sentiment
3. Classify the current market regime as Bull, Bear, or Neutral
4. Provide a confidence score and supporting evidence

Market Regime Definitions:
- BULL MARKET: Strong upward trend, S&P 500 above 50-day and 200-day SMAs,
  RSI between 50-70, positive momentum, low volatility
- BEAR MARKET: Downward trend, S&P 500 below moving averages,
  RSI below 45, high volatility, negative sentiment
- NEUTRAL / RANGE-BOUND: Sideways movement, mixed signals,
  RSI 45-55, moderate volatility, indecisive market

Provide:
1. REGIME: Bull / Bear / Neutral
2. CONFIDENCE: 0.0-1.0
3. Rationale: 2-3 sentences explaining the classification

Be precise and data-driven."""


class RegimeAgent:
    """Agent #3: Market Regime Detection."""

    NAME = "Regime Detection"

    def __init__(self, llm: BaseChatModel | None = None):
        self.llm = llm  # None → deterministic / rule-based fallback

    def _fetch_market_closes(self) -> tuple[np.ndarray | None, dict[str, Any]]:
        """Read market history through MCP first, then direct yfinance fallback."""
        mcp_warning = ""
        try:
            response = MCPTradingServer().call_tool(
                "get_market_regime_data",
                {"symbol": "SPY", "period": "6mo", "interval": "1d"},
            )
            if response.success and isinstance(response.data, dict):
                history = response.data.get("history", [])
                closes = np.array(
                    [float(row["close"]) for row in history if float(row.get("close", 0)) > 0],
                    dtype=float,
                )
                if len(closes) >= 50:
                    metadata = {
                        "source": response.data.get("source", "yfinance"),
                        "freshness": response.data.get("freshness", ""),
                        "is_realtime": bool(response.data.get("is_realtime", False)),
                    }
                    warning = response.data.get("warning")
                    if warning:
                        metadata["warning"] = warning
                    return closes, metadata
                mcp_warning = "MCP market data was incomplete."
            else:
                mcp_warning = response.error or "MCP market data unavailable."
        except Exception as exc:
            mcp_warning = str(exc)

        try:
            spy = yf.Ticker("SPY")
            hist = spy.history(period="6mo")
            if hist is not None and not hist.empty and len(hist) >= 50:
                close = np.asarray(hist["Close"].values, dtype=float)
                latest = hist.index[-1]
                freshness = latest.isoformat() if hasattr(latest, "isoformat") else str(latest)
                warning = "Yahoo Finance OHLC data may be delayed."
                if mcp_warning:
                    warning = f"MCP market-data unavailable; used direct yfinance fallback. {mcp_warning}"
                return close, {
                    "source": "yfinance",
                    "freshness": freshness,
                    "is_realtime": False,
                    "warning": warning,
                }
        except Exception as exc:
            if mcp_warning:
                mcp_warning = f"{mcp_warning}; direct yfinance fallback failed: {exc}"
            else:
                mcp_warning = f"Direct yfinance fallback failed: {exc}"

        return None, {
            "source": "yfinance",
            "freshness": datetime.now(timezone.utc).isoformat(),
            "is_realtime": False,
            "warning": mcp_warning or "Insufficient market data.",
        }

    def analyze(
        self,
        sentiment: Optional[RiskSentimentOutput] = None,
    ) -> RegimeOutput:
        """Detect the current market regime.

        Args:
            sentiment: Optional RiskSentimentOutput for additional context.

        Returns:
            RegimeOutput with regime classification and confidence.
        """
        close, provider_metadata = self._fetch_market_closes()

        if close is None or len(close) < 50:
            # Fallback with limited data
            return RegimeOutput(
                regime=MarketRegime.NEUTRAL,
                confidence=0.3,
                indicators=provider_metadata,
                reasoning="Insufficient market data to determine regime. Defaulting to Neutral.",
            )

        current_price = float(close[-1])

        # Compute indicators
        sma_50 = float(np.mean(close[-50:])) if len(close) >= 50 else current_price
        sma_200 = float(np.mean(close[-200:])) if len(close) >= 200 else sma_50
        price_vs_sma50 = (current_price - sma_50) / sma_50
        price_vs_sma200 = (current_price - sma_200) / sma_200

        # RSI
        rsi = self._compute_rsi(close)

        # Volatility (20-day)
        returns = np.diff(close[-21:]) / close[-21:-1] if len(close) >= 21 else np.array([0.0])
        volatility = float(np.std(returns) * np.sqrt(252))

        # Trend direction (slope of 50-day SMA)
        if len(close) >= 100:
            sma_50_history = np.convolve(close, np.ones(50)/50, mode='valid')
            if len(sma_50_history) >= 20:
                sma_slope = (sma_50_history[-1] - sma_50_history[-20]) / sma_50_history[-20]
            else:
                sma_slope = 0.0
        else:
            sma_slope = 0.0

        # Rule-based deterministic classification (no LLM needed)
        if price_vs_sma50 > 0.02 and sma_slope > 0.01 and rsi > 55:
            det_regime = MarketRegime.BULL
            det_confidence = 0.7
            det_analysis = f"Bull market: SPY above 50-SMA by {price_vs_sma50:.1%}, RSI at {rsi:.0f}, positive trend."
        elif price_vs_sma50 < -0.02 and sma_slope < -0.01 and rsi < 45:
            det_regime = MarketRegime.BEAR
            det_confidence = 0.7
            det_analysis = f"Bear market: SPY below 50-SMA by {price_vs_sma50:.1%}, RSI at {rsi:.0f}, negative trend."
        else:
            det_regime = MarketRegime.NEUTRAL
            det_confidence = 0.5
            det_analysis = f"Neutral market: Mixed signals, SPY near moving averages, RSI at {rsi:.0f}."

        if self.llm is None:
            return RegimeOutput(
                regime=det_regime,
                confidence=det_confidence,
                volatility_index=volatility,
                trend_strength=abs(sma_slope),
                sp500_trend="UP" if sma_slope > 0 else "DOWN",
                indicators={
                    "rsi": round(rsi, 1),
                    "sma_50": round(sma_50, 2),
                    "sma_200": round(sma_200, 2),
                    "volatility": round(volatility, 4),
                    **provider_metadata,
                },
                reasoning=det_analysis,
            )

        # Build market data context for LLM
        market_context = f"""
S&P 500 (SPY) - Current: ${current_price:.2f}
  50-day SMA: ${sma_50:.2f} ({price_vs_sma50:+.1%})
  200-day SMA: ${sma_200:.2f} ({price_vs_sma200:+.1%})
  RSI (14): {rsi:.1f}
  20-day Volatility (annualized): {volatility:.1%}
  50-day SMA Trend (20-day): {sma_slope:+.1%}
"""

        if sentiment:
            market_context += f"""
Fear & Greed Index: {sentiment.fear_greed.value}/100 ({sentiment.fear_greed.zone.value})
Market Trend: {sentiment.market_trend}
Risk Assessment: {sentiment.risk_assessment}
"""

        # LLM classification
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=(
                    f"Classify the current market regime based on this data:\n\n{market_context}\n\n"
                    "Respond with REGIME: [Bull/Bear/Neutral], CONFIDENCE: [0.0-1.0], and a 2-3 sentence rationale."
                )),
            ]
            response = self.llm.invoke(messages)
            analysis = str(response.content) if hasattr(response, 'content') else str(response)
        except Exception:
            return RegimeOutput(
                regime=det_regime,
                confidence=det_confidence,
                volatility_index=volatility,
                trend_strength=abs(sma_slope),
                sp500_trend="UP" if sma_slope > 0 else "DOWN",
                indicators={
                    "rsi": round(rsi, 1),
                    "sma_50": round(sma_50, 2),
                    "sma_200": round(sma_200, 2),
                    "volatility": round(volatility, 4),
                    **provider_metadata,
                },
                reasoning=det_analysis,
            )

        # Parse LLM response
        regime = MarketRegime.NEUTRAL
        confidence = 0.5

        for line in analysis.split("\n"):
            upper = line.strip().upper()
            if "REGIME:" in upper:
                regime_text = line.split(":", 1)[-1].strip().lower()
                if "bull" in regime_text:
                    regime = MarketRegime.BULL
                elif "bear" in regime_text:
                    regime = MarketRegime.BEAR
                else:
                    regime = MarketRegime.NEUTRAL
            elif "CONFIDENCE:" in upper:
                conf_text = line.split(":", 1)[-1].strip()
                try:
                    confidence = float(conf_text.replace("%", "")) / 100 if "%" in conf_text else float(conf_text)
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass

        return RegimeOutput(
            regime=regime,
            confidence=confidence,
            volatility_index=volatility,
            trend_strength=abs(sma_slope),
            sp500_trend="UP" if sma_slope > 0 else "DOWN",
            indicators={
                "rsi": round(rsi, 1),
                "sma_50": round(sma_50, 2),
                "sma_200": round(sma_200, 2),
                "volatility": round(volatility, 4),
                **provider_metadata,
            },
            reasoning=analysis,
        )

    @staticmethod
    def _compute_rsi(prices: np.ndarray, period: int = 14) -> float:
        """Compute RSI for a price series."""
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
