"""MCP (Model Context Protocol) Trading Server.

Provides a simulated paper trading server using the Model Context Protocol
pattern. The server exposes trading operations as tools that an LLM can call:

Tools:
  - get_account_status: Returns current account balance and positions
  - place_option_order: Places an options order (call/put/strangle)
  - cancel_order: Cancels a pending order
  - get_order_history: Returns recent order history

This follows the MCP pattern where tools are defined with JSON schemas
and the server processes tool calls through a defined protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .broker import execute_paper_trade, get_account, reset_account
from ..models import (
    OrderConfirmation,
    OrderRequest,
    OrderStatus,
    OrderType,
    OptionStrategy,
)


# ════════════════════════════════════════════════════════════════════════
# MCP Tool Definitions (JSON Schema for each tool)
# ════════════════════════════════════════════════════════════════════════

MCP_TOOLS = [
    {
        "name": "get_account_status",
        "description": "Get current paper trading account status: cash balance, total equity, P&L, and open positions.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "place_option_order",
        "description": (
            "Place an options trade in the paper trading account. "
            "Supports: Long Call, Long Put, and Long Strangle strategies."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The underlying stock symbol (e.g., 'AAPL').",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["Call", "Put", "Strangle", "No Trade"],
                    "description": "The options strategy to execute.",
                },
                "strike": {
                    "type": "number",
                    "description": "The strike price for the option (ignored for strangles).",
                },
                "expiration": {
                    "type": "string",
                    "description": "Expiration date in YYYY-MM-DD format.",
                },
                "option_type": {
                    "type": "string",
                    "enum": ["call", "put"],
                    "description": "Option type (call or put). For strangle, this is ignored.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of contracts (default: 1).",
                },
                "limit_price": {
                    "type": "number",
                    "description": "Optional limit price per contract.",
                },
            },
            "required": ["symbol", "strategy"],
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel a pending order by order ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to cancel.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_order_history",
        "description": "Get recent order history from the paper trading account.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of orders to return (default: 10).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "reset_account",
        "description": "Reset the paper trading account to initial state ($100,000 cash, no positions).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


@dataclass
class MCPResponse:
    """Standard MCP response wrapper."""
    success: bool
    data: Any = None
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class MCPTradingServer:
    """Model Context Protocol server for paper trading.

    This server implements the MCP tool-calling protocol, allowing
    LLM agents to discover and call trading tools through
    structured tool definitions.
    """

    def __init__(self):
        self._tools: dict[str, Callable] = {
            "get_account_status": self._handle_account_status,
            "place_option_order": self._handle_place_order,
            "cancel_order": self._handle_cancel_order,
            "get_order_history": self._handle_order_history,
            "reset_account": self._handle_reset_account,
        }

    @property
    def tool_definitions(self) -> list[dict]:
        """Return the list of tool definitions (JSON schemas) for LLM context."""
        return MCP_TOOLS

    def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPResponse:
        """Process an MCP tool call.

        Args:
            name: Tool name.
            arguments: Tool arguments as a dict.

        Returns:
            MCPResponse with success/data or error.
        """
        handler = self._tools.get(name)
        if handler is None:
            return MCPResponse(
                success=False,
                error=f"Unknown tool: '{name}'. Available tools: {list(self._tools.keys())}",
            )
        try:
            result = handler(arguments)
            return MCPResponse(success=True, data=result)
        except Exception as e:
            return MCPResponse(success=False, error=str(e))

    # ── Tool Handlers ──────────────────────────────────────────────────

    def _handle_account_status(self, _args: dict) -> dict:
        account = get_account()
        return {
            "cash": round(account.cash, 2),
            "total_equity": round(account.total_equity, 2),
            "total_pnl": round(account.total_pnl, 2),
            "total_commission": round(account.total_commission, 2),
            "positions": [
                {
                    "position_id": p.position_id,
                    "symbol": p.symbol,
                    "strategy": p.strategy,
                    "option_type": p.option_type,
                    "strike": p.strike,
                    "expiration": p.expiration,
                    "quantity": p.quantity,
                    "entry_price": p.entry_price,
                    "market_value": round(p.market_value, 2),
                    "unrealized_pnl": round(p.unrealized_pnl, 2),
                }
                for p in account.positions
            ],
            "position_count": len(account.positions),
        }

    def _handle_place_order(self, args: dict) -> dict:
        strategy_str = args.get("strategy", "No Trade")
        strategy_map = {
            "Call": OptionStrategy.CALL,
            "Put": OptionStrategy.PUT,
            "Strangle": OptionStrategy.STRANGLE,
            "No Trade": OptionStrategy.NO_TRADE,
        }
        strategy = strategy_map.get(strategy_str, OptionStrategy.NO_TRADE)

        if strategy == OptionStrategy.NO_TRADE:
            return {
                "status": "No Trade",
                "notes": "No trade strategy selected. Order not placed.",
            }

        request = OrderRequest(
            symbol=args.get("symbol", "").upper(),
            strategy=strategy,
            strike=args.get("strike"),
            expiration=args.get("expiration"),
            option_type=args.get("option_type", "call"),
            quantity=args.get("quantity", 1),
            limit_price=args.get("limit_price"),
        )

        confirmation = execute_paper_trade(request)

        return {
            "order_id": confirmation.order_id,
            "status": confirmation.status.value,
            "filled_price": confirmation.filled_price,
            "filled_quantity": confirmation.filled_quantity,
            "commission": confirmation.commission,
            "total_cost": confirmation.total_cost,
            "timestamp": confirmation.timestamp.isoformat(),
            "notes": confirmation.notes,
        }

    def _handle_cancel_order(self, args: dict) -> dict:
        order_id = args.get("order_id", "")
        return {
            "order_id": order_id,
            "status": "Rejected",
            "notes": "Paper trading orders are filled instantly and cannot be cancelled.",
        }

    def _handle_order_history(self, args: dict) -> dict:
        limit = args.get("limit", 10)
        account = get_account()
        history = account.order_history[-limit:]
        return {
            "orders": [
                {
                    "order_id": o.order_id,
                    "status": o.status.value,
                    "filled_price": o.filled_price,
                    "filled_quantity": o.filled_quantity,
                    "commission": o.commission,
                    "total_cost": o.total_cost,
                    "timestamp": o.timestamp.isoformat(),
                    "notes": o.notes[:200],
                }
                for o in reversed(history)
            ],
            "total_orders": len(account.order_history),
        }

    def _handle_reset_account(self, _args: dict) -> dict:
        reset_account()
        return {
            "status": "Reset",
            "notes": "Paper trading account reset to $100,000 cash, no positions.",
        }
