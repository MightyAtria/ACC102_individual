"""
data_fetcher.py
---------------
Fetches historical stock price data from WRDS (Wharton Research Data Services)
using the CRSP Daily Stock Files (crsp.dsf).

Institution : Xi'an Jiaotong-Liverpool University (XJTLU)
Database    : CRSP — Center for Research in Security Prices
WRDS Portal : https://wrds-www.wharton.upenn.edu/

Credentials are read from Streamlit Cloud Secrets:
    WRDS_USERNAME = "your_wrds_username"
    WRDS_PASSWORD = "your_wrds_password"
"""

import os
import wrds
import pandas as pd
from datetime import datetime, timedelta

# ── Period string → calendar days ────────────────────────────────────────────
_PERIOD_DAYS = {
    "1mo":  30,
    "3mo":  90,
    "6mo":  180,
    "1y":   365,
    "2y":   730,
    "5y":   1825,
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _connect() -> wrds.Connection:
    """
    Establish a WRDS PostgreSQL connection.
    Reads credentials from Streamlit Secrets first, then environment variables.
    """
    username, password = "", ""
    try:
        import streamlit as st
        username = st.secrets.get("WRDS_USERNAME", "")
        password = st.secrets.get("WRDS_PASSWORD", "")
    except Exception:
        pass

    # Fallback to OS environment variables
    if not username:
        username = os.environ.get("WRDS_USERNAME", "")
    if not password:
        password = os.environ.get("WRDS_PASSWORD", "")

    if not username or not password:
        raise ValueError(
            "⚠️ WRDS credentials not configured.\n"
            "Please add WRDS_USERNAME and WRDS_PASSWORD to Streamlit Cloud Secrets.\n"
            "Dashboard → App Settings → Secrets"
        )

    return wrds.Connection(
        wrds_username=username,
        wrds_password=password,
    )


def _ticker_to_permno(db: wrds.Connection, ticker: str) -> int:
    """
    Map a stock ticker symbol to its CRSP PERMNO identifier.
    Uses crsp.stocknames; picks the most recent record if multiple exist.
    """
    sql = f"""
        SELECT permno
        FROM crsp.stocknames
        WHERE ticker = '{ticker.upper()}'
        ORDER BY nameenddt DESC NULLS FIRST
        LIMIT 1
    """
    result = db.raw_sql(sql)
    if result.empty:
        raise ValueError(
            f"Ticker '{ticker}' was not found in CRSP stocknames.\n"
            "The symbol may be unavailable in CRSP or delisted before coverage began."
        )
    return int(result["permno"].iloc[0])


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_stock_data(
    ticker: str,
    period: str = None,
    start:  str = None,
    end:    str = None,
) -> pd.DataFrame:
    """
    Download daily OHLCV-equivalent data from CRSP Daily Stock File (crsp.dsf).

    Note on CRSP data:
    - CRSP does NOT store Open / High / Low natively.
    - Close  = ABS(prc)  [negative prc means bid-ask midpoint was used]
    - High   = ask price (best available proxy)
    - Low    = bid price (best available proxy)
    - Open   = previous day's Close (synthetic)
    - Volume = shares traded (vol field, already in full shares for modern data)

    Parameters
    ----------
    ticker : str   e.g. 'AAPL'
    period : str   '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y'
    start  : str   'YYYY-MM-DD'
    end    : str   'YYYY-MM-DD'

    Returns
    -------
    pd.DataFrame  with columns Open / High / Low / Close / Volume
    """
    # ── Compute date range ─────────────────────────────────────────────────
    if start and end:
        d_start, d_end = start, end
    else:
        days    = _PERIOD_DAYS.get(period or "1y", 365)
        d_end   = datetime.today().strftime("%Y-%m-%d")
        d_start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    # ── Connect & query CRSP ───────────────────────────────────────────────
    db = _connect()
    try:
        permno = _ticker_to_permno(db, ticker)

        sql = f"""
            SELECT
                date,
                ABS(prc)                    AS "Close",
                COALESCE(ask, ABS(prc))     AS "High",
                COALESCE(bid, ABS(prc))     AS "Low",
                COALESCE(vol, 0)            AS "Volume"
            FROM crsp.dsf
            WHERE permno = {permno}
              AND date BETWEEN '{d_start}' AND '{d_end}'
            ORDER BY date ASC
        """
        df = db.raw_sql(sql, date_cols=["date"])

    finally:
        db.close()

    if df.empty:
        raise ValueError(
            f"No CRSP data found for '{ticker}' between {d_start} and {d_end}.\n"
            "Try extending the time range."
        )

    # ── Post-process ───────────────────────────────────────────────────────
    df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"

    # Synthetic Open = previous day's Close (standard academic practice)
    df["Open"] = df["Close"].shift(1).fillna(df["Close"])

    # Standard OHLCV column order
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df = df.dropna(subset=["Close"]).sort_index()

    return df


def fetch_benchmark_data(
    period: str = None,
    start:  str = None,
    end:    str = None,
) -> pd.DataFrame:
    """
    Fetch SPY (SPDR S&P 500 ETF) as the market benchmark.
    SPY is listed on NYSE Arca and is covered in CRSP since its 1993 inception.
    """
    return fetch_stock_data("SPY", period=period, start=start, end=end)


def get_company_info(ticker: str) -> dict:
    """
    Return basic company metadata from CRSP stocknames table.
    Falls back to safe defaults on any error.

    CRSP fields used:
    - comnam   : full company name
    - primexch : primary exchange (N=NYSE, Q=NASDAQ, A=AMEX)
    - siccd    : SIC industry code
    """
    _EXCHANGE = {"N": "NYSE", "Q": "NASDAQ", "A": "AMEX / NYSE MKT", "": "—"}

    try:
        db = _connect()
        try:
            sql = f"""
                SELECT comnam, primexch, siccd
                FROM crsp.stocknames
                WHERE ticker = '{ticker.upper()}'
                ORDER BY nameenddt DESC NULLS FIRST
                LIMIT 1
            """
            result = db.raw_sql(sql)
        finally:
            db.close()

        if result.empty:
            raise ValueError("Not found")

        row  = result.iloc[0]
        exch = _EXCHANGE.get(str(row.get("primexch", "")).strip(), "—")
        return {
            "name":       str(row.get("comnam", ticker)).title(),
            "sector":     exch,
            "industry":   f"SIC {int(row['siccd'])}" if row.get("siccd") else "—",
            "market_cap": None,   # not available in crsp.dsf
            "currency":   "USD",
        }

    except Exception:
        return {
            "name": ticker, "sector": "—", "industry": "—",
            "market_cap": None, "currency": "USD",
        }
