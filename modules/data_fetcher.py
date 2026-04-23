"""
data_fetcher.py
---------------
Fetches historical stock price data from WRDS (Wharton Research Data Services)
using the CRSP Daily Stock Files (crsp.dsf).

Each user provides their own WRDS credentials via the app sidebar.

Institution : Xi'an Jiaotong-Liverpool University (XJTLU)
Database    : CRSP — Center for Research in Security Prices
WRDS Portal : https://wrds-www.wharton.upenn.edu/
"""

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

def _connect(username: str, password: str) -> wrds.Connection:
    """
    Establish a WRDS PostgreSQL connection using user-supplied credentials.
    """
    if not username or not password:
        raise ValueError(
            "Please enter your WRDS Username and Password in the sidebar to proceed."
        )
    try:
        return wrds.Connection(
            wrds_username=username.strip(),
            wrds_password=password.strip(),
        )
    except Exception as e:
        raise ValueError(
            f"WRDS login failed: {e}\n"
            "Please check your username and password."
        )


def _ticker_to_permno(db: wrds.Connection, ticker: str) -> int:
    """
    Map a stock ticker to its CRSP PERMNO using crsp.stocknames.
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
            f"Ticker '{ticker}' was not found in CRSP.\n"
            "The symbol may not be covered or may be delisted."
        )
    return int(result["permno"].iloc[0])


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_stock_data(
    ticker:   str,
    username: str,
    password: str,
    period:   str = None,
    start:    str = None,
    end:      str = None,
) -> pd.DataFrame:
    """
    Download daily OHLCV-equivalent data from CRSP Daily Stock File (crsp.dsf).

    CRSP field mapping:
    - Close  = ABS(prc)           [negative prc = bid-ask midpoint used]
    - High   = ask price
    - Low    = bid price
    - Open   = previous day Close [CRSP has no Open field]
    - Volume = vol (shares)

    Parameters
    ----------
    ticker   : str   e.g. 'AAPL'
    username : str   WRDS username
    password : str   WRDS password
    period   : str   '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y'
    start    : str   'YYYY-MM-DD'
    end      : str   'YYYY-MM-DD'
    """
    # Date range
    if start and end:
        d_start, d_end = start, end
    else:
        days    = _PERIOD_DAYS.get(period or "1y", 365)
        d_end   = datetime.today().strftime("%Y-%m-%d")
        d_start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    db = _connect(username, password)
    try:
        permno = _ticker_to_permno(db, ticker)

        sql = f"""
            SELECT
                date,
                ABS(prc)                 AS "Close",
                COALESCE(ask, ABS(prc))  AS "High",
                COALESCE(bid, ABS(prc))  AS "Low",
                COALESCE(vol, 0)         AS "Volume"
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
            f"No CRSP data for '{ticker}' between {d_start} and {d_end}.\n"
            "Try a longer time range."
        )

    df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"

    # Synthetic Open = previous Close
    df["Open"] = df["Close"].shift(1).fillna(df["Close"])
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df = df.dropna(subset=["Close"]).sort_index()
    return df


def fetch_benchmark_data(
    username: str,
    password: str,
    period:   str = None,
    start:    str = None,
    end:      str = None,
) -> pd.DataFrame:
    """Fetch SPY (S&P 500 ETF) as the market benchmark from CRSP."""
    return fetch_stock_data(
        "SPY", username, password,
        period=period, start=start, end=end,
    )


def get_company_info(ticker: str, username: str, password: str) -> dict:
    """
    Return company metadata from crsp.stocknames.
    """
    _EXCHANGE = {"N": "NYSE", "Q": "NASDAQ", "A": "AMEX", "": "—"}
    try:
        db = _connect(username, password)
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
            "market_cap": None,
            "currency":   "USD",
        }
    except Exception:
        return {
            "name": ticker, "sector": "—", "industry": "—",
            "market_cap": None, "currency": "USD",
        }
