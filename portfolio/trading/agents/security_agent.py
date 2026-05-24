"""Security Agent — Symbol validation and company identification.

Responsibility:
  1. Accept stock security symbol from user
  2. Validate the symbol exists and is tradeable
  3. Identify company profile (name, sector, market cap, current price)
  4. Determine if the security has listed options
  5. Provide initial buy/sell context based on company fundamentals

Uses:
  - yfinance for market data
  - OpenAI GPT-4o for reasoning about the company
  - LangChain for structured LLM interaction
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

import yfinance as yf

from ..models import SecurityInfo


SYSTEM_PROMPT = """You are the Security Identification Agent in a multi-agent trading system.

Your responsibilities:
1. Verify that a stock ticker symbol is valid and tradeable on US exchanges
2. Gather company profile information (name, sector, industry, market cap)
3. Assess whether options are available for this security
4. Provide initial context about whether this company might be a candidate for options trading

For the given symbol, analyze it and respond with a structured assessment.
Be concise but thorough. Include:
- Company name and what they do
- Sector and industry classification
- Current market cap tier (mega/large/mid/small/micro)
- Whether options are available (most US stocks > $5 with market cap > $300M have options)
- A brief 2-3 sentence summary of the company's current position

Do NOT recommend specific trades — that's the Decision Agent's job.
Focus on identification and validation only."""


class SecurityAgent:
    """Agent #1: Security Identification & Validation."""

    NAME = "Security Agent"

    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.2)

    def analyze(self, symbol: str) -> SecurityInfo:
        """Analyze and validate a security symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL').

        Returns:
            SecurityInfo with company profile and validation.
        """
        symbol = symbol.strip().upper()

        # Fetch market data
        stock = yf.Ticker(symbol)
        try:
            info = stock.info
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                # Check history as fallback
                hist = stock.history(period="5d")
                if hist.empty:
                    return SecurityInfo(
                        symbol=symbol,
                        company_name=f"Unknown ({symbol})",
                        reasoning=(
                            f"Could not validate symbol '{symbol}'. "
                            "It may be invalid, delisted, or unavailable through Yahoo Finance."
                        ),
                        is_optionable=False,
                    )
        except Exception:
            return SecurityInfo(
                symbol=symbol,
                company_name=f"Unknown ({symbol})",
                reasoning=f"Failed to fetch data for {symbol}. Yahoo Finance may be unavailable.",
                is_optionable=False,
            )

        # Build SecurityInfo from market data
        company_name = info.get("longName") or info.get("shortName") or f"{symbol} Inc."
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        market_cap = info.get("marketCap")
        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        exchange = info.get("exchange", "N/A")
        currency = info.get("currency", "USD")

        # Determine if optionable (most US stocks are)
        is_optionable = (
            exchange in ("NMS", "NYQ", "ASE", "PCX", "BATS", "NCM", "NGM")
            or "NASDAQ" in exchange.upper()
            or "NYSE" in exchange.upper()
        )
        if current_price and current_price < 5:
            is_optionable = False

        # Use LLM for reasoning
        company_context = f"""
Symbol: {symbol}
Company: {company_name}
Sector: {sector}
Industry: {industry}
Market Cap: ${market_cap:,.0f}" if market_cap else "N/A"
Current Price: ${current_price:.2f}" if current_price else "N/A"
Exchange: {exchange}
Options Available: {'Yes' if is_optionable else 'No'}
"""

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=(
                    f"Analyze this security and provide your identification assessment:\n\n{company_context}"
                )),
            ]
            response = self.llm.invoke(messages)
            reasoning = str(response.content) if hasattr(response, 'content') else str(response)
        except Exception:
            reasoning = (
                f"Validated {symbol} ({company_name}) — {sector}/{industry}. "
                f"Market cap: ${market_cap:,.0f}. "
                f"Options available: {'Yes' if is_optionable else 'No'}."
                if market_cap else
                f"Validated {symbol} ({company_name}) — {sector}/{industry}. "
                f"Options available: {'Yes' if is_optionable else 'No'}."
            )

        return SecurityInfo(
            symbol=symbol,
            company_name=company_name,
            sector=sector,
            industry=industry,
            market_cap=market_cap,
            current_price=current_price,
            exchange=exchange,
            currency=currency,
            is_optionable=is_optionable,
            reasoning=reasoning,
        )
