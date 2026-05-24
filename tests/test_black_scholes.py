"""Unit tests for Black-Scholes options pricing and Greeks."""

from __future__ import annotations

import math

import pytest

from portfolio.trading.options.black_scholes import (
    black_scholes,
    calculate_greeks,
    estimate_implied_volatility,
)


class TestBlackScholesPricing:
    """Test Black-Scholes option pricing accuracy."""

    def test_atm_call_price_positive(self):
        price = black_scholes(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")
        assert price > 0
        assert 4.0 < price < 9.0

    def test_atm_put_price_positive(self):
        price = black_scholes(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="put")
        assert price > 0
        assert 4.0 < price < 9.0

    def test_put_call_parity(self):
        S, K, T, r, sigma = 100, 105, 0.5, 0.05, 0.25
        call = black_scholes(S, K, T, r, sigma, "call")
        put = black_scholes(S, K, T, r, sigma, "put")
        parity_lhs = call - put
        parity_rhs = S - K * math.exp(-r * T)
        assert abs(parity_lhs - parity_rhs) < 0.01

    def test_deep_itm_call_approaches_intrinsic(self):
        S, K, T, r, sigma = 100, 50, 0.01, 0.05, 0.30
        price = black_scholes(S, K, T, r, sigma, "call")
        intrinsic = S - K * math.exp(-r * T)
        assert abs(price - intrinsic) < 1.0

    def test_deep_otm_call_approaches_zero(self):
        price = black_scholes(S=100, K=200, T=0.1, r=0.05, sigma=0.30, option_type="call")
        assert price < 0.01

    def test_higher_iv_increases_option_price(self):
        call_low = black_scholes(S=100, K=100, T=0.25, r=0.05, sigma=0.15, option_type="call")
        call_high = black_scholes(S=100, K=100, T=0.25, r=0.05, sigma=0.50, option_type="call")
        put_low = black_scholes(S=100, K=100, T=0.25, r=0.05, sigma=0.15, option_type="put")
        put_high = black_scholes(S=100, K=100, T=0.25, r=0.05, sigma=0.50, option_type="put")
        assert call_high > call_low
        assert put_high > put_low

    def test_longer_time_increases_option_price(self):
        price_short = black_scholes(S=100, K=100, T=0.05, r=0.05, sigma=0.30, option_type="call")
        price_long = black_scholes(S=100, K=100, T=0.50, r=0.05, sigma=0.30, option_type="call")
        assert price_long > price_short

    def test_higher_rate_increases_call_decreases_put(self):
        call_low_r = black_scholes(S=100, K=100, T=0.25, r=0.01, sigma=0.30, option_type="call")
        call_high_r = black_scholes(S=100, K=100, T=0.25, r=0.10, sigma=0.30, option_type="call")
        put_low_r = black_scholes(S=100, K=100, T=0.25, r=0.01, sigma=0.30, option_type="put")
        put_high_r = black_scholes(S=100, K=100, T=0.25, r=0.10, sigma=0.30, option_type="put")
        assert call_high_r > call_low_r
        assert put_low_r > put_high_r


class TestBlackScholesEdgeCases:
    """Test Black-Scholes edge cases and boundary conditions."""

    def test_expired_option_returns_intrinsic(self):
        assert black_scholes(S=100, K=90, T=0, r=0.05, sigma=0.30, option_type="call") == pytest.approx(10.0)
        assert black_scholes(S=90, K=100, T=0, r=0.05, sigma=0.30, option_type="call") == pytest.approx(0.0)
        assert black_scholes(S=90, K=100, T=0, r=0.05, sigma=0.30, option_type="put") == pytest.approx(10.0)
        assert black_scholes(S=100, K=90, T=0, r=0.05, sigma=0.30, option_type="put") == pytest.approx(0.0)

    def test_negative_time_treated_as_expired(self):
        price = black_scholes(S=100, K=90, T=-0.1, r=0.05, sigma=0.30, option_type="call")
        assert price == pytest.approx(10.0)

    def test_zero_volatility(self):
        call = black_scholes(S=100, K=95, T=0.25, r=0.05, sigma=0.001, option_type="call")
        expected = 100 - 95 * math.exp(-0.05 * 0.25)
        assert abs(call - expected) < 0.5

    def test_zero_underlying_price(self):
        call = black_scholes(S=0.01, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")
        put = black_scholes(S=0.01, K=100, T=0.25, r=0.05, sigma=0.30, option_type="put")
        assert call < 0.01
        assert put > 90

    def test_symmetric_for_atm_when_r_equals_zero(self):
        call = black_scholes(S=100, K=100, T=0.25, r=0.0, sigma=0.30, option_type="call")
        put = black_scholes(S=100, K=100, T=0.25, r=0.0, sigma=0.30, option_type="put")
        assert abs(call - put) < 0.01


class TestGreeks:
    """Test option Greeks accuracy and consistency."""

    def test_delta_range_call(self):
        greeks = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")
        assert 0.0 <= greeks["delta"] <= 1.0

    def test_delta_range_put(self):
        greeks = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="put")
        assert -1.0 <= greeks["delta"] <= 0.0

    def test_call_put_delta_sum(self):
        call = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")
        put = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="put")
        assert abs(call["delta"] - put["delta"] - 1.0) < 0.01

    def test_gamma_same_for_call_and_put(self):
        call = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")
        put = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="put")
        assert abs(call["gamma"] - put["gamma"]) < 0.0001

    def test_vega_same_for_call_and_put(self):
        call = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")
        put = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="put")
        assert abs(call["vega"] - put["vega"]) < 0.0001

    def test_atm_delta_approximately_half(self):
        greeks = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")
        assert 0.45 <= greeks["delta"] <= 0.65

    def test_deep_itm_delta_near_one(self):
        greeks = calculate_greeks(S=100, K=50, T=0.25, r=0.05, sigma=0.30, option_type="call")
        assert greeks["delta"] > 0.95

    def test_deep_otm_delta_near_zero(self):
        greeks = calculate_greeks(S=100, K=200, T=0.25, r=0.05, sigma=0.30, option_type="call")
        assert greeks["delta"] < 0.05

    def test_expired_greeks_zero(self):
        greeks = calculate_greeks(S=100, K=100, T=0, r=0.05, sigma=0.30, option_type="call")
        assert greeks == {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    def test_theta_negative_for_long_options(self):
        call_theta = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")["theta"]
        put_theta = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="put")["theta"]
        assert call_theta < 0, "Long call should have negative theta"
        assert put_theta < 0, "Long put should have negative theta"

    def test_gamma_peaks_near_atm(self):
        atm_gamma = calculate_greeks(S=100, K=100, T=0.25, r=0.05, sigma=0.30, option_type="call")["gamma"]
        otm_gamma = calculate_greeks(S=100, K=120, T=0.25, r=0.05, sigma=0.30, option_type="call")["gamma"]
        assert atm_gamma > otm_gamma


