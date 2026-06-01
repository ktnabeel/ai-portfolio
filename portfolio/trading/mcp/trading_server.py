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

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import yfinance as yf

from .broker import close_position, execute_paper_trade, get_account, reset_account
from ..options.polygon_client import fetch_option_chain_with_metadata
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
        "name": "get_market_quote",
        "description": "Read-only market quote lookup for a symbol with source and freshness metadata.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The stock or ETF ticker symbol (e.g., 'AAPL' or 'SPY').",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_market_regime_data",
        "description": "Read-only OHLC market data used by the Regime Detection agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The market proxy ticker symbol. Defaults to SPY.",
                },
                "period": {
                    "type": "string",
                    "description": "Yahoo Finance history period. Defaults to 6mo.",
                },
                "interval": {
                    "type": "string",
                    "description": "Yahoo Finance history interval. Defaults to 1d.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_option_chain",
        "description": "Read-only options chain lookup for a symbol and optional expiration.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The underlying stock symbol (e.g., 'AAPL').",
                },
                "expiration": {
                    "type": "string",
                    "description": "Optional expiration date in YYYY-MM-DD format.",
                },
            },
            "required": ["symbol"],
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
    {
        "name": "close_position",
        "description": "Close an open position and realise its P&L. Returns the trade record.",
        "parameters": {
            "type": "object",
            "properties": {
                "position_id": {
                    "type": "string",
                    "description": "The position ID to close (e.g., 'POS-ABCD1234').",
                },
                "exit_price": {
                    "type": "number",
                    "description": "Optional exit price per contract (uses current price if omitted).",
                },
            },
            "required": ["position_id"],
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
            "get_market_quote": self._handle_market_quote,
            "get_market_regime_data": self._handle_market_regime_data,
            "get_option_chain": self._handle_option_chain,
            "place_option_order": self._handle_place_order,
            "cancel_order": self._handle_cancel_order,
            "get_order_history": self._handle_order_history,
            "reset_account": self._handle_reset_account,
            "close_position": self._handle_close_position,
        }
        self.call_log: list[dict[str, Any]] = []

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
            self.call_log.append({
                "tool": name, "status": "failed",
                "detail": f"Unknown tool. Available: {list(self._tools.keys())}",
            })
            return MCPResponse(
                success=False,
                error=f"Unknown tool: '{name}'. Available tools: {list(self._tools.keys())}",
            )
        try:
            result = handler(arguments)
            detail = self._summarise_call(name, arguments, result)
            self.call_log.append({"tool": name, "status": "success", "detail": detail})
            return MCPResponse(success=True, data=result)
        except Exception as e:
            self.call_log.append({"tool": name, "status": "failed", "detail": str(e)})
            return MCPResponse(success=False, error=str(e))

    def _summarise_call(self, name: str, args: dict[str, Any], result: Any) -> str:
        """Build a human-readable one-line summary of the tool call."""
        if name == "get_account_status":
            pos = result.get("position_count", 0) if isinstance(result, dict) else "?"
            return f"Account: {pos} position(s)"
        if name == "get_market_quote":
            symbol = result.get("symbol", args.get("symbol", "?")) if isinstance(result, dict) else args.get("symbol", "?")
            price = result.get("price", "?") if isinstance(result, dict) else "?"
            source = result.get("source", "?") if isinstance(result, dict) else "?"
            return f"{symbol} quote: {price} via {source}"
        if name == "get_market_regime_data":
            symbol = result.get("symbol", args.get("symbol", "SPY")) if isinstance(result, dict) else args.get("symbol", "SPY")
            rows = len(result.get("history", [])) if isinstance(result, dict) else "?"
            return f"{symbol} regime data: {rows} bar(s)"
        if name == "get_option_chain":
            symbol = result.get("symbol", args.get("symbol", "?")) if isinstance(result, dict) else args.get("symbol", "?")
            calls = len(result.get("calls", [])) if isinstance(result, dict) else "?"
            puts = len(result.get("puts", [])) if isinstance(result, dict) else "?"
            source = result.get("source", "?") if isinstance(result, dict) else "?"
            return f"{symbol} chain: {calls} calls/{puts} puts via {source}"
        if name == "place_option_order":
            status = result.get("status", "?") if isinstance(result, dict) else "?"
            symbol = args.get("symbol", "?")
            strategy = args.get("strategy", "?")
            return f"{strategy} on {symbol} → {status}"
        if name == "close_position":
            ok = result.get("success", False) if isinstance(result, dict) else False
            pid = args.get("position_id", "?")
            return f"Close {pid}: {'OK' if ok else 'Failed'}"
        if name == "reset_account":
            return "Account reset to initial state"
        return "OK"

    @property
    def last_calls(self) -> list[dict[str, Any]]:
        """Return call log entries since last drain."""
        calls = list(self.call_log)
        self.call_log.clear()
        return calls

    # ── Tool Handlers ──────────────────────────────────────────────────

    @staticmethod
    def _now_freshness() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if math.isnan(number) or math.isinf(number):
            return default
        return number

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if math.isnan(number) or math.isinf(number):
            return default
        return int(number)

    @classmethod
    def _quote_from_fast_info(cls, info: Any) -> dict[str, Any]:
        if info is None:
            return {}
        if isinstance(info, dict):
            return dict(info)
        fields = [
            "last_price",
            "regular_market_price",
            "previous_close",
            "open",
            "day_high",
            "day_low",
            "last_volume",
            "currency",
        ]
        return {field: getattr(info, field) for field in fields if hasattr(info, field)}

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

    def _handle_market_quote(self, args: dict) -> dict:
        symbol = (args.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("symbol is required")

        stock = yf.Ticker(symbol)
        fast_info = self._quote_from_fast_info(getattr(stock, "fast_info", None))
        info = getattr(stock, "info", {}) if not fast_info else {}
        if not isinstance(info, dict):
            info = {}

        price = self._safe_float(
            fast_info.get("last_price")
            or fast_info.get("regular_market_price")
            or info.get("regularMarketPrice")
            or info.get("currentPrice")
        )
        previous_close = self._safe_float(
            fast_info.get("previous_close") or info.get("previousClose")
        )
        open_price = self._safe_float(fast_info.get("open") or info.get("open"))
        high = self._safe_float(fast_info.get("day_high") or info.get("dayHigh"))
        low = self._safe_float(fast_info.get("day_low") or info.get("dayLow"))
        volume = self._safe_int(fast_info.get("last_volume") or info.get("volume"))

        if price <= 0:
            hist = stock.history(period="1d")
            if hist is not None and not hist.empty:
                last = hist.iloc[-1]
                price = self._safe_float(last.get("Close"))
                open_price = open_price or self._safe_float(last.get("Open"))
                high = high or self._safe_float(last.get("High"))
                low = low or self._safe_float(last.get("Low"))
                volume = volume or self._safe_int(last.get("Volume"))

        if price <= 0:
            raise RuntimeError(f"No quote data available for {symbol}")

        return {
            "symbol": symbol,
            "price": price,
            "previous_close": previous_close,
            "open": open_price,
            "high": high,
            "low": low,
            "volume": volume,
            "currency": fast_info.get("currency") or info.get("currency", "USD"),
            "source": "yfinance",
            "freshness": self._now_freshness(),
            "is_realtime": False,
            "warning": "Yahoo Finance quotes may be delayed.",
        }

    def _handle_market_regime_data(self, args: dict) -> dict:
        symbol = (args.get("symbol") or "SPY").strip().upper()
        period = args.get("period") or "6mo"
        interval = args.get("interval") or "1d"
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period, interval=interval)
        if hist is None or hist.empty:
            raise RuntimeError(f"No market history available for {symbol}")

        history: list[dict[str, Any]] = []
        for index, row in hist.iterrows():
            close = self._safe_float(row.get("Close"))
            if close <= 0:
                continue
            if hasattr(index, "isoformat"):
                row_date = index.isoformat()
            else:
                row_date = str(index)
            history.append({
                "date": row_date,
                "open": self._safe_float(row.get("Open")),
                "high": self._safe_float(row.get("High")),
                "low": self._safe_float(row.get("Low")),
                "close": close,
                "volume": self._safe_int(row.get("Volume")),
            })

        if len(history) < 2:
            raise RuntimeError(f"Insufficient market history available for {symbol}")

        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "history": history,
            "source": "yfinance",
            "freshness": history[-1]["date"],
            "is_realtime": False,
            "warning": "Yahoo Finance OHLC data may be delayed.",
        }

    def _handle_option_chain(self, args: dict) -> dict:
        symbol = (args.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        expiration = args.get("expiration") or None
        chain, metadata = fetch_option_chain_with_metadata(symbol, expiration)
        data = chain.model_dump()
        data.update(metadata)
        return data

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

    def _handle_close_position(self, args: dict) -> dict:
        position_id = args.get("position_id", "")
        exit_price = args.get("exit_price")
        return close_position(position_id, exit_price)
