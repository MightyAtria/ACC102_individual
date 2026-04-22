"""
data_fetcher.py
---------------
Fetches historical OHLCV stock data using the yfinance library,
which wraps the Yahoo Finance API and provides a clean pandas interface.

Docs: https://github.com/ranaroussi/yfinance
"""

import yfinance as yf
import pandas as pd


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_stock_data(
    ticker: str,
    period: str = None,
    start:  str = None,
    end:    str = None,
) -> pd.DataFrame:
    """
    Download daily OHLCV data for a US stock symbol via yfinance.

    Parameters
    ----------
    ticker : str   e.g. 'AAPL'
    period : str   '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y'
    start  : str   'YYYY-MM-DD'  (custom range; overrides period)
    end    : str   'YYYY-MM-DD'

    Returns
    -------
    pd.DataFrame  with columns Open / High / Low / Close / Volume
    """
    try:
        ticker_obj = yf.Ticker(ticker.upper())

        if start and end:
            df = ticker_obj.history(start=start, end=end, auto_adjust=True)
        else:
            df = ticker_obj.history(period=period or "1y", auto_adjust=True)

        # yfinance returns timezone-aware index — strip tz for consistency
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Keep only standard OHLCV columns
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.dropna(subset=["Close"]).sort_index()

    except Exception as e:
        raise ValueError(f"Failed to fetch data for '{ticker}': {e}")

    if df.empty:
        raise ValueError(
            f"No trading data found for '{ticker}' in the selected period. "
            "The symbol may be invalid or delisted. Try a different ticker or time range."
        )

    return df


def fetch_benchmark_data(
    period: str = None,
    start:  str = None,
    end:    str = None,
) -> pd.DataFrame:
    """Fetch SPY (S&P 500 ETF) as the market benchmark."""
    return fetch_stock_data("SPY", period=period, start=start, end=end)


def get_company_info(ticker: str) -> dict:
    """
    Return basic company metadata using yfinance Ticker.info.
    Falls back to safe defaults on any error.
    """
    try:
        info = yf.Ticker(ticker.upper()).info
        return {
            "name":       info.get("longName") or info.get("shortName") or ticker,
            "sector":     info.get("sector",   "—"),
            "industry":   info.get("industry", "—"),
            "market_cap": info.get("marketCap"),
            "currency":   info.get("currency", "USD"),
        }
    except Exception:
        return {
            "name": ticker, "sector": "—", "industry": "—",
            "market_cap": None, "currency": "USD",
        }
