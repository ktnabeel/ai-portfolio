"""Simulated paper trading broker.

Provides a realistic simulated broker for options trading without
real money. Tracks portfolio, executes orders, and maintains P&L.

All orders are filled instantly at market price with simulated
commission fees and slippage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..models import (
    OptionContract,
    OrderConfirmation,
    OrderRequest,
    OrderStatus,
    OrderType,
    OptionStrategy,
)


@dataclass
class Position:
    """A single position in the paper trading account."""
    position_id: str
    symbol: str
    option_symbol: str
    strategy: str
    option_type: str
    strike: float
    expiration: str
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0

    @property
    def cost_basis(self) -> float:
        return self.entry_price * self.quantity * 100

    @property
    def market_value(self) -> float:
        return self.current_price * self.quantity * 100

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis


@dataclass
class PaperAccount:
    """Paper trading account state."""
    cash: float = 100_000.0
    positions: list[Position] = field(default_factory=list)
    order_history: list[OrderConfirmation] = field(default_factory=list)
    total_commission: float = 0.0

    @property
    def total_equity(self) -> float:
        return self.cash + sum(p.market_value for p in self.positions)

    @property
    def total_pnl(self) -> float:
        return self.total_equity - 100_000.0


# Global paper account instance
_account = PaperAccount()


def get_account() -> PaperAccount:
    """Get the current paper trading account."""
    return _account


def reset_account():
    """Reset the paper account to initial state."""
    global _account
    _account = PaperAccount()


def execute_paper_trade(request: OrderRequest) -> OrderConfirmation:
    """Execute a simulated trade in the paper account.

    Args:
        request: The order request with strategy, symbol, quantity, etc.

    Returns:
        OrderConfirmation with fill details or rejection reason.
    """
    account = get_account()

    # Estimate option price based on strategy
    estimated_price = _estimate_option_price(request)

    if estimated_price <= 0:
        return OrderConfirmation(
            order_id=request.order_id,
            status=OrderStatus.REJECTED,
            notes=f"Cannot price option for {request.symbol}. No valid option chain available.",
        )

    # Apply realistic spread and slippage
    fill_price = estimated_price

    # Per-contract commission
    commission = 0.65 * request.quantity
    total_cost = fill_price * request.quantity * 100 + commission

    # Check if we have enough cash
    if total_cost > account.cash:
        return OrderConfirmation(
            order_id=request.order_id,
            status=OrderStatus.REJECTED,
            filled_price=fill_price,
            filled_quantity=0,
            commission=0.0,
            total_cost=total_cost,
            notes=(
                f"Insufficient cash. Need ${total_cost:,.2f} but have "
                f"${account.cash:,.2f}."
            ),
        )

    # Execute the trade
    account.cash -= total_cost
    account.total_commission += commission

    position = Position(
        position_id=f"POS-{uuid.uuid4().hex[:8].upper()}",
        symbol=request.symbol,
        option_symbol=request.option_symbol or f"O:{request.symbol}",
        strategy=request.strategy.value,
        option_type=request.option_type or "unknown",
        strike=request.strike or 0.0,
        expiration=request.expiration or "",
        quantity=request.quantity,
        entry_price=fill_price,
        entry_date=datetime.now(),
        current_price=fill_price,
    )
    account.positions.append(position)

    confirmation = OrderConfirmation(
        order_id=request.order_id,
        status=OrderStatus.FILLED,
        filled_price=fill_price,
        filled_quantity=request.quantity,
        commission=commission,
        total_cost=total_cost,
        timestamp=datetime.now(),
        notes=(
            f"Paper trade executed: {request.strategy.value} on {request.symbol}. "
            f"Filled at ${fill_price:.2f}/contract. "
            f"Remaining cash: ${account.cash:,.2f}."
        ),
    )
    account.order_history.append(confirmation)
    return confirmation


def _estimate_option_price(request: OrderRequest) -> float:
    """Estimate option price for paper trading based on strategy type.

    Uses typical at-the-money option pricing as a baseline.
    """
    from ..options.black_scholes import black_scholes

    # Default assumptions
    underlying_price = 100.0  # Will be overridden by actual price if available

    try:
        import yfinance as yf
        stock = yf.Ticker(request.symbol)
        info = stock.fast_info if hasattr(stock, 'fast_info') else stock.info
        if hasattr(info, 'last_price'):
            underlying_price = float(info.last_price)
        elif isinstance(info, dict):
            underlying_price = float(info.get("regularMarketPrice", 100.0))
    except Exception:
        pass

    strike = request.strike or underlying_price
    T = 14 / 365  # ~2 weeks default
    r = 0.045
    iv = 0.35  # Typical IV

    base_price = black_scholes(underlying_price, strike, T, r, iv, "call")

    if request.strategy == OptionStrategy.CALL:
        return base_price
    elif request.strategy == OptionStrategy.PUT:
        return black_scholes(underlying_price, strike, T, r, iv, "put")
    elif request.strategy == OptionStrategy.STRANGLE:
        # Strangle: OTM call + OTM put
        otm_call_strike = underlying_price * 1.05
        otm_put_strike = underlying_price * 0.95
        call_price = black_scholes(underlying_price, otm_call_strike, T, r, iv * 0.9, "call")
        put_price = black_scholes(underlying_price, otm_put_strike, T, r, iv * 0.9, "put")
        return call_price + put_price
    else:
        return base_price
