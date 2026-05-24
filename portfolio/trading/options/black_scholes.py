"""Black-Scholes options pricing model.

Implements the Black-Scholes formula for European options pricing,
Greeks calculation, and implied volatility estimation.

Used to generate realistic synthetic option chains when Polygon.io
data is unavailable or as a fallback.
"""

from __future__ import annotations

import math
from typing import Optional

from scipy.stats import norm


def black_scholes(
    S: float,       # Underlying price
    K: float,       # Strike price
    T: float,       # Time to expiration (years)
    r: float,       # Risk-free rate
    sigma: float,   # Implied volatility
    option_type: str = "call",
) -> float:
    """Calculate Black-Scholes option price.

    Args:
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate (e.g., 0.05 for 5%).
        sigma: Implied volatility (e.g., 0.30 for 30%).
        option_type: "call" or "put".

    Returns:
        Theoretical option price.
    """
    if T <= 0:
        # At expiration, intrinsic value
        if option_type == "call":
            return max(0.0, S - K)
        return max(0.0, K - S)

    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def calculate_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> dict[str, float]:
    """Calculate option Greeks (Delta, Gamma, Theta, Vega).

    Args:
        S, K, T, r, sigma: Same as black_scholes.
        option_type: "call" or "put".

    Returns:
        Dict with delta, gamma, theta, vega values.
    """
    if T <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    # Delta
    if option_type == "call":
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1

    # Gamma (same for call and put)
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))

    # Theta (per year, then convert to per day)
    term1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
    if option_type == "call":
        term2 = r * K * math.exp(-r * T) * norm.cdf(d2)
        theta = (term1 - term2) / 365
    else:
        term2 = r * K * math.exp(-r * T) * norm.cdf(-d2)
        theta = (term1 + term2) / 365

    # Vega (per 1% change in IV)
    vega = S * norm.pdf(d1) * math.sqrt(T) / 100

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 4),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
    }


def estimate_implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    max_iterations: int = 100,
    tolerance: float = 0.0001,
) -> Optional[float]:
    """Estimate implied volatility from market price using Newton-Raphson.

    Args:
        market_price: Observed market price of the option.
        S, K, T, r: Same as black_scholes.
        option_type: "call" or "put".
        max_iterations: Maximum Newton-Raphson iterations.
        tolerance: Convergence tolerance.

    Returns:
        Estimated implied volatility, or None if it fails to converge.
    """
    sigma = 0.3  # Initial guess (30% IV)

    for _ in range(max_iterations):
        price = black_scholes(S, K, T, r, sigma, option_type)
        diff = market_price - price

        if abs(diff) < tolerance:
            return sigma

        # Vega (derivative of price w.r.t. sigma)
        if T <= 0:
            break
        d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
        vega = S * norm.pdf(d1) * math.sqrt(T)

        if vega == 0:
            break

        sigma = sigma + diff / vega

        # Clamp to reasonable range
        sigma = max(0.01, min(5.0, sigma))

    return None
