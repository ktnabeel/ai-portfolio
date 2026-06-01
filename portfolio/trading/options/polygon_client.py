"""Polygon.io options chain client.

Fetches real options data from Polygon.io API for US equity options.
Provides option chain construction with Greeks computed via Black-Scholes.

API: https://polygon.io/docs/options
Requires: POLYGON_API_KEY environment variable.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx
import yfinance as yf

from .black_scholes import black_scholes, calculate_greeks
from ..models import OptionChain, OptionContract


POLYGON_BASE_URL = "https://api.polygon.io"
RISK_FREE_RATE = 0.045  # ~4.5% current risk-free rate


def _get_api_key() -> Optional[str]:
    """Get Polygon API key from environment."""
    return os.environ.get("POLYGON_API_KEY")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return int(number)


def _get_underlying_price(symbol: str) -> float:
    """Best-effort underlying price lookup using Yahoo Finance."""
    try:
        stock = yf.Ticker(symbol)
        info = stock.fast_info if hasattr(stock, "fast_info") else stock.info
        if hasattr(info, "last_price"):
            underlying_price = _safe_float(info.last_price)
        elif isinstance(info, dict):
            underlying_price = _safe_float(
                info.get("regularMarketPrice", info.get("currentPrice", 0))
            )
        else:
            underlying_price = 0.0

        if underlying_price <= 0:
            hist = stock.history(period="1d")
            if not hist.empty:
                underlying_price = _safe_float(hist["Close"].iloc[-1])
    except Exception:
        underlying_price = 0.0

    return underlying_price if underlying_price > 0 else 100.0


def _metadata(source: str, warning: str | None = None, is_realtime: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "source": source,
        "freshness": _utc_now_iso(),
        "is_realtime": is_realtime,
    }
    if warning:
        data["warning"] = warning
    return data


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


def _row_to_contract(row: Any, symbol: str, expiration: str, option_type: str, underlying_price: float) -> OptionContract:
    strike = _safe_float(row.get("strike"))
    iv = _safe_float(row.get("impliedVolatility"), 0.30) or 0.30
    try:
        exp_dt = datetime.strptime(expiration, "%Y-%m-%d")
        T = max(0.001, (exp_dt - datetime.now()).days / 365)
    except ValueError:
        T = 7 / 365

    greeks = calculate_greeks(underlying_price, strike, T, RISK_FREE_RATE, iv, option_type)
    contract_symbol = str(row.get("contractSymbol") or row.get("symbol") or "")
    if not contract_symbol:
        suffix = "C" if option_type == "call" else "P"
        contract_symbol = f"O:{symbol}{expiration.replace('-','')}{suffix}{int(strike * 1000):08d}"

    return OptionContract(
        symbol=contract_symbol,
        strike=strike,
        expiration=expiration,
        option_type=option_type,
        bid=_safe_float(row.get("bid")),
        ask=_safe_float(row.get("ask")),
        last=_safe_float(row.get("lastPrice", row.get("last"))),
        volume=_safe_int(row.get("volume")),
        open_interest=_safe_int(row.get("openInterest", row.get("open_interest"))),
        implied_volatility=round(iv, 4),
        delta=greeks["delta"],
        gamma=greeks["gamma"],
        theta=greeks["theta"],
        vega=greeks["vega"],
    )


def _records_from_frame(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        try:
            return list(frame.to_dict("records"))
        except TypeError:
            return []
    if isinstance(frame, list):
        return [r for r in frame if isinstance(r, dict)]
    return []


def _fetch_yfinance_option_chain(
    symbol: str,
    underlying_price: float,
    expiration: Optional[str] = None,
) -> OptionChain:
    stock = yf.Ticker(symbol)
    expirations = list(getattr(stock, "options", []) or [])
    if not expirations:
        raise RuntimeError("Yahoo Finance returned no option expirations")

    selected_exp = expiration if expiration in expirations else expirations[0]
    raw_chain = stock.option_chain(selected_exp)
    calls = [
        _row_to_contract(row, symbol, selected_exp, "call", underlying_price)
        for row in _records_from_frame(getattr(raw_chain, "calls", None))
    ]
    puts = [
        _row_to_contract(row, symbol, selected_exp, "put", underlying_price)
        for row in _records_from_frame(getattr(raw_chain, "puts", None))
    ]
    if not calls and not puts:
        raise RuntimeError("Yahoo Finance returned an empty option chain")

    return OptionChain(
        symbol=symbol,
        underlying_price=underlying_price,
        expiration_dates=expirations,
        calls=sorted(calls, key=lambda c: c.strike),
        puts=sorted(puts, key=lambda p: p.strike),
    )


def _fetch_polygon_option_chain(
    symbol: str,
    underlying_price: float,
    api_key: str,
    expiration: Optional[str] = None,
) -> OptionChain:
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
            raise RuntimeError(f"Polygon contracts request failed: HTTP {response.status_code}")

        data = response.json()
        results = data.get("results", [])

        if not results:
            raise RuntimeError("Polygon returned no option contracts")

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
            strike = _safe_float(details.get("strike_price"))
            exp_date = details.get("expiration_date", "")
            expirations.add(exp_date)

            # Compute T for Greeks
            try:
                exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
                T = max(0.001, (exp_dt - datetime.now()).days / 365)
            except ValueError:
                T = 7 / 365

            iv = _safe_float(day.get("implied_volatility"), 0.30) if day else 0.30
            greeks = calculate_greeks(underlying_price, strike, T, RISK_FREE_RATE, iv, opt_type)

            contract_obj = OptionContract(
                symbol=ticker,
                strike=strike,
                expiration=exp_date,
                option_type=opt_type,
                bid=_safe_float(day.get("bid") if day else 0),
                ask=_safe_float(day.get("ask") if day else 0),
                last=_safe_float(day.get("close") if day else 0),
                volume=_safe_int(day.get("volume") if day else 0),
                open_interest=_safe_int(day.get("open_interest") if day else 0),
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


def fetch_option_chain_with_metadata(
    symbol: str,
    expiration: Optional[str] = None,
) -> tuple[OptionChain, dict[str, Any]]:
    """Fetch an option chain and provider metadata without changing OptionChain."""
    symbol = symbol.strip().upper()
    underlying_price = _get_underlying_price(symbol)
    api_key = _get_api_key()

    if api_key:
        try:
            return (
                _fetch_polygon_option_chain(symbol, underlying_price, api_key, expiration),
                _metadata("polygon", is_realtime=True),
            )
        except Exception as exc:
            polygon_warning = f"Polygon option chain unavailable; falling back to Yahoo Finance. {exc}"
    else:
        polygon_warning = ""

    try:
        warning = "Yahoo Finance option chain may be delayed."
        if polygon_warning:
            warning = f"{polygon_warning} {warning}"
        return (
            _fetch_yfinance_option_chain(symbol, underlying_price, expiration),
            _metadata("yfinance", warning=warning, is_realtime=False),
        )
    except Exception as exc:
        warning = f"Synthetic option chain generated because live option data was unavailable. {exc}"
        if polygon_warning:
            warning = f"{polygon_warning} {warning}"
        return (
            _make_synthetic_chain(symbol, underlying_price),
            _metadata("synthetic", warning=warning, is_realtime=False),
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
    chain, _metadata_dict = fetch_option_chain_with_metadata(symbol, expiration)
    return chain
