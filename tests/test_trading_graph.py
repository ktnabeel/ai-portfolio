"""End-to-end tests for the LangGraph trading workflow with mocked LLM calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from portfolio.trading.graph.state import TradingState
from portfolio.trading.graph.trading_graph import (
    build_trading_graph,
    run_trading_workflow,
    _node_security,
    _node_sentiment,
    _node_regime,
    _node_fetch_chain,
    _node_decision,
    _node_execution,
)
from portfolio.trading.models import (
    ExecutionResult,
    FearGreedData,
    FearGreedZone,
    MarketRegime,
    OptionChain,
    OptionContract,
    OptionStrategy,
    OrderRequest,
    RegimeOutput,
    RiskSentimentOutput,
    SecurityInfo,
    StrategyDecision,
)


@pytest.fixture
def mock_security():
    return SecurityInfo(
        symbol="AAPL", company_name="Apple Inc.",
        sector="Technology", industry="Consumer Electronics",
        market_cap=3_000_000_000_000, current_price=185.50,
        exchange="NASDAQ", is_optionable=True,
        reasoning="Apple is a technology giant.",
    )


@pytest.fixture
def mock_fear_greed():
    return FearGreedData(
        value=45, zone=FearGreedZone.NEUTRAL,
        description="Investors are neutral.",
        previous_close=44,
    )


@pytest.fixture
def mock_sentiment(mock_fear_greed):
    return RiskSentimentOutput(
        fear_greed=mock_fear_greed,
        top_news=[],
        market_trend="Neutral market.",
        risk_assessment="MODERATE",
        reasoning="Balanced sentiment.",
    )


@pytest.fixture
def mock_regime():
    return RegimeOutput(
        regime=MarketRegime.BULL, confidence=0.75,
        volatility_index=0.18, trend_strength=0.03,
        sp500_trend="UP",
        indicators={"rsi": 62.0, "sma_50": 475.0, "sma_200": 450.0},
        reasoning="S&P 500 above moving averages — bullish.",
    )


@pytest.fixture
def mock_option_chain():
    atm = 185.50
    return OptionChain(
        symbol="AAPL", underlying_price=atm,
        expiration_dates=["2026-06-15", "2026-07-15"],
        calls=[
            OptionContract(
                symbol="AAPL250615C00180000", strike=180,
                expiration="2026-06-15", option_type="call",
                bid=8.50, ask=8.80, last=8.65, volume=1200,
                open_interest=5000, implied_volatility=0.28,
                delta=0.65, gamma=0.03, theta=-0.05, vega=0.20,
            ),
            OptionContract(
                symbol="AAPL250615C00185500", strike=185,
                expiration="2026-06-15", option_type="call",
                bid=5.00, ask=5.20, last=5.10, volume=800,
                open_interest=3500, implied_volatility=0.26,
                delta=0.52, gamma=0.04, theta=-0.04, vega=0.18,
            ),
        ],
        puts=[
            OptionContract(
                symbol="AAPL250615P00180000", strike=180,
                expiration="2026-06-15", option_type="put",
                bid=2.20, ask=2.40, last=2.30, volume=900,
                open_interest=4000, implied_volatility=0.28,
                delta=-0.35, gamma=0.03, theta=-0.04, vega=0.20,
            ),
            OptionContract(
                symbol="AAPL250615P00185500", strike=185,
                expiration="2026-06-15", option_type="put",
                bid=4.50, ask=4.70, last=4.60, volume=700,
                open_interest=3100, implied_volatility=0.26,
                delta=-0.47, gamma=0.04, theta=-0.03, vega=0.18,
            ),
        ],
    )


@pytest.fixture
def mock_strategy_call():
    return StrategyDecision(
        strategy=OptionStrategy.CALL, confidence=0.80,
        rationale="Bullish regime with moderate IV.",
        recommended_strike=185.0, recommended_expiration="2026-06-15",
        max_risk=520.0, max_reward=float("inf"),
        breakeven="$190.20",
        alternatives=["No Trade"],
    )


# ════════════════════════════════════════════════════════════════════════
# Graph Construction
# ════════════════════════════════════════════════════════════════════════

class TestGraphConstruction:
    def test_build_graph_returns_compiled_graph(self):
        graph = build_trading_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_has_all_nodes(self):
        graph = build_trading_graph()
        nodes = graph.get_graph().nodes
        node_names = {n for n in nodes.keys()}
        expected = {"security_agent", "sentiment_agent", "regime_agent", "fetch_chain",
                     "decision_agent", "execution_agent", "__start__", "__end__"}
        assert node_names == expected


# ════════════════════════════════════════════════════════════════════════
# Node Error Isolation
# ════════════════════════════════════════════════════════════════════════

class TestNodeErrorIsolation:
    def _empty_state(self, symbol="AAPL"):
        return {
            "symbol": symbol,
            "security": None, "sentiment": None, "regime": None,
            "options_chain": None, "strategy": None, "execution": None,
            "error": "", "stage": "init", "messages": [], "log": [],
        }

    def test_security_node_survives_error(self):
        state = self._empty_state()
        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as mock:
            mock.return_value.analyze.side_effect = RuntimeError("API down")
            result = _node_security(state)
            assert "stage" in result

    def test_sentiment_node_survives_error(self):
        state = self._empty_state()
        with patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as mock:
            mock.return_value.analyze.side_effect = RuntimeError("Scraping failed")
            result = _node_sentiment(state)
            assert "stage" in result

    def test_regime_node_survives_error(self):
        state = self._empty_state()
        with patch("portfolio.trading.graph.trading_graph.RegimeAgent") as mock:
            mock.return_value.analyze.side_effect = RuntimeError("Data error")
            result = _node_regime(state)
            assert "stage" in result

    def test_fetch_chain_node_survives_error(self):
        state = self._empty_state()
        with patch("portfolio.trading.graph.trading_graph.fetch_option_chain") as mock:
            mock.side_effect = RuntimeError("Polygon API down")
            result = _node_fetch_chain(state)
            assert "stage" in result

    def test_decision_node_survives_error(self):
        state = self._empty_state()
        with patch("portfolio.trading.graph.trading_graph.DecisionAgent") as mock:
            mock.return_value.decide.side_effect = RuntimeError("LLM timeout")
            result = _node_decision(state)
            assert "stage" in result

    def test_execution_node_survives_error(self):
        state = self._empty_state()
        with patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as mock:
            mock.return_value.execute.side_effect = RuntimeError("MCP unreachable")
            result = _node_execution(state)
            assert "stage" in result


# ════════════════════════════════════════════════════════════════════════
# Node Outputs
# ════════════════════════════════════════════════════════════════════════

class TestNodeOutputs:
    def test_security_node_writes_security(self, mock_security):
        state = {"symbol": "AAPL", "security": None, "sentiment": None,
                 "regime": None, "options_chain": None, "strategy": None,
                 "execution": None, "error": "", "stage": "init",
                 "messages": [], "log": []}
        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as mock:
            mock.return_value.analyze.return_value = mock_security
            result = _node_security(state)
            assert result["security"] == mock_security
            assert result["stage"] == "security"
            assert len(result["log"]) > 0

    def test_sentiment_node_writes_sentiment(self, mock_sentiment):
        state = {"symbol": "AAPL", "security": None, "sentiment": None,
                 "regime": None, "options_chain": None, "strategy": None,
                 "execution": None, "error": "", "stage": "init",
                 "messages": [], "log": []}
        with patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as mock:
            mock.return_value.analyze.return_value = mock_sentiment
            result = _node_sentiment(state)
            assert result["sentiment"] == mock_sentiment
            assert result["stage"] == "sentiment"

    def test_regime_node_writes_regime(self, mock_regime):
        state = {"symbol": "AAPL", "security": None, "sentiment": None,
                 "regime": None, "options_chain": None, "strategy": None,
                 "execution": None, "error": "", "stage": "init",
                 "messages": [], "log": []}
        with patch("portfolio.trading.graph.trading_graph.RegimeAgent") as mock:
            mock.return_value.analyze.return_value = mock_regime
            result = _node_regime(state)
            assert result["regime"] == mock_regime
            assert result["stage"] == "regime"

    def test_decision_node_writes_strategy(self, mock_security, mock_sentiment,
                                            mock_regime, mock_option_chain, mock_strategy_call):
        state = {"symbol": "AAPL", "security": mock_security,
                 "sentiment": mock_sentiment, "regime": mock_regime,
                 "options_chain": mock_option_chain,
                 "strategy": None, "execution": None,
                 "error": "", "stage": "init", "messages": [], "log": []}
        with patch("portfolio.trading.graph.trading_graph.DecisionAgent") as mock:
            mock.return_value.decide.return_value = mock_strategy_call
            result = _node_decision(state)
            assert result["strategy"] == mock_strategy_call
            assert result["stage"] == "decision"

    def test_execution_node_writes_execution(self, mock_strategy_call):
        state = {"symbol": "AAPL", "security": None, "sentiment": None,
                 "regime": None, "options_chain": None,
                 "strategy": mock_strategy_call, "execution": None,
                 "error": "", "stage": "init", "messages": [], "log": []}
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="AAPL", strategy=OptionStrategy.CALL),
            confirmation={"status": "Filled", "order_id": "ORD-TEST"},
            reasoning="Trade executed.",
        )
        with patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as mock:
            mock.return_value.execute.return_value = mock_exec
            result = _node_execution(state)
            assert result["execution"] == mock_exec
            assert result["stage"] == "execution"

    def test_decision_with_missing_upstream_data(self):
        state = {"symbol": "AAPL", "security": None, "sentiment": None,
                 "regime": None, "options_chain": None,
                 "strategy": None, "execution": None,
                 "error": "", "stage": "init", "messages": [], "log": []}
        result = _node_decision(state)
        assert result.get("error"), f"Expected error message, got: {result}"

    def test_decision_with_partial_upstream_failure(self, mock_security, mock_regime, mock_option_chain):
        """Decision should still catch missing sentiment even if other fields are present."""
        state = {"symbol": "AAPL", "security": mock_security,
                 "sentiment": None,  # <-- missing
                 "regime": mock_regime, "options_chain": mock_option_chain,
                 "strategy": None, "execution": None,
                 "error": "", "stage": "init", "messages": [], "log": []}
        result = _node_decision(state)
        assert result.get("error"), f"Expected error when sentiment missing, got: {result}"

    def test_execution_no_trade_log_format(self):
        """NO_TRADE execution should produce a truncated rationale log, not a price fill."""
        mock_no_trade = StrategyDecision(
            strategy=OptionStrategy.NO_TRADE, confidence=0.90,
            rationale="Market conditions unfavorable — high VIX and bearish Fear & Greed.",
        )
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="AAPL", strategy=OptionStrategy.NO_TRADE),
            confirmation={"status": "No Trade", "cash": 100000.0},
            reasoning="No trade executed.",
        )
        state = {"symbol": "AAPL", "security": None, "sentiment": None,
                 "regime": None, "options_chain": None,
                 "strategy": mock_no_trade, "execution": None,
                 "error": "", "stage": "init", "messages": [], "log": []}
        with patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as mock:
            mock.return_value.execute.return_value = mock_exec
            result = _node_execution(state)
            assert result["execution"] == mock_exec
            # NO_TRADE log should not contain "Fill: $"
            log_entry = result["log"][0]
            assert "No trade" in log_entry or "No Trade" in log_entry
            assert "Fill: $" not in log_entry

    def test_execution_with_missing_strategy(self):
        state = {"symbol": "AAPL", "security": None, "sentiment": None,
                 "regime": None, "options_chain": None,
                 "strategy": None, "execution": None,
                 "error": "", "stage": "init", "messages": [], "log": []}
        result = _node_execution(state)
        assert result.get("error"), f"Expected error message, got: {result}"


# ════════════════════════════════════════════════════════════════════════
# End-to-End Workflow
# ════════════════════════════════════════════════════════════════════════

class TestWorkflowEndToEnd:
    def test_full_workflow_completes(self, mock_security, mock_sentiment, mock_regime,
                                      mock_option_chain, mock_strategy_call):
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="AAPL", strategy=OptionStrategy.CALL),
            confirmation={"status": "Filled", "order_id": "ORD-TEST-1234",
                          "filled_price": 5.20},
            reasoning="Paper trade filled.",
        )

        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as sec, \
             patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as sent, \
             patch("portfolio.trading.graph.trading_graph.RegimeAgent") as reg, \
             patch("portfolio.trading.graph.trading_graph.DecisionAgent") as dec, \
             patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as exec, \
             patch("portfolio.trading.graph.trading_graph.fetch_option_chain") as fetch:

            sec.return_value.analyze.return_value = mock_security
            sent.return_value.analyze.return_value = mock_sentiment
            reg.return_value.analyze.return_value = mock_regime
            fetch.return_value = mock_option_chain
            dec.return_value.decide.return_value = mock_strategy_call
            exec.return_value.execute.return_value = mock_exec

            result = run_trading_workflow("AAPL", user_approved=True)

        assert result["symbol"] == "AAPL"
        assert result["security"] is not None
        assert result["security"].company_name == "Apple Inc."
        assert result["sentiment"] is not None
        assert result["regime"] is not None
        assert result["regime"].regime == MarketRegime.BULL
        assert result["options_chain"] is not None
        assert result["strategy"] is not None
        assert result["strategy"].strategy == OptionStrategy.CALL
        assert result["execution"] is not None
        assert result["stage"] == "execution"
        assert len(result["log"]) >= 6

    def test_workflow_no_trade_path(self, mock_security, mock_sentiment,
                                     mock_regime, mock_option_chain):
        mock_no_trade = StrategyDecision(
            strategy=OptionStrategy.NO_TRADE, confidence=0.90,
            rationale="Conditions unfavorable.",
        )
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="AAPL", strategy=OptionStrategy.NO_TRADE),
            confirmation={"status": "No Trade", "cash": 100000.0},
            reasoning="No trade executed.",
        )

        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as sec, \
             patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as sent, \
             patch("portfolio.trading.graph.trading_graph.RegimeAgent") as reg, \
             patch("portfolio.trading.graph.trading_graph.DecisionAgent") as dec, \
             patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as exec, \
             patch("portfolio.trading.graph.trading_graph.fetch_option_chain") as fetch:

            sec.return_value.analyze.return_value = mock_security
            sent.return_value.analyze.return_value = mock_sentiment
            reg.return_value.analyze.return_value = mock_regime
            fetch.return_value = mock_option_chain
            dec.return_value.decide.return_value = mock_no_trade
            exec.return_value.execute.return_value = mock_exec

            result = run_trading_workflow("AAPL", user_approved=True)

        assert result["strategy"].strategy == OptionStrategy.NO_TRADE
        assert result["execution"] is not None

    def test_workflow_survives_node_failure(self, mock_sentiment, mock_regime,
                                             mock_option_chain, mock_strategy_call):
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="AAPL", strategy=OptionStrategy.CALL),
            confirmation={"status": "Filled", "order_id": "ORD-ERR"},
            reasoning="Eventual execution.",
        )

        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as sec, \
             patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as sent, \
             patch("portfolio.trading.graph.trading_graph.RegimeAgent") as reg, \
             patch("portfolio.trading.graph.trading_graph.DecisionAgent") as dec, \
             patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as exec, \
             patch("portfolio.trading.graph.trading_graph.fetch_option_chain") as fetch:

            sec.return_value.analyze.side_effect = RuntimeError("API error")
            sent.return_value.analyze.return_value = mock_sentiment
            reg.return_value.analyze.return_value = mock_regime
            fetch.return_value = mock_option_chain
            dec.return_value.decide.return_value = mock_strategy_call
            exec.return_value.execute.return_value = mock_exec

            result = run_trading_workflow("AAPL", user_approved=True)

        assert result is not None
        assert result.get("error")  # security failed, error should be recorded
        # Sentiment & regime still run (nodes are isolated)
        assert result["sentiment"] is not None
        # But decision can't run without security, so execution is skipped
        assert result["execution"] is None  # graceful degradation

    def test_workflow_preserves_all_logs(self, mock_security, mock_sentiment,
                                          mock_regime, mock_option_chain, mock_strategy_call):
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="AAPL", strategy=OptionStrategy.CALL),
            confirmation={"status": "Filled", "order_id": "ORD-LOG"},
            reasoning="Logged.",
        )

        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as sec, \
             patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as sent, \
             patch("portfolio.trading.graph.trading_graph.RegimeAgent") as reg, \
             patch("portfolio.trading.graph.trading_graph.DecisionAgent") as dec, \
             patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as exec, \
             patch("portfolio.trading.graph.trading_graph.fetch_option_chain") as fetch:

            sec.return_value.analyze.return_value = mock_security
            sent.return_value.analyze.return_value = mock_sentiment
            reg.return_value.analyze.return_value = mock_regime
            fetch.return_value = mock_option_chain
            dec.return_value.decide.return_value = mock_strategy_call
            exec.return_value.execute.return_value = mock_exec

            result = run_trading_workflow("MSFT", user_approved=True)

        keywords = ["Security", "Risk/Sentiment", "Regime", "Options Chain",
                     "Decision", "Execution"]
        for keyword in keywords:
            found = any(keyword in entry for entry in result["log"])
            assert found, f"Log entry for '{keyword}' missing"

    def test_full_workflow_put_strategy(self, mock_security, mock_sentiment, mock_regime,
                                         mock_option_chain):
        """E2E with PUT strategy."""
        mock_put = StrategyDecision(
            strategy=OptionStrategy.PUT, confidence=0.75,
            rationale="Bearish regime with elevated IV.",
            recommended_strike=180.0, recommended_expiration="2026-06-15",
            max_risk=470.0, max_reward=float("inf"),
            breakeven="$175.30",
            alternatives=["CALL", "No Trade"],
        )
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="AAPL", strategy=OptionStrategy.PUT),
            confirmation={"status": "Filled", "order_id": "ORD-PUT-9999",
                          "filled_price": 4.60},
            reasoning="Paper put filled.",
        )

        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as sec, \
             patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as sent, \
             patch("portfolio.trading.graph.trading_graph.RegimeAgent") as reg, \
             patch("portfolio.trading.graph.trading_graph.DecisionAgent") as dec, \
             patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as exec, \
             patch("portfolio.trading.graph.trading_graph.fetch_option_chain") as fetch:

            sec.return_value.analyze.return_value = mock_security
            sent.return_value.analyze.return_value = mock_sentiment
            reg.return_value.analyze.return_value = mock_regime
            fetch.return_value = mock_option_chain
            dec.return_value.decide.return_value = mock_put
            exec.return_value.execute.return_value = mock_exec

            result = run_trading_workflow("AAPL", user_approved=True)

        assert result["strategy"].strategy == OptionStrategy.PUT
        assert result["execution"] is not None
        assert result["stage"] == "execution"

    def test_full_workflow_strangle_strategy(self, mock_security, mock_sentiment,
                                              mock_regime, mock_option_chain):
        """E2E with STRANGLE strategy."""
        mock_strangle = StrategyDecision(
            strategy=OptionStrategy.STRANGLE, confidence=0.65,
            rationale="High IV environment — strangle captures vol expansion.",
            recommended_expiration="2026-07-15", max_risk=850.0,
            max_reward=float("inf"),
            breakeven="$160 / $210",
            alternatives=["CALL", "No Trade"],
        )
        mock_exec = ExecutionResult(
            request=OrderRequest(symbol="MSFT", strategy=OptionStrategy.STRANGLE),
            confirmation={"status": "Filled", "order_id": "ORD-STR-7777",
                          "filled_price": 8.50},
            reasoning="Strangle filled — call + put legs.",
        )

        with patch("portfolio.trading.graph.trading_graph.SecurityAgent") as sec, \
             patch("portfolio.trading.graph.trading_graph.RiskSentimentAgent") as sent, \
             patch("portfolio.trading.graph.trading_graph.RegimeAgent") as reg, \
             patch("portfolio.trading.graph.trading_graph.DecisionAgent") as dec, \
             patch("portfolio.trading.graph.trading_graph.ExecutionAgent") as exec, \
             patch("portfolio.trading.graph.trading_graph.fetch_option_chain") as fetch:

            sec.return_value.analyze.return_value = mock_security
            sent.return_value.analyze.return_value = mock_sentiment
            reg.return_value.analyze.return_value = mock_regime
            fetch.return_value = mock_option_chain
            dec.return_value.decide.return_value = mock_strangle
            exec.return_value.execute.return_value = mock_exec

            result = run_trading_workflow("MSFT", user_approved=True)

        assert result["strategy"].strategy == OptionStrategy.STRANGLE
        assert result["execution"] is not None
        assert result["stage"] == "execution"
