"""Execution Agent — MCP-based trade execution.

Responsibility:
  1. Receive the StrategyDecision from the Decision Agent
  2. Connect to the MCP trading server
  3. Format and submit the order
  4. Confirm execution and report results
  5. Handle errors, rejections, and no-trade decisions gracefully

Uses:
  - MCPTradingServer for paper trading execution
  - Order confirmation and P&L estimation
"""

from __future__ import annotations

from ..mcp.trading_server import MCPTradingServer
from ..models import (
    ExecutionResult,
    OptionStrategy,
    OrderRequest,
    OrderType,
    StrategyDecision,
)


class ExecutionAgent:
    """Agent #5: MCP-Based Trade Execution."""

    NAME = "Execution"

    def __init__(self):
        self.mcp = MCPTradingServer()

    def execute(self, decision: StrategyDecision, symbol: str) -> ExecutionResult:
        """Execute the strategy decision via MCP paper trading.

        Args:
            decision: The StrategyDecision from the Decision Agent.
            symbol: Stock ticker symbol.

        Returns:
            ExecutionResult with order confirmation and P&L estimate.
        """
        if decision.strategy == OptionStrategy.NO_TRADE:
            return ExecutionResult(
                request=OrderRequest(
                    symbol=symbol,
                    strategy=OptionStrategy.NO_TRADE,
                ),
                confirmation=self.mcp.call_tool("get_account_status", {}).data or {},
                reasoning=(
                    f"No trade executed. Strategy decision was '{decision.strategy.value}' "
                    f"with {decision.confidence:.0%} confidence. "
                    f"Rationale: {decision.rationale[:200]}"
                ),
            )

        # Build the order arguments for MCP
        order_args = {
            "symbol": symbol.upper(),
            "strategy": decision.strategy.value.replace("Long ", ""),
            "quantity": 1,
        }

        if decision.recommended_strike:
            order_args["strike"] = decision.recommended_strike
        if decision.recommended_expiration:
            order_args["expiration"] = decision.recommended_expiration

        if decision.strategy == OptionStrategy.CALL:
            order_args["option_type"] = "call"
        elif decision.strategy == OptionStrategy.PUT:
            order_args["option_type"] = "put"
        # Strangle: MCP handles both legs

        # Submit order through MCP
        mcp_response = self.mcp.call_tool("place_option_order", order_args)

        # Build the order request for the result
        request = OrderRequest(
            symbol=symbol.upper(),
            strategy=decision.strategy,
            option_symbol=(
                decision.call_contract.symbol if decision.call_contract
                else decision.put_contract.symbol if decision.put_contract
                else None
            ),
            strike=decision.recommended_strike,
            expiration=decision.recommended_expiration,
            option_type=(
                "call" if decision.strategy == OptionStrategy.CALL
                else "put" if decision.strategy == OptionStrategy.PUT
                else None
            ),
            quantity=1,
        )

        if mcp_response.success:
            data = mcp_response.data or {}
            confirmation_data = {
                "order_id": data.get("order_id", request.order_id),
                "status": data.get("status", "Filled"),
                "filled_price": data.get("filled_price"),
                "filled_quantity": data.get("filled_quantity", 1),
                "commission": data.get("commission", 0.0),
                "total_cost": data.get("total_cost"),
                "notes": data.get("notes", ""),
            }

            # Get account status for P&L context
            account = self.mcp.call_tool("get_account_status", {})
            account_data = account.data if account.success else {}

            reasoning = (
                f"Order {confirmation_data['order_id']} executed successfully. "
                f"Strategy: {decision.strategy.value} on {symbol}. "
                f"Filled at ${confirmation_data.get('filled_price', 'N/A')}/contract. "
                f"Total cost: ${confirmation_data.get('total_cost', 'N/A')}. "
                f"Remaining cash: ${account_data.get('cash', 'N/A')}. "
                f"Rationale: {decision.rationale[:200]}"
            )

            return ExecutionResult(
                request=request,
                confirmation=confirmation_data,
                pnl_estimate=account_data.get("total_pnl"),
                reasoning=reasoning,
            )
        else:
            # MCP call failed
            return ExecutionResult(
                request=request,
                confirmation={
                    "order_id": request.order_id,
                    "status": "Rejected",
                    "notes": f"MCP execution failed: {mcp_response.error}",
                },
                reasoning=(
                    f"Order submission failed. MCP error: {mcp_response.error}. "
                    f"Strategy was {decision.strategy.value} on {symbol}."
                ),
            )
