"""Unit tests for the MCP Trading Server."""

from __future__ import annotations

import sys
import types

import pytest

# ════════════════════════════════════════════════════════════════════════
# Mock yfinance at sys.modules level to avoid pyarrow crash on Windows.
# broker.py does a lazy `import yfinance as yf` inside _estimate_option_price
# which crashes pyarrow/pandas on Windows. Inserting the mock before
# MCPTradingServer is imported lets the real broker logic run normally.
# ════════════════════════════════════════════════════════════════════════

class _MockFastInfo:
    last_price = 185.50


class _MockTicker:
    fast_info = _MockFastInfo()
    info = {"regularMarketPrice": 185.50}

    def __init__(self, symbol):
        self.symbol = symbol


_mock_yfinance = types.ModuleType("yfinance")
_mock_yfinance.Ticker = _MockTicker
sys.modules["yfinance"] = _mock_yfinance

from portfolio.trading.mcp.trading_server import (
    MCPTradingServer,
    MCP_TOOLS,
)


@pytest.fixture
def server():
    s = MCPTradingServer()
    s.call_tool("reset_account", {})
    return s


class TestToolDefinitions:
    def test_all_six_tools_defined(self):
        tool_names = {t["name"] for t in MCP_TOOLS}
        expected = {"get_account_status", "place_option_order", "cancel_order",
                     "get_order_history", "reset_account", "close_position"}
        assert tool_names == expected

    def test_each_tool_has_parameters_schema(self):
        for tool in MCP_TOOLS:
            assert "parameters" in tool
            assert "type" in tool["parameters"]
            assert tool["parameters"]["type"] == "object"

    def test_place_order_has_required_fields(self):
        place_tool = [t for t in MCP_TOOLS if t["name"] == "place_option_order"][0]
        assert "symbol" in place_tool["parameters"]["required"]
        assert "strategy" in place_tool["parameters"]["required"]

    def test_server_exposes_tool_definitions(self):
        s = MCPTradingServer()
        assert len(s.tool_definitions) == 6


class TestAccountStatus:
    def test_returns_success(self, server):
        r = server.call_tool("get_account_status", {})
        assert r.success

    def test_initial_cash_is_100k(self, server):
        r = server.call_tool("get_account_status", {})
        assert r.data["cash"] == 100_000.0

    def test_initial_positions_empty(self, server):
        r = server.call_tool("get_account_status", {})
        assert r.data["positions"] == []
        assert r.data["position_count"] == 0

    def test_initial_equity_equals_cash(self, server):
        r = server.call_tool("get_account_status", {})
        assert r.data["total_equity"] == r.data["cash"]

    def test_initial_pnl_zero(self, server):
        r = server.call_tool("get_account_status", {})
        assert r.data["total_pnl"] == 0.0


class TestPlaceOrder:
    def test_place_call_order_succeeds(self, server):
        r = server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "Call", "strike": 150,
            "option_type": "call", "quantity": 1,
        })
        assert r.success
        assert r.data["status"] == "Filled"

    def test_place_put_order_succeeds(self, server):
        r = server.call_tool("place_option_order", {
            "symbol": "MSFT", "strategy": "Put", "strike": 300,
            "option_type": "put", "quantity": 1,
        })
        assert r.success
        assert r.data["status"] == "Filled"

    def test_place_strangle_order_succeeds(self, server):
        r = server.call_tool("place_option_order", {
            "symbol": "NVDA", "strategy": "Strangle", "quantity": 1,
        })
        assert r.success
        assert r.data["status"] == "Filled"

    def test_no_trade_does_not_create_order(self, server):
        r = server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "No Trade",
        })
        assert r.success
        assert r.data["status"] == "No Trade"

    def test_order_reduces_cash(self, server):
        before = server.call_tool("get_account_status", {})
        server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "Call", "strike": 150,
            "option_type": "call", "quantity": 1,
        })
        after = server.call_tool("get_account_status", {})
        assert after.data["cash"] < before.data["cash"]

    def test_order_creates_position(self, server):
        server.call_tool("place_option_order", {
            "symbol": "MSFT", "strategy": "Put", "strike": 300,
            "option_type": "put", "quantity": 2,
        })
        status = server.call_tool("get_account_status", {})
        assert status.data["position_count"] == 1
        pos = status.data["positions"][0]
        assert pos["symbol"] == "MSFT"
        assert pos["quantity"] == 2

    def test_multiple_orders_create_multiple_positions(self, server):
        server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "Call", "strike": 150,
            "option_type": "call", "quantity": 1,
        })
        server.call_tool("place_option_order", {
            "symbol": "MSFT", "strategy": "Put", "strike": 300,
            "option_type": "put", "quantity": 1,
        })
        status = server.call_tool("get_account_status", {})
        assert status.data["position_count"] == 2

    def test_order_charges_commission(self, server):
        server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "Call", "strike": 150,
            "option_type": "call", "quantity": 3,
        })
        status = server.call_tool("get_account_status", {})
        assert status.data["total_commission"] > 0


