"""Unit tests for the simulated paper trading broker."""

from __future__ import annotations

import sys
import types

import pytest

# ════════════════════════════════════════════════════════════════════════
# Mock yfinance at sys.modules level to avoid pyarrow crash on Windows.
# broker.py does a lazy `import yfinance as yf` inside _estimate_option_price
# which crashes pyarrow/pandas on Windows. This mock must be inserted BEFORE
# the broker module is imported (which happens on the next line).
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

from portfolio.trading.mcp.broker import (
    execute_paper_trade,
    get_account,
    reset_account,
)
from portfolio.trading.models import (
    OrderRequest,
    OrderStatus,
    OptionStrategy,
)


@pytest.fixture(autouse=True)
def reset():
    reset_account()


class TestAccountInitialization:
    def test_initial_cash(self):
        assert get_account().cash == 100_000.0

    def test_initial_positions_empty(self):
        assert get_account().positions == []

    def test_initial_history_empty(self):
        assert get_account().order_history == []

    def test_initial_equity_equals_cash(self):
        acc = get_account()
        assert acc.total_equity == acc.cash

    def test_initial_pnl_zero(self):
        assert get_account().total_pnl == 0.0

    def test_reset_restores_cash(self):
        get_account().cash = 50000.0
        reset_account()
        assert get_account().cash == 100_000.0


class TestOrderExecution:
    def test_execute_call_order_returns_filled(self):
        request = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        )
        confirmation = execute_paper_trade(request)
        assert confirmation.status == OrderStatus.FILLED
        assert confirmation.filled_quantity == 1

    def test_execute_put_order_returns_filled(self):
        request = OrderRequest(
            symbol="MSFT", strategy=OptionStrategy.PUT,
            strike=300, option_type="put", quantity=1,
        )
        confirmation = execute_paper_trade(request)
        assert confirmation.status == OrderStatus.FILLED

    def test_execute_strangle_returns_filled(self):
        request = OrderRequest(
            symbol="NVDA", strategy=OptionStrategy.STRANGLE, quantity=1,
        )
        confirmation = execute_paper_trade(request)
        assert confirmation.status == OrderStatus.FILLED

    def test_filled_price_is_positive(self):
        request = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        )
        confirmation = execute_paper_trade(request)
        assert confirmation.filled_price is not None
        assert confirmation.filled_price > 0

    def test_commission_is_charged(self):
        request = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=5,
        )
        confirmation = execute_paper_trade(request)
        assert confirmation.commission == 0.65 * 5

    def test_confirmation_has_notes(self):
        request = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        )
        confirmation = execute_paper_trade(request)
        assert "Paper trade executed" in confirmation.notes
        assert "AAPL" in confirmation.notes


class TestCashAccounting:
    def test_cash_reduces_after_trade(self):
        before = get_account().cash
        request = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        )
        confirmation = execute_paper_trade(request)
        after = get_account().cash
        assert after < before
        assert after == pytest.approx(before - (confirmation.total_cost or 0))

    def test_multiple_trades_accumulate(self):
        request1 = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        )
        request2 = OrderRequest(
            symbol="MSFT", strategy=OptionStrategy.PUT,
            strike=300, option_type="put", quantity=1,
        )
        confirm1 = execute_paper_trade(request1)
        confirm2 = execute_paper_trade(request2)
        acc = get_account()
        expected = 100_000.0 - (confirm1.total_cost or 0) - (confirm2.total_cost or 0)
        assert acc.cash == pytest.approx(expected)

    def test_commission_accumulates(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=2,
        ))
        execute_paper_trade(OrderRequest(
            symbol="MSFT", strategy=OptionStrategy.PUT,
            strike=300, option_type="put", quantity=3,
        ))
        expected = 0.65 * 2 + 0.65 * 3
        assert get_account().total_commission == pytest.approx(expected)


class TestPositionTracking:
    def test_position_created_after_trade(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        ))
        assert len(get_account().positions) == 1

    def test_position_has_correct_symbol(self):
        execute_paper_trade(OrderRequest(
            symbol="MSFT", strategy=OptionStrategy.CALL,
            strike=300, option_type="call", quantity=1,
        ))
        assert get_account().positions[0].symbol == "MSFT"

    def test_position_has_correct_quantity(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=3,
        ))
        assert get_account().positions[0].quantity == 3

    def test_multiple_positions(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        ))
        execute_paper_trade(OrderRequest(
            symbol="MSFT", strategy=OptionStrategy.PUT,
            strike=300, option_type="put", quantity=1,
        ))
        assert len(get_account().positions) == 2

    def test_position_has_unique_id(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        ))
        execute_paper_trade(OrderRequest(
            symbol="MSFT", strategy=OptionStrategy.PUT,
            strike=300, option_type="put", quantity=1,
        ))
        ids = [p.position_id for p in get_account().positions]
        assert ids[0] != ids[1]

    def test_market_value_calculation(self):
        request = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=2,
        )
        confirmation = execute_paper_trade(request)
        pos = get_account().positions[0]
        expected_mv = confirmation.filled_price * 2 * 100
        assert pos.market_value == pytest.approx(expected_mv)


class TestOrderRejection:
    def test_insufficient_cash_rejected(self):
        get_account().cash = 10.0
        request = OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=100,
        )
        confirmation = execute_paper_trade(request)
        assert confirmation.status == OrderStatus.REJECTED
        assert "Insufficient cash" in confirmation.notes

    def test_rejected_order_does_not_change_cash(self):
        get_account().cash = 10.0
        before = get_account().cash
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=100,
        ))
        assert get_account().cash == before

    def test_rejected_order_no_position(self):
        get_account().cash = 10.0
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=100,
        ))
        assert len(get_account().positions) == 0

    def test_rejected_order_no_commission(self):
        get_account().cash = 10.0
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=100,
        ))
        assert get_account().total_commission == 0.0


class TestPnL:
    def test_pnl_negative_after_commission(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        ))
        assert get_account().total_pnl < 0

    def test_equity_reduced_by_commission(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        ))
        assert get_account().total_equity < 100_000.0


class TestOrderHistory:
    def test_history_empty_initially(self):
        assert len(get_account().order_history) == 0

    def test_history_after_trade(self):
        execute_paper_trade(OrderRequest(
            symbol="AAPL", strategy=OptionStrategy.CALL,
            strike=150, option_type="call", quantity=1,
        ))
        assert len(get_account().order_history) == 1

    def test_history_after_multiple_trades(self):
        for _ in range(3):
            execute_paper_trade(OrderRequest(
                symbol="AAPL", strategy=OptionStrategy.CALL,
                strike=150, option_type="call", quantity=1,
            ))
        assert len(get_account().order_history) == 3


class TestStrangleExecution:
    def test_strangle_creates_single_position(self):
        execute_paper_trade(OrderRequest(
            symbol="NVDA", strategy=OptionStrategy.STRANGLE, quantity=1,
        ))
        assert len(get_account().positions) == 1
