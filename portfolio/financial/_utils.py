"""Shared utilities for financial agents."""

def safe_info(stock) -> dict:
    """Safely extract info dict, returning empty dict on failure."""
    try:
        return stock.info or {}
    except Exception:
        return {}


def fetch_stock_data(ticker: str):
    """Fetch both info and price history for a ticker once.

    Returns (info_dict, history_dataframe_or_None).
    """
    import yfinance as yf
    try:
        stock = yf.Ticker(ticker)
        info = safe_info(stock)
        hist = stock.history(period="1y")
        return info, hist if not hist.empty else None
    except Exception:
        return {}, None