class TestImpliedVolatility:
    """Test implied volatility estimation via Newton-Raphson."""

    def test_recovers_known_iv(self):
        S, K, T, r, true_iv = 100, 105, 0.25, 0.05, 0.35
        market_price = black_scholes(S, K, T, r, true_iv, "call")
        estimated = estimate_implied_volatility(market_price, S, K, T, r, "call")
        assert estimated is not None
        assert abs(estimated - true_iv) < 0.01

    def test_recovers_atm_iv(self):
        S, K, T, r, true_iv = 100, 100, 0.5, 0.04, 0.25
        market_price = black_scholes(S, K, T, r, true_iv, "call")
        estimated = estimate_implied_volatility(market_price, S, K, T, r, "call")
        assert estimated is not None
        assert abs(estimated - true_iv) < 0.01

    def test_put_iv_recovery(self):
        S, K, T, r, true_iv = 100, 95, 0.25, 0.05, 0.40
        market_price = black_scholes(S, K, T, r, true_iv, "put")
        estimated = estimate_implied_volatility(market_price, S, K, T, r, "put")
        assert estimated is not None
        assert abs(estimated - true_iv) < 0.01

    def test_returns_none_for_extreme_price(self):
        result = estimate_implied_volatility(
            market_price=200, S=100, K=105, T=0.25, r=0.05,
            option_type="call",
        )
        if result is not None:
            assert result > 1.0

    def test_zero_volatility_edge_case(self):
        S, K, T, r = 100, 50, 0.25, 0.05
        intrinsic = S - K * math.exp(-r * T)
        estimated = estimate_implied_volatility(intrinsic, S, K, T, r, "call")
        if estimated is not None:
            assert estimated < 0.5
