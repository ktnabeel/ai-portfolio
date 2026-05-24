"""Polygon.io options chain client.

Fetches real options data from Polygon.io API for US equity options.
Provides option chain construction with Greeks computed via Black-Scholes.

API: https://polygon.io/docs/options
Requires: POLYGON_API_KEY environment variable.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
import yfinance as yf

from .black_scholes import black_scholes, calculate_greeks
from ..models import OptionChain, OptionContract


POLYGON_BASE_URL = "https://api.polygon.io"
RISK_FREE_RATE = 0.045  # ~4.5% current risk-free rate


def _get_api_key() -> Optional[str]:
    """Get Polygon API key from environment."""
    return os.environ.get("POLYGON_API_KEY")


def _make_synthetic_chain(
    symbol: str,
    underlying_price: float,
    num_strikes: int = 7,
) -> OptionChain:
    """Generate a realistic synthetic option chain using Black-Scholes.

    Used when Polygon API is unavailable or the API key is not set.

    Args:
        symbol: Stock ticker.
        underlying_price: Current stock price.
        num_strikes: Number of strikes to generate on each side.

    Returns:
        OptionChain with synthetic call and put contracts.
    """
    # Generate strikes around the current price
    strike_step = max(2.5, underlying_price * 0.03)
    strikes = [
        round(underlying_price + (i - num_strikes // 2) * strike_step, 2)
        for i in range(num_strikes)
    ]

    # Expiration dates: ~7, 14, 30, 60 days out
    today = datetime.now()
    expirations = [
        (today + timedelta(days=d)).strftime("%Y-%m-%d")
        for d in [7, 14, 30, 60]
    ]
    nearest_exp = expirations[0]

    # ATM IV typically 20-40% for most stocks
    base_iv = 0.30

    calls: list[OptionContract] = []
    puts: list[OptionContract] = []

    for strike in strikes:
        moneyness = strike / underlying_price
        # Volatility smile: higher IV for OTM options
        iv_adjustment = abs(moneyness - 1.0) * 0.5
        iv = base_iv + iv_adjustment

        T = 7 / 365  # ~7 days for nearest expiration

        call_price = black_scholes(underlying_price, strike, T, RISK_FREE_RATE, iv, "call")
        put_price = black_scholes(underlying_price, strike, T, RISK_FREE_RATE, iv, "put")

        call_greeks = calculate_greeks(underlying_price, strike, T, RISK_FREE_RATE, iv, "call")
        put_greeks = calculate_greeks(underlying_price, strike, T, RISK_FREE_RATE, iv, "put")

        # Simulate realistic bid/ask spread
        spread = max(0.05, call_price * 0.15)

        call_symbol = f"O:{symbol}{nearest_exp.replace('-','')}C{int(strike*1000):08d}"
        put_symbol = f"O:{symbol}{nearest_exp.replace('-','')}P{int(strike*1000):08d}"

        calls.append(OptionContract(
            symbol=call_symbol,
            strike=strike,
            expiration=nearest_exp,
            option_type="call",
            bid=round(max(0.01, call_price - spread / 2), 2),
            ask=round(call_price + spread / 2, 2),
            last=round(call_price, 2),
            volume=max(1, int(abs(1.0 - moneyness) * 500)),
            open_interest=max(10, int(abs(1.0 - moneyness) * 2000)),
            implied_volatility=round(iv, 4),
            delta=call_greeks["delta"],
            gamma=call_greeks["gamma"],
            theta=call_greeks["theta"],
            vega=call_greeks["vega"],
        ))

        puts.append(OptionContract(
            symbol=put_symbol,
            strike=strike,
            expiration=nearest_exp,
            option_type="put",
            bid=round(max(0.01, put_price - spread / 2), 2),
            ask=round(put_price + spread / 2, 2),
            last=round(put_price, 2),
            volume=max(1, int(abs(1.0 - moneyness) * 400)),
            open_interest=max(10, int(abs(1.0 - moneyness) * 1800)),
            implied_volatility=round(iv, 4),
            delta=put_greeks["delta"],
            gamma=put_greeks["gamma"],
            theta=put_greeks["theta"],
            vega=put_greeks["vega"],
        ))

    return OptionChain(
        symbol=symbol,
        underlying_price=underlying_price,
        expiration_dates=expirations,
        calls=calls,
        puts=puts,
    )


def fetch_option_chain(
    symbol: str,
    expiration: Optional[str] = None,
) -> OptionChain:
    """Fetch the options chain for a symbol.

    Tries Polygon.io first if API key is available.
    Falls back to a synthetic chain generated via Black-Scholes.

    Args:
        symbol: Stock ticker symbol.
        expiration: Specific expiration date (YYYY-MM-DD). If None, uses nearest.

    Returns:
        OptionChain with calls and puts.
    """
    # First, get the current underlying price
    try:
        stock = yf.Ticker(symbol)
        info = stock.fast_info if hasattr(stock, 'fast_info') else stock.info
        if hasattr(info, 'last_price'):
            underlying_price = float(info.last_price)
        elif isinstance(info, dict):
            underlying_price = float(info.get("regularMarketPrice", info.get("currentPrice", 0)))
        else:
            underlying_price = 0.0

        if underlying_price <= 0:
            hist = stock.history(period="1d")
            if not hist.empty:
                underlying_price = float(hist["Close"].iloc[-1])
    except Exception:
        underlying_price = 100.0  # Fallback

    api_key = _get_api_key()

    if not api_key:
        # No API key — use synthetic chain
        return _make_synthetic_chain(symbol, underlying_price)

    # Try Polygon.io
    try:
        with httpx.Client(timeout=15.0) as client:
            # Get option contracts
            contracts_url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts"
            params = {
                "underlying_ticker": symbol,
                "expired": "false",
                "limit": 50,
                "apiKey": api_key,
            }
            if expiration:
                params["expiration_date"] = expiration

            response = client.get(contracts_url, params=params)
            if response.status_code != 200:
                return _make_synthetic_chain(symbol, underlying_price)

            data = response.json()
            results = data.get("results", [])

            if not results:
                return _make_synthetic_chain(symbol, underlying_price)

            # Get snapshot of prices for these contracts
            contract_symbols = [r["ticker"] for r in results[:50]]
            snapshot_url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{','.join(contract_symbols)}"
            snap_response = client.get(snapshot_url, params={
                "apiKey": api_key,
            })

            snap_data = {}
            if snap_response.status_code == 200:
                for snap in snap_response.json().get("results", []):
                    snap_data[snap.get("ticker", "")] = snap

            calls: list[OptionContract] = []
            puts: list[OptionContract] = []
            expirations: set[str] = set()

            for contract in results:
                details = contract.get("details", {})
                ticker = contract.get("ticker", "")
                snap = snap_data.get(ticker, {})
                day = snap.get("day", {}) if snap else {}

                opt_type = details.get("contract_type", "").lower()
                strike = float(details.get("strike_price", 0))
                exp_date = details.get("expiration_date", "")
                expirations.add(exp_date)

                # Compute T for Greeks
                try:
                    exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
                    T = max(0.001, (exp_dt - datetime.now()).days / 365)
                except ValueError:
                    T = 7 / 365

                iv = float(day.get("implied_volatility", 0.30)) if day else 0.30
                greeks = calculate_greeks(underlying_price, strike, T, RISK_FREE_RATE, iv, opt_type)

                contract_obj = OptionContract(
                    symbol=ticker,
                    strike=strike,
                    expiration=exp_date,
                    option_type=opt_type,
                    bid=float(day.get("bid", 0) if day else 0),
                    ask=float(day.get("ask", 0) if day else 0),
                    last=float(day.get("close", 0) if day else 0),
                    volume=int(day.get("volume", 0) if day else 0),
                    open_interest=int(day.get("open_interest", 0) if day else 0),
                    implied_volatility=round(iv, 4),
                    delta=greeks["delta"],
                    gamma=greeks["gamma"],
                    theta=greeks["theta"],
                    vega=greeks["vega"],
                )

                if opt_type == "call":
                    calls.append(contract_obj)
                else:
                    puts.append(contract_obj)

            return OptionChain(
                symbol=symbol,
                underlying_price=underlying_price,
                expiration_dates=sorted(expirations),
                calls=sorted(calls, key=lambda c: c.strike),
                puts=sorted(puts, key=lambda p: p.strike),
            )

    except Exception:
        return _make_synthetic_chain(symbol, underlying_price)
