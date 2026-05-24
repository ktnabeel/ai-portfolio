"""Decision Agent — Options strategy selection (Call/Put/Strangle).

Responsibility:
  1. Combine ALL previous agent outputs (Security, Sentiment, Regime)
  2. Analyze the options chain for the target security
  3. Select the optimal options strategy: Call, Put, Strangle, or No Trade
  4. Recommend specific strike, expiration, and contracts
  5. Calculate max risk, max reward, and breakeven

Uses:
  - OpenAI GPT-4o for strategy reasoning and selection
  - Options chain data (Polygon.io or synthetic)
  - All upstream agent outputs as context
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..models import (
    MarketRegime,
    OptionChain,
    OptionContract,
    OptionStrategy,
    RegimeOutput,
    RiskSentimentOutput,
    SecurityInfo,
    StrategyDecision,
)
from ..options.polygon_client import fetch_option_chain


SYSTEM_PROMPT = """You are the Options Strategy Decision Agent in a multi-agent trading system.

Your responsibilities:
1. Analyze all upstream agent outputs to understand the full market context
2. Evaluate the options chain data for the target security
3. Select the optimal strategy: Long Call, Long Put, Long Strangle, or No Trade
4. Recommend specific strike price and expiration date
5. Calculate max risk, max reward, and breakeven points

Strategy Selection Guide:
- LONG CALL: Bullish outlook. Use when regime is Bull or Neutral with upward bias,
  IV is moderate (<50%), and there's positive momentum. Select ATM or slightly OTM call.
- LONG PUT: Bearish outlook. Use when regime is Bear or Neutral with downward bias,
  IV is moderate, and there's negative momentum. Select ATM or slightly OTM put.
- LONG STRANGLE: High volatility expected, direction unclear. Use when regime is Neutral
  with high IV or during major events (earnings, FOMC). Buy OTM call + OTM put.
- NO TRADE: When conditions are unfavorable — excessive IV, unclear direction,
  or the security has no options. Always err on the side of caution.

For each decision, provide:
1. STRATEGY: Call / Put / Strangle / No Trade
2. CONFIDENCE: 0.0-1.0
3. RATIONALE: 2-4 sentences explaining the reasoning
4. RECOMMENDED STRIKE and EXPIRATION
5. MAX RISK, MAX REWARD, BREAKEVEN (if applicable)
6. ALTERNATIVES: 1-2 alternative strategies considered

