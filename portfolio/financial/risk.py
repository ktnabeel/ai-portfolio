"""Risk Assessment Agent - volatility, VaR, Sharpe, portfolio risk."""

import numpy as np
import yfinance as yf

from .models import AgentSignal, RiskLevel, SignalType, PortfolioHolding


class RiskAssessmentAgent:
    """Evaluates stock and portfolio risk metrics."""

    NAME = "Risk Assessment"

    def analyze_stock(self, ticker: str, info: dict, history) -> AgentSignal:
        if history is None or history.empty or len(history) < 20:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary=f"Insufficient data to assess risk for {ticker}.",
            )

        close = history["Close"].values
        returns = np.diff(close) / close[:-1]
        current_price = float(close[-1])

        volatility = float(np.std(returns) * np.sqrt(252))
        var_95 = float(np.percentile(returns, 5))
        sharpe = self._compute_sharpe(returns)
        max_drawdown = self._compute_max_drawdown(close)
        beta = info.get("beta", 1.0)

        if volatility > 0.50 or max_drawdown < -0.40:
            risk = RiskLevel.CRITICAL
        elif volatility > 0.35 or max_drawdown < -0.25:
            risk = RiskLevel.HIGH
        elif volatility > 0.20 or max_drawdown < -0.15:
            risk = RiskLevel.MODERATE
        else:
            risk = RiskLevel.LOW

        if risk == RiskLevel.LOW:
            signal = SignalType.BULLISH
            confidence = 0.6
        elif risk == RiskLevel.CRITICAL:
            signal = SignalType.BEARISH
            confidence = 0.7
        elif risk == RiskLevel.HIGH:
            signal = SignalType.BEARISH
            confidence = 0.5
        else:
            signal = SignalType.NEUTRAL
            confidence = 0.4

        return AgentSignal(
            agent_name=self.NAME,
            signal=signal,
            confidence=confidence,
            summary=(
                f"Risk: {risk.value} | "
                f"Vol={volatility:.1%} | "
                f"VaR={var_95:.1%} | "
                f"Sharpe={sharpe:.2f} | "
                f"MaxDD={max_drawdown:.1%}"
            ),
            metrics={
                "risk_level": risk.value,
                "volatility_annual": round(volatility, 4),
                "var_95": round(var_95, 4),
                "sharpe_ratio": round(sharpe, 2),
                "max_drawdown": round(max_drawdown, 4),
                "beta": beta,
                "current_price": current_price,
            },
        )

    def analyze_portfolio(self, holdings: list[PortfolioHolding]) -> AgentSignal:
        if not holdings:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary="No holdings to assess.",
                metrics={"risk_level": RiskLevel.LOW.value},
            )

        tickers = [h.ticker for h in holdings]
        try:
            data = yf.download(tickers, period="1y", progress=False)
        except Exception:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary="Could not fetch portfolio data.",
            )

        if data.empty:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary="Could not fetch portfolio data.",
            )

        closes = data["Close"]
        if len(tickers) == 1:
            closes = closes.to_frame()
            closes.columns = tickers

        returns = closes.pct_change().dropna()

        if returns.empty:
            return AgentSignal(
                agent_name=self.NAME,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                summary="Insufficient return data.",
            )

        weights = np.array([h.shares for h in holdings])
        weights = weights / weights.sum()

        cov_matrix = returns.cov() * 252
        port_var = float(weights.T @ cov_matrix.values @ weights)
        port_vol = float(np.sqrt(port_var))

        corr_matrix = returns.corr()
        corr_values = []
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                corr_values.append(corr_matrix.iloc[i, j])
        avg_corr = float(np.mean(corr_values)) if corr_values else 0.0
        diversification = 1.0 - max(0.0, min(1.0, avg_corr))

        if port_vol > 0.50:
            risk = RiskLevel.CRITICAL
        elif port_vol > 0.35:
            risk = RiskLevel.HIGH
        elif port_vol > 0.20:
            risk = RiskLevel.MODERATE
        else:
            risk = RiskLevel.LOW

        signal = SignalType.BULLISH if risk == RiskLevel.LOW else (
            SignalType.NEUTRAL if risk == RiskLevel.MODERATE else SignalType.BEARISH
        )

        return AgentSignal(
            agent_name=self.NAME,
            signal=signal,
            confidence=min(0.8, 0.4 + abs(port_vol)) if signal != SignalType.NEUTRAL else 0.35,
            summary=(
                f"Portfolio Risk: {risk.value} | "
                f"Vol={port_vol:.1%} | "
                f"Diversification={diversification:.0%} | "
                f"Holding{'s' if len(holdings) > 1 else ''}: {len(holdings)}"
            ),
            metrics={
                "risk_level": risk.value,
                "portfolio_volatility": round(port_vol, 4),
                "diversification_score": round(diversification, 3),
                "avg_correlation": round(avg_corr, 3),
                "num_holdings": len(holdings),
            },
        )

    @staticmethod
    def _compute_sharpe(returns, risk_free=0.04):
        if len(returns) == 0:
            return 0.0
        excess = np.mean(returns) * 252 - risk_free
        vol = np.std(returns) * np.sqrt(252)
        return float(excess / vol) if vol > 0 else 0.0

    @staticmethod
    def _compute_max_drawdown(prices):
        peak = np.maximum.accumulate(prices)
        drawdown = (prices - peak) / peak
        return float(np.min(drawdown))
