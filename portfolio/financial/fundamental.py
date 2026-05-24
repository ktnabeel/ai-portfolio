"""Fundamental Analysis Agent - P/E, EPS, margins, debt ratios."""

from .models import AgentSignal, SignalType


class FundamentalAnalysisAgent:
    """Analyzes P/E, EPS, revenue growth, margins, and debt ratios."""

    NAME = "Fundamental Analysis"

    def analyze(self, ticker: str, info: dict, history) -> AgentSignal:
        if not info:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary=f"No fundamental data available for {ticker}.",
            )

        pe_ratio = (
            info["trailingPE"] if info.get("trailingPE") is not None
            else info.get("forwardPE")
        )
        eps = info.get("trailingEps")
        debt_to_equity = info.get("debtToEquity")
        profit_margin = info.get("profitMargins")
        revenue_growth = info.get("revenueGrowth")
        roe = info.get("returnOnEquity")
        free_cashflow = info.get("freeCashflow")
        peg_ratio = info.get("pegRatio")

        scores = []
        details = []

        if pe_ratio is not None and pe_ratio > 0:
            details.append(f"P/E={pe_ratio:.1f}")
            if pe_ratio < 15:
                scores.append(0.8)
            elif pe_ratio < 25:
                scores.append(0.3)
            elif pe_ratio < 40:
                scores.append(-0.2)
            else:
                scores.append(-0.6)

        if peg_ratio is not None:
            if peg_ratio < 1.0:
                scores.append(0.7)
            elif peg_ratio < 2.0:
                scores.append(0.1)
            else:
                scores.append(-0.3)

        if eps is not None and eps > 0:
            details.append(f"EPS={eps:.2f}")
            scores.append(0.3)

        if debt_to_equity is not None:
            if debt_to_equity < 50:
                scores.append(0.5)
            elif debt_to_equity < 100:
                scores.append(0.0)
            else:
                scores.append(-0.5)

        if profit_margin is not None:
            details.append(f"Margin={profit_margin:.1%}")
            if profit_margin > 0.15:
                scores.append(0.6)
            elif profit_margin > 0.05:
                scores.append(0.2)
            elif profit_margin > 0:
                scores.append(-0.2)
            else:
                scores.append(-0.7)

        if revenue_growth is not None:
            details.append(f"RevGrowth={revenue_growth:.1%}")
            if revenue_growth > 0.10:
                scores.append(0.6)
            elif revenue_growth > 0:
                scores.append(0.2)
            else:
                scores.append(-0.4)

        if roe is not None:
            if roe > 0.15:
                scores.append(0.5)
            elif roe > 0:
                scores.append(0.1)
            else:
                scores.append(-0.3)

        if free_cashflow is not None:
            if free_cashflow > 0:
                scores.append(0.4)
            else:
                scores.append(-0.4)

        if not scores:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.3,
                summary="Limited fundamental data available.",
                metrics=self._build_metrics(info),
            )

        composite = float(sum(scores) / len(scores))
        confidence = min(0.8, abs(composite) + 0.15)

        if composite > 0.2:
            signal = SignalType.BULLISH
        elif composite < -0.2:
            signal = SignalType.BEARISH
        else:
            signal = SignalType.NEUTRAL

        return AgentSignal(
            agent_name=self.NAME,
            signal=signal,
            confidence=confidence,
            summary=f"Fundamental composite: {composite:+.2f} | {' '.join(details)}",
            metrics=self._build_metrics(info),
        )

    @staticmethod
    def _build_metrics(info: dict) -> dict:
        return {
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "pb_ratio": info.get("priceToBook"),
            "debt_to_equity": info.get("debtToEquity"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "roe": info.get("returnOnEquity"),
            "peg_ratio": info.get("pegRatio"),
            "current_ratio": info.get("currentRatio"),
            "free_cashflow": info.get("freeCashflow"),
            "market_cap": info.get("marketCap"),
        }