Be thorough but decisive. Explain WHY this strategy fits the current conditions."""


class DecisionAgent:
    """Agent #4: Strategy Decision & Options Selection."""

    NAME = "Decision"

    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.3)

    def decide(
        self,
        security: SecurityInfo,
        sentiment: RiskSentimentOutput,
        regime: RegimeOutput,
        chain: OptionChain,
    ) -> StrategyDecision:
        """Select the optimal options strategy.

        Args:
            security: Security identification from Agent #1.
            sentiment: Market sentiment from Agent #2.
            regime: Market regime from Agent #3.
            chain: Options chain data.

        Returns:
            StrategyDecision with selected strategy and details.
        """
        # Build comprehensive context
        context = f"""
═══ SECURITY ANALYSIS ═══
Symbol: {security.symbol} ({security.company_name})
Sector: {security.sector} / {security.industry}
Current Price: ${security.current_price:.2f}" if security.current_price else "N/A"
Options Available: {'Yes' if security.is_optionable else 'No'}
Market Cap: ${security.market_cap:,.0f}" if security.market_cap else "N/A"

═══ MARKET SENTIMENT ═══
Fear & Greed: {sentiment.fear_greed.value}/100 ({sentiment.fear_greed.zone.value})
Market Trend: {sentiment.market_trend}
Risk Level: {sentiment.risk_assessment}
News Impact: {sum(1 for n in sentiment.top_news if n.impact == 'Positive')} positive, {sum(1 for n in sentiment.top_news if n.impact == 'Negative')} negative headlines

═══ MARKET REGIME ═══
Regime: {regime.regime.value} (confidence: {regime.confidence:.0%})
S&P 500 Trend: {regime.sp500_trend}
Volatility: {regime.volatility_index:.1%}" if regime.volatility_index else "N/A"
"""

        if regime.indicators:
            context += "Indicators: " + ", ".join(f"{k}={v}" for k, v in regime.indicators.items()) + "\n"

        # Options chain summary
        atm_strike = min(chain.calls, key=lambda c: abs(c.strike - chain.underlying_price)) if chain.calls else None
        atm_iv = atm_strike.implied_volatility if atm_strike else 0.30

        context += f"""
═══ OPTIONS CHAIN ═══
Underlying: ${chain.underlying_price:.2f}
ATM IV: {atm_iv:.1%}
Available Strikes: {len(chain.calls)} calls, {len(chain.puts)} puts
Expirations: {', '.join(chain.expiration_dates[:4])}
"""

        # Add top 3 ATM/near-ATM contracts
        if chain.calls:
            sorted_calls = sorted(chain.calls, key=lambda c: abs(c.strike - chain.underlying_price))[:3]
            context += "\nNear-ATM Calls:\n"
            for c in sorted_calls:
                context += f"  ${c.strike:.2f}: Bid=${c.bid:.2f} Ask=${c.ask:.2f}, IV={c.implied_volatility:.1%}, Delta={c.delta:.2f}, Vol={c.volume}\n"

        if chain.puts:
            sorted_puts = sorted(chain.puts, key=lambda c: abs(c.strike - chain.underlying_price))[:3]
            context += "\nNear-ATM Puts:\n"
            for p in sorted_puts:
                context += f"  ${p.strike:.2f}: Bid=${p.bid:.2f} Ask=${p.ask:.2f}, IV={p.implied_volatility:.1%}, Delta={p.delta:.2f}, Vol={p.volume}\n"

        context += f"""
═══ DECISION TASK ═══
Based on the above context, determine the optimal options strategy for {security.symbol}.
Respond with:
STRATEGY: [Call/Put/Strangle/No Trade]
CONFIDENCE: [0.0-1.0]
RATIONALE: [2-4 sentences]
STRIKE: [recommended strike price]
EXPIRATION: [recommended expiration date]
MAX RISK: [total premium paid]
MAX REWARD: [unlimited or specific target]
BREAKEVEN: [strike +/- premium]
ALTERNATIVES: [1-2 alternatives considered]
"""

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=context),
            ]
            response = self.llm.invoke(messages)
            analysis = str(response.content) if hasattr(response, 'content') else str(response)
        except Exception as e:
            # Rule-based fallback
            analysis = self._fallback_decision(security, regime, chain)

        # Parse the response
        strategy = OptionStrategy.NO_TRADE
        confidence = 0.5
        rationale = ""
        recommended_strike: float | None = None
        recommended_exp: str | None = None
        max_risk: float | None = None
        max_reward: float | None = None
        breakeven = ""
        alternatives: list[str] = []

        for line in analysis.split("\n"):
            upper = line.strip().upper()
            if upper.startswith("STRATEGY:"):
                strat_text = line.split(":", 1)[-1].strip().lower()
                if "strangle" in strat_text:
                    strategy = OptionStrategy.STRANGLE
                elif "call" in strat_text:
                    strategy = OptionStrategy.CALL
                elif "put" in strat_text:
                    strategy = OptionStrategy.PUT
                else:
                    strategy = OptionStrategy.NO_TRADE
            elif upper.startswith("CONFIDENCE:"):
                conf_text = line.split(":", 1)[-1].strip()
                try:
                    confidence = float(conf_text.replace("%", "")) / 100 if "%" in conf_text else float(conf_text)
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass
            elif upper.startswith("RATIONALE:"):
                rationale = line.split(":", 1)[-1].strip()
            elif upper.startswith("STRIKE:"):
                try:
                    recommended_strike = float(line.split(":", 1)[-1].strip().replace("$", ""))
                except ValueError:
                    pass
            elif upper.startswith("EXPIRATION:"):
                recommended_exp = line.split(":", 1)[-1].strip()
            elif upper.startswith("MAX RISK:"):
                try:
                    max_risk = float(line.split(":", 1)[-1].strip().replace("$", "").split()[0])
                except (ValueError, IndexError):
                    pass
            elif upper.startswith("MAX REWARD:"):
                reward_text = line.split(":", 1)[-1].strip()
                if "unlimited" in reward_text.lower():
                    max_reward = float("inf")
                else:
                    try:
                        max_reward = float(reward_text.replace("$", "").split()[0])
                    except (ValueError, IndexError):
                        pass
            elif upper.startswith("BREAKEVEN:"):
                breakeven = line.split(":", 1)[-1].strip()
            elif upper.startswith("ALTERNATIVES:"):
                alt_text = line.split(":", 1)[-1].strip()
                alternatives = [a.strip() for a in alt_text.split(";") if a.strip()]

        if not rationale:
            rationale = analysis[:300]

        # Find the recommended contracts
        call_contract = None
        put_contract = None
        if recommended_strike:
            for c in chain.calls:
                if abs(c.strike - recommended_strike) < 0.01:
                    call_contract = c
                    break
            for p in chain.puts:
                if abs(p.strike - recommended_strike) < 0.01:
                    put_contract = p
                    break

        # Recalculate max risk if we have contracts
        if strategy == OptionStrategy.CALL and call_contract:
            if max_risk is None:
                max_risk = call_contract.ask * 100
            if not breakeven and call_contract.strike:
                breakeven = f"${call_contract.strike + call_contract.ask:.2f}"
        elif strategy == OptionStrategy.PUT and put_contract:
            if max_risk is None:
                max_risk = put_contract.ask * 100
            if not breakeven and put_contract.strike:
                breakeven = f"${put_contract.strike - put_contract.ask:.2f}"
        elif strategy == OptionStrategy.STRANGLE:
            otm_call = min((c for c in chain.calls if c.strike > chain.underlying_price), key=lambda c: c.strike - chain.underlying_price, default=None)
            otm_put = max((p for p in chain.puts if p.strike < chain.underlying_price), key=lambda p: p.strike, default=None)
            if otm_call and otm_put and max_risk is None:
                max_risk = (otm_call.ask + otm_put.ask) * 100
            if otm_call and otm_put and not breakeven:
                total_prem = otm_call.ask + otm_put.ask
                breakeven = f"${otm_put.strike - total_prem:.2f} / ${otm_call.strike + total_prem:.2f}"

        return StrategyDecision(
            strategy=strategy,
            confidence=confidence,
            rationale=rationale,
            recommended_strike=recommended_strike,
            recommended_expiration=recommended_exp or (chain.expiration_dates[0] if chain.expiration_dates else None),
            call_contract=call_contract,
            put_contract=put_contract,
            max_risk=max_risk,
            max_reward=max_reward,
            breakeven=breakeven,
            alternatives=alternatives,
        )

    def _fallback_decision(
        self,
        security: SecurityInfo,
        regime: RegimeOutput,
        chain: OptionChain,
    ) -> str:
        """Rule-based fallback when LLM is unavailable."""
        if not security.is_optionable:
            return "STRATEGY: No Trade\nCONFIDENCE: 0.9\nRATIONALE: This security does not have listed options."

        if regime.regime == MarketRegime.BULL:
            strategy = "Call"
        elif regime.regime == MarketRegime.BEAR:
            strategy = "Put"
        else:
            strategy = "Strangle" if (regime.volatility_index or 0.2) > 0.25 else "No Trade"

        return (
            f"STRATEGY: {strategy}\n"
            f"CONFIDENCE: {regime.confidence:.0%}\n"
            f"RATIONALE: Rule-based fallback. Regime is {regime.regime.value} "
            f"(confidence {regime.confidence:.0%}).\n"
            f"STRIKE: ${chain.underlying_price:.2f}\n"
            f"EXPIRATION: {chain.expiration_dates[0] if chain.expiration_dates else '30 DTE'}\n"
            f"ALTERNATIVES: No Trade (preserve capital)"
        )
