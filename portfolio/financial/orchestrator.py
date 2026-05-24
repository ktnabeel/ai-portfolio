"""Decision Orchestrator - coordinates agents with weighted scoring."""

from ._utils import fetch_stock_data
from .market_data import MarketDataAgent
from .technical import TechnicalAnalysisAgent
from .fundamental import FundamentalAnalysisAgent
from .sentiment import SentimentAnalysisAgent
from .risk import RiskAssessmentAgent
from .models import (
    AgentSignal,
    PortfolioHolding,
    PortfolioDecision,
    StockDecision,
    SignalType,
    RiskLevel,
    DecisionAction,
)


class DecisionOrchestrator:
    """Orchestrates multiple analysis agents to produce BUY/SELL/HOLD decisions."""

    AGENT_WEIGHTS = {
        "Market Data": 1.0,
        "Technical Analysis": 0.9,
        "Fundamental Analysis": 1.0,
        "Sentiment Analysis": 0.6,
        "Risk Assessment": 1.1,
    }

    def __init__(self):
        self.agents = {
            "Market Data": MarketDataAgent(),
            "Technical Analysis": TechnicalAnalysisAgent(),
            "Fundamental Analysis": FundamentalAnalysisAgent(),
            "Sentiment Analysis": SentimentAnalysisAgent(),
            "Risk Assessment": RiskAssessmentAgent(),
        }

    def analyze_stock(self, ticker: str) -> StockDecision:
        """Run all agents and produce a final decision."""
        ticker = ticker.strip().upper()
        info, history = fetch_stock_data(ticker)

        signals: list[AgentSignal] = []
        for agent_name, agent in self.agents.items():
            try:
                if agent_name == "Risk Assessment":
                    signal = agent.analyze_stock(ticker, info, history)
                else:
                    signal = agent.analyze(ticker, info, history)
                signals.append(signal)
            except Exception as e:
                signals.append(AgentSignal(
                    agent_name=agent_name,
                    signal=SignalType.NEUTRAL,
                    confidence=0.0,
                    summary=f"Agent error: {e}",
                ))

        current_price = 0.0
        for s in signals:
            if "price" in s.metrics and s.metrics["price"]:
                current_price = float(s.metrics["price"])
                break
        if current_price == 0.0 and history is not None and not history.empty:
            current_price = float(history["Close"].iloc[-1])

        weighted_score = 0.0
        total_weight = 0.0
        for s in signals:
            weight = self.AGENT_WEIGHTS.get(s.agent_name, 1.0)
            if s.signal == SignalType.BULLISH:
                weighted_score += s.confidence * weight
            elif s.signal == SignalType.BEARISH:
                weighted_score -= s.confidence * weight
            total_weight += weight

        avg_score = weighted_score / total_weight if total_weight > 0 else 0.0

        if avg_score > 0.15:
            action = DecisionAction.BUY
        elif avg_score < -0.15:
            action = DecisionAction.SELL
        else:
            action = DecisionAction.HOLD

        risk_level = RiskLevel.MODERATE
        for s in signals:
            if s.agent_name == "Risk Assessment":
                risk_raw = s.metrics.get("risk_level", "")
                if isinstance(risk_raw, RiskLevel):
                    risk_level = risk_raw
                elif risk_raw:
                    try:
                        risk_level = RiskLevel(risk_raw)
                    except ValueError:
                        pass
                break

        confidence = min(0.95, abs(avg_score) + 0.15)

        signal_summaries = "\n".join(
            f"  [{s.agent_name}] {s.signal.value} ({s.confidence:.0%}): {s.summary}"
            for s in signals
        )
        reasoning = (
            f"Weighted score: {avg_score:+.3f}\n"
            f"Agent signals:\n{signal_summaries}"
        )

        return StockDecision(
            ticker=ticker,
            action=action,
            confidence=confidence,
            risk_level=risk_level,
            current_price=current_price,
            signals=signals,
            reasoning=reasoning,
        )

    def analyze_portfolio(self, holdings: list[PortfolioHolding]) -> PortfolioDecision:
        """Analyze every holding in a portfolio and aggregate results."""
        decisions: list[StockDecision] = []
        for holding in holdings:
            decision = self.analyze_stock(holding.ticker)
            decisions.append(decision)

        risk_agent = self.agents["Risk Assessment"]
        try:
            risk_signal = risk_agent.analyze_portfolio(holdings)
            portfolio_risk = risk_signal.metrics.get("risk_level", RiskLevel.MODERATE)
            if isinstance(portfolio_risk, str):
                portfolio_risk = RiskLevel(portfolio_risk)
            diversification = risk_signal.metrics.get("diversification_score", 0.0)
        except Exception:
            portfolio_risk = RiskLevel.MODERATE
            diversification = 0.0

        buy_count = sum(1 for d in decisions if d.action == DecisionAction.BUY)
        sell_count = sum(1 for d in decisions if d.action == DecisionAction.SELL)
        hold_count = sum(1 for d in decisions if d.action == DecisionAction.HOLD)

        summary = (
            f"Portfolio: {len(decisions)} stocks analyzed. "
            f"Buy: {buy_count}, Sell: {sell_count}, Hold: {hold_count}. "
            f"Risk: {portfolio_risk.value}. Diversification: {diversification:.0%}"
        )

        return PortfolioDecision(
            decisions=decisions,
            portfolio_risk=portfolio_risk,
            diversification_score=diversification,
            summary=summary,
        )
