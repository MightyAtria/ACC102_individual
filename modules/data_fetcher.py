"""
data_fetcher.py
---------------
Fetches historical OHLCV stock data directly from the Yahoo Finance v8 API
using requests with browser-like headers to avoid 429 / empty-response issues.
"""

import requests
import pandas as pd
from datetime import datetime, date

# ── session with browser-like headers (avoids Yahoo Finance 429 / empty body) ─
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://finance.yahoo.com",
    "Origin":          "https://finance.yahoo.com",
})

_YF_CHART = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"

# period string → seconds-back from now
_PERIOD_MAP = {
    "1mo":  30  * 86400,
    "3mo":  90  * 86400,
    "6mo":  180 * 86400,
    "1y":   365 * 86400,
    "2y":   730 * 86400,
    "5y":   1825 * 86400,
}


def _fetch_raw(symbol: str, params: dict) -> dict:
    url = _YF_CHART.format(symbol=symbol.upper())
    resp = _SESSION.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    result = data.get("chart", {}).get("result")
    if not result:
        err = data.get("chart", {}).get("error", {})
        raise ValueError(
            f"No data for '{symbol}': {err.get('description', 'unknown error')}"
        )
    return result[0]


def _result_to_df(result: dict) -> pd.DataFrame:
    """Convert raw Yahoo Finance chart result to a clean OHLCV DataFrame."""
    timestamps = result["timestamp"]
    q = result["indicators"]["quote"][0]

    df = pd.DataFrame({
        "Open":   q["open"],
        "High":   q["high"],
        "Low":    q["low"],
        "Close":  q["close"],
        "Volume": q["volume"],
    }, index=pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None))

    df.index.name = "Date"
    df = df.dropna(subset=["Close"])          # drop any NaN rows
    df = df.sort_index()
    return df


def fetch_stock_data(
    ticker: str,
    period: str = None,
    start: str = None,
    end: str = None,
) -> pd.DataFrame:
    """
    Download daily OHLCV data for a US stock symbol.

    Parameters
    ----------
    ticker : str   e.g. 'AAPL'
    period : str   '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y'
    start  : str   'YYYY-MM-DD'  (used when period is None)
    end    : str   'YYYY-MM-DD'
    """
    if start and end:
        t1 = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
        t2 = int(datetime.strptime(end,   "%Y-%m-%d").timestamp())
        params = {"interval": "1d", "period1": t1, "period2": t2}
    else:
        secs = _PERIOD_MAP.get(period or "1y", 365 * 86400)
        now  = int(datetime.utcnow().timestamp())
        params = {"interval": "1d", "period1": now - secs, "period2": now}

    try:
        result = _fetch_raw(ticker, params)
    except ValueError:
        raise
    except requests.HTTPError as e:
        raise ValueError(
            f"HTTP {e.response.status_code} fetching '{ticker}'. "
            "Check the ticker symbol and try again."
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch data for '{ticker}': {e}")

    df = _result_to_df(result)
    if df.empty:
        raise ValueError(
            f"No trading data found for '{ticker}' in the selected period."
        )
    return df


def fetch_benchmark_data(period: str = None, start: str = None, end: str = None) -> pd.DataFrame:
    """Fetch SPY (S&P 500 ETF) as the market benchmark."""
    return fetch_stock_data("SPY", period=period, start=start, end=end)


def get_company_info(ticker: str) -> dict:
    """
    Return basic company metadata from Yahoo Finance quote summary.
    Falls back gracefully on any error.
    """
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker.upper()}"
    params = {"modules": "assetProfile,summaryDetail,price"}
    try:
        resp = _SESSION.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        res   = data["quoteSummary"]["result"][0]
        prof  = res.get("assetProfile", {})
        price = res.get("price", {})
        return {
            "name":       price.get("longName") or price.get("shortName") or ticker,
            "sector":     prof.get("sector",   "—"),
            "industry":   prof.get("industry", "—"),
            "market_cap": price.get("marketCap", {}).get("raw"),
            "currency":   price.get("currency", "USD"),
        }
    except Exception:
        return {"name": ticker, "sector": "—", "industry": "—",
                "market_cap": None, "currency": "USD"}