class TestCancelOrder:
    def test_cancel_returns_rejected(self, server):
        r = server.call_tool("cancel_order", {"order_id": "ORD-12345678"})
        assert r.success
        assert r.data["status"] == "Rejected"
        assert "cannot be cancelled" in r.data["notes"].lower()


class TestOrderHistory:
    def test_empty_history_initially(self, server):
        r = server.call_tool("get_order_history", {})
        assert r.success
        assert r.data["orders"] == []
        assert r.data["total_orders"] == 0

    def test_history_after_trades(self, server):
        server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "Call", "strike": 150,
            "option_type": "call", "quantity": 1,
        })
        server.call_tool("place_option_order", {
            "symbol": "MSFT", "strategy": "Put", "strike": 300,
            "option_type": "put", "quantity": 1,
        })
        r = server.call_tool("get_order_history", {})
        assert r.data["total_orders"] == 2

    def test_history_respects_limit(self, server):
        for _ in range(5):
            server.call_tool("place_option_order", {
                "symbol": "AAPL", "strategy": "Call", "strike": 150,
                "option_type": "call", "quantity": 1,
            })
        r = server.call_tool("get_order_history", {"limit": 3})
        assert len(r.data["orders"]) == 3
        assert r.data["total_orders"] == 5

    def test_history_order_has_required_fields(self, server):
        server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "Call", "strike": 150,
            "option_type": "call", "quantity": 1,
        })
        r = server.call_tool("get_order_history", {})
        order = r.data["orders"][0]
        for field in ["order_id", "status", "filled_price", "filled_quantity",
                       "commission", "total_cost", "timestamp", "notes"]:
            assert field in order, f"Missing field: {field}"


class TestResetAccount:
    def test_reset_restores_state(self, server):
        server.call_tool("place_option_order", {
            "symbol": "AAPL", "strategy": "Call", "strike": 150,
            "option_type": "call", "quantity": 2,
        })
        r = server.call_tool("reset_account", {})
        assert r.success
        status = server.call_tool("get_account_status", {})
        assert status.data["cash"] == 100_000.0
        assert status.data["positions"] == []
        history = server.call_tool("get_order_history", {})
        assert history.data["total_orders"] == 0


class TestErrorHandling:
    def test_unknown_tool_returns_error(self, server):
        r = server.call_tool("nonexistent_tool", {})
        assert not r.success
        assert "Unknown tool" in r.error

    def test_empty_args_does_not_crash(self, server):
        for tool_name in ["get_account_status", "reset_account"]:
            r = server.call_tool(tool_name, {})
            assert r.success

    def test_missing_strategy_defaults_to_no_trade(self, server):
        r = server.call_tool("place_option_order", {"symbol": "AAPL"})
        assert r.success
        assert r.data["status"] == "No Trade"

    def test_response_has_timestamp(self, server):
        r = server.call_tool("get_account_status", {})
        assert r.timestamp is not None
