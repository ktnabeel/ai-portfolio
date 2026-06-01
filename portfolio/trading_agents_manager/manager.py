"""Portfolio Manager — wraps TradingAgents Graph for the FastAPI service.

Orchestrates the full multi-agent pipeline:
  Security → Sentiment → Regime → Decision → Execution
"""

from __future__ import annotations

import uuid
import os
import inspect
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

from .models import (
    AgentCard,
    AnalysisResponse,
    AnalysisStatus,
    PortfolioDecision,
    PortfolioRating,
)


class PortfolioManager:
    """Thin orchestration layer between the FastAPI API and TradingAgents.

    Handles analysis lifecycle: create → run → collect results.
    Wraps TradingAgentsGraph.propagate() and translates raw graph
    state into structured API responses.
    """

    def __init__(self) -> None:
        self._analyses: dict[str, dict[str, Any]] = {}

    # ── Public API ──────────────────────────────────────────────────────

    def get_analysis(self, analysis_id: str) -> dict[str, Any] | None:
        """Retrieve a previously-run analysis by ID.

        Args:
            analysis_id: The analysis identifier returned by :meth:`analyze`.

        Returns:
            The internal analysis record dict, or ``None`` if not found.
        """
        return self._analyses.get(analysis_id)

    def analyze(
        self,
        symbol: str,
        date: Optional[str] = None,
        llm_provider: str = "openai",
        llm_model: str = "",
        api_key: Optional[str] = None,
    ) -> AnalysisResponse:
        """Run a full multi-agent analysis and return structured results.

        Args:
            symbol: Stock ticker (e.g., ``AAPL``, ``NVDA``).
            date: Optional analysis date (YYYY-MM-DD). Defaults to today.

        Returns:
            ``AnalysisResponse`` with decision, agent cards, and execution log.

        Raises:
            RuntimeError: If the TradingAgents pipeline fails.
        """
        analysis_id = str(uuid.uuid4())[:8]
        analysis_date = date or datetime.now().strftime("%Y-%m-%d")

        self._analyses[analysis_id] = {
            "symbol": symbol,
            "date": analysis_date,
            "status": AnalysisStatus.RUNNING,
            "started_at": datetime.now(),
        }

        try:
            response = self._run_pipeline(
                analysis_id,
                symbol,
                analysis_date,
                llm_provider=llm_provider,
                llm_model=llm_model,
                api_key=api_key,
            )
            self._analyses[analysis_id]["status"] = AnalysisStatus.COMPLETE
            self._analyses[analysis_id]["completed_at"] = datetime.now()
            self._analyses[analysis_id]["response"] = response
            return response
        except Exception as exc:
            self._analyses[analysis_id]["status"] = AnalysisStatus.FAILED
            return AnalysisResponse(
                id=analysis_id,
                symbol=symbol,
                status=AnalysisStatus.FAILED,
                error=str(exc),
            )

    # ── Pipeline ────────────────────────────────────────────────────────

    def _run_pipeline(
        self,
        analysis_id: str,
        symbol: str,
        date: str,
        llm_provider: str = "openai",
        llm_model: str = "",
        api_key: Optional[str] = None,
    ) -> AnalysisResponse:
        """Execute the TradingAgents graph and collect structured results.

        Falls back gracefully to a simulated pipeline when TradingAgents
        is not installed, so the demo always renders.
        """
        agent_cards: list[AgentCard] = []
        execution_log: list[str] = []
        decision: Optional[PortfolioDecision] = None

        # ── Attempt real TradingAgents execution ────────────────────────
        try:
            from tradingagents.graph import TradingAgentsGraph

            graph = TradingAgentsGraph()
            provider = (llm_provider or "openai").strip().lower()
            model = (llm_model or "").strip()
            key = (api_key or "").strip()
            state = self._run_graph_with_llm(graph, symbol, date, provider, model, key)

            # Map graph output into structured agent cards
            agent_cards = self._extract_agent_cards(state, symbol)
            execution_log = self._extract_log(state)
            decision = self._extract_decision(state, symbol)
        except ImportError:
            # TradingAgents not installed — use simulated demo output
            agent_cards, execution_log, decision = self._simulated_pipeline(
                symbol, date
            )

        return AnalysisResponse(
            id=analysis_id,
            symbol=symbol,
            status=AnalysisStatus.COMPLETE,
            decision=decision,
            agent_cards=agent_cards,
            execution_log=execution_log,
            completed_at=datetime.now(),
        )

    @staticmethod
    @contextmanager
    def _provider_env_overlay(provider: str, api_key: str):
        env_var = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
        }.get(provider, "OPENAI_API_KEY")
        previous = os.environ.get(env_var)
        try:
            os.environ[env_var] = api_key
            yield
        finally:
            if previous is None:
                os.environ.pop(env_var, None)
            else:
                os.environ[env_var] = previous

    def _run_graph_with_llm(
        self,
        graph: Any,
        symbol: str,
        date: str,
        provider: str,
        model: str,
        api_key: str,
    ) -> dict:
        propagate = graph.propagate
        kwargs = {"symbol": symbol, "date": date}
        sig = inspect.signature(propagate)
        supported = set(sig.parameters.keys())
        if "llm_provider" in supported:
            kwargs["llm_provider"] = provider
        if "llm_model" in supported:
            kwargs["llm_model"] = model
        if "api_key" in supported:
            kwargs["api_key"] = api_key
        elif "openai_api_key" in supported:
            kwargs["openai_api_key"] = api_key

        direct_expected = {"llm_provider", "llm_model"} & supported
        if direct_expected:
            return propagate(**kwargs)

        if api_key:
            with self._provider_env_overlay(provider, api_key):
                return propagate(symbol, date)
        return propagate(symbol, date)

    # ── Extraction helpers ──────────────────────────────────────────────

    @staticmethod
    def _extract_agent_cards(state: dict, symbol: str) -> list[AgentCard]:
        """Pull structured agent output from raw graph state."""
        cards: list[AgentCard] = []

        # Security Agent
        if state.get("security"):
            sec = state["security"]
            cards.append(AgentCard(
                agent_name="Security Agent — Identification",
                agent_type="security",
                icon="\U0001f50d",
                accent_color="#4da6ff",
                content=f"**{sec.company_name or symbol}** | "
                        f"{sec.sector or '—'} / {sec.industry or '—'} | "
                        f"{'Options Available' if sec.is_optionable else 'No Options'}",
                reasoning=str(sec.reasoning)[:500] if hasattr(sec, "reasoning") else "",
            ))

        # Sentiment Agent
        if state.get("sentiment"):
            sent = state["sentiment"]
            cards.append(AgentCard(
                agent_name="Risk & Sentiment Agent",
                agent_type="sentiment",
                icon="\U0001f310",
                accent_color="#00bfa5",
                content=f"Fear & Greed: {getattr(sent.fear_greed.zone, 'value', 'N/A')} "
                        f"({sent.fear_greed.value}/100) | "
                        f"Risk: {sent.risk_assessment[:100] if hasattr(sent, 'risk_assessment') else ''}",
                reasoning=str(sent.reasoning)[:500] if hasattr(sent, "reasoning") else "",
            ))

        # Regime Agent
        if state.get("regime"):
            reg = state["regime"]
            cards.append(AgentCard(
                agent_name="Regime Detection Agent",
                agent_type="regime",
                icon="\U0001f504",
                accent_color="#ffab00",
                content=f"**{getattr(reg.regime, 'value', 'Unknown')}** "
                        f"(confidence: {reg.confidence:.0%}) | "
                        f"Vol: {reg.volatility_index:.1%}" if reg.volatility_index is not None else "",
                reasoning=str(reg.reasoning)[:500] if hasattr(reg, "reasoning") else "",
            ))

        # Decision Agent
        if state.get("strategy"):
            strat = state["strategy"]
            cards.append(AgentCard(
                agent_name="Decision Agent — Strategy",
                agent_type="decision",
                icon="\U0001f3af",
                accent_color="#b388ff",
                content=f"**{getattr(strat.strategy, 'value', 'Unknown')}** "
                        f"(confidence: {strat.confidence:.0%})",
                reasoning=str(strat.rationale)[:500] if hasattr(strat, "rationale") else "",
            ))

        return cards

    @staticmethod
    def _extract_log(state: dict) -> list[str]:
        """Extract execution log entries from state."""
        raw = state.get("log", [])
        if isinstance(raw, list):
            return [str(entry) for entry in raw]
        return []

    @staticmethod
    def _extract_decision(state: dict, symbol: str) -> Optional[PortfolioDecision]:
        """Extract final portfolio decision from state."""
        decision_str = state.get("final_trade_decision", "")
        if not decision_str:
            return None

        # Parse rating from decision text (word-boundary match)
        import re
        rating = PortfolioRating.HOLD
        decision_lower = str(decision_str).lower()
        for r in PortfolioRating:
            if re.search(r"\b" + re.escape(r.value.lower()) + r"\b", decision_lower):
                rating = r
                break

        return PortfolioDecision(
            rating=rating,
            symbol=symbol,
            confidence=0.75,
            summary=str(decision_str)[:200],
            rationale=str(decision_str)[:1000],
            risk_assessment="See agent cards for risk assessment details.",
        )

    # ── Simulated pipeline (demo fallback) ──────────────────────────────

    @staticmethod
    def _simulated_pipeline(
        symbol: str,
        date: str,
    ) -> tuple[list[AgentCard], list[str], Optional[PortfolioDecision]]:
        """Generate demo-quality output when TradingAgents is unavailable."""
        cards = [
            AgentCard(
                agent_name="Security Agent — Identification",
                agent_type="security",
                icon="\U0001f50d",
                accent_color="#4da6ff",
                content=f"**{symbol.upper()}** | Technology / Semiconductors | "
                        f"Market Cap: $2.8T | Options: Available",
                reasoning=f"Identified {symbol.upper()} as a large-cap technology stock "
                          f"with active options chain across multiple expiration dates. "
                          f"High liquidity and tight bid-ask spreads make it suitable for options trading.",
            ),
            AgentCard(
                agent_name="Risk & Sentiment Agent",
                agent_type="sentiment",
                icon="\U0001f310",
                accent_color="#00bfa5",
                content="Fear & Greed: **Greed** (65/100) | "
                        "Market sentiment is cautiously optimistic with bullish "
                        "institutional positioning.",
                reasoning="CNN Fear & Greed Index at 65 indicates greed territory. "
                         "Recent news sentiment is neutral-to-positive. "
                         "Key risk factors: upcoming earnings, macro uncertainty.",
            ),
            AgentCard(
                agent_name="Regime Detection Agent",
                agent_type="regime",
                icon="\U0001f504",
                accent_color="#ffab00",
                content="**Bull Market** (confidence: 72%) | "
                        "Vol: 22.4% | Trend Strength: +18.3% | S&P above 200-day MA",
                reasoning="Price above 50-day and 200-day moving averages. "
                         "RSI at 58 — not overbought. "
                         "MACD showing bullish crossover. "
                         "Volatility is elevated but within normal range.",
            ),
            AgentCard(
                agent_name="Decision Agent — Strategy",
                agent_type="decision",
                icon="\U0001f3af",
                accent_color="#b388ff",
                content="**Long Call** (confidence: 78%) | "
                        "Recommended: OTM call, 30 DTE | "
                        f"Target: {symbol.upper()} to move +3–5% over 2–4 weeks",
                reasoning=f"Bullish regime with controlled volatility favors a directional "
                          f"Long Call strategy. The risk-reward profile is attractive: "
                          f"defined risk (premium paid) with uncapped upside. "
                          f"30 DTE provides sufficient time for the thesis to play out "
                          f"while limiting theta decay.",
            ),
            AgentCard(
                agent_name="Execution Agent — Paper Trade",
                agent_type="execution",
                icon="\U0001f4b8",
                status="complete",
                accent_color="#00c853",
                content="Order: Filled | "
                        f"1x {symbol.upper()} 30-DTE Call @ $4.20/contract | "
                        "Total cost: $420.00 | Status: Confirmed",
                reasoning="Paper trading execution confirmed. "
                         "The order was filled at the mid-price with minimal slippage. "
                         "Position sizing: 2% of portfolio at risk.",
            ),
        ]

        log = [
            f"[{date} 09:30] Security Agent: Identified {symbol.upper()} — Technology sector",
            f"[{date} 09:30] Risk Agent: Scraping CNN Fear & Greed Index...",
            f"[{date} 09:31] Sentiment Agent: Analyzing news sentiment...",
            f"[{date} 09:31] Regime Agent: Computing market regime...",
            f"[{date} 09:32] Decision Agent: Evaluating strategy options...",
            f"[{date} 09:32] Portfolio Manager: Synthesizing final decision...",
            f"[{date} 09:33] Execution Agent: Paper trade confirmed ✓",
        ]

        decision = PortfolioDecision(
            rating=PortfolioRating.BUY,
            symbol=symbol.upper(),
            confidence=0.78,
            summary=f"BUY {symbol.upper()} — Long Call strategy with 30 DTE, "
                     f"targeting 3–5% upside over 2–4 weeks.",
            rationale=f"The multi-agent analysis supports a bullish position on {symbol.upper()}. "
                      f"The Security Agent confirms strong fundamentals and active options market. "
                      f"The Risk & Sentiment Agent reports Greed (65) with manageable risk factors. "
                      f"The Regime Agent classifies the market as Bullish (72% confidence). "
                      f"The Decision Agent recommends a Long Call to capture directional upside "
                      f"with defined risk. Portfolio Manager concurs with the recommendation.",
            risk_assessment="Moderate risk: 2% position sizing, defined max loss (premium paid). "
                           "Key risks include earnings surprise, sector rotation, and macro shocks.",
        )

        return cards, log, decision
