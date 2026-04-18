"""
metrics.py
----------
Quantitative risk / performance metrics for a daily return series.
All functions accept a pd.Series of daily closing prices and return
a single scalar (float) unless noted otherwise.
"""

import numpy as np
import pandas as pd


# ── helpers ──────────────────────────────────────────────────────────────────

def _daily_returns(prices: pd.Series) -> pd.Series:
    """Compute simple daily percentage returns, drop the first NaN."""
    return prices.pct_change().dropna()


def _annualise(daily_std: float, trading_days: int = 252) -> float:
    return daily_std * np.sqrt(trading_days)


# ── individual metrics ────────────────────────────────────────────────────────

def cagr(prices: pd.Series) -> float:
    """
    Compound Annual Growth Rate.
    CAGR = (end/start)^(252/n) - 1
    """
    n = len(prices)
    if n < 2:
        return np.nan
    years = n / 252
    return (prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1


def annualised_volatility(prices: pd.Series) -> float:
    """Annualised standard deviation of daily returns."""
    return _annualise(_daily_returns(prices).std())


def sharpe_ratio(prices: pd.Series, risk_free_rate: float = 0.05) -> float:
    """
    Annualised Sharpe Ratio.
    SR = (mean_daily_return - rf_daily) / std_daily  * sqrt(252)
    """
    rets = _daily_returns(prices)
    rf_daily = risk_free_rate / 252
    excess = rets - rf_daily
    if excess.std() == 0:
        return np.nan
    return (excess.mean() / excess.std()) * np.sqrt(252)


def sortino_ratio(prices: pd.Series, risk_free_rate: float = 0.05) -> float:
    """
    Sortino Ratio — uses downside deviation only.
    """
    rets = _daily_returns(prices)
    rf_daily = risk_free_rate / 252
    excess = rets - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return np.nan
    downside_std = downside.std() * np.sqrt(252)
    annual_excess = excess.mean() * 252
    return annual_excess / downside_std


def max_drawdown(prices: pd.Series) -> float:
    """
    Maximum Drawdown: largest peak-to-trough decline.
    Returns a negative float (e.g. -0.35 means −35 %).
    """
    roll_max = prices.cummax()
    drawdown = prices / roll_max - 1
    return drawdown.min()


def beta(prices: pd.Series, benchmark_prices: pd.Series) -> float:
    """
    Beta relative to a benchmark (e.g. SPY).
    Aligns both series by date before computing covariance.
    """
    rets = _daily_returns(prices)
    bench_rets = _daily_returns(benchmark_prices)
    aligned = pd.concat([rets, bench_rets], axis=1, join="inner")
    aligned.columns = ["asset", "bench"]
    cov_matrix = aligned.cov()
    bench_var = aligned["bench"].var()
    if bench_var == 0:
        return np.nan
    return cov_matrix.loc["asset", "bench"] / bench_var


def calmar_ratio(prices: pd.Series) -> float:
    """Calmar Ratio = CAGR / |Max Drawdown|."""
    mdd = max_drawdown(prices)
    if mdd == 0:
        return np.nan
    return cagr(prices) / abs(mdd)


# ── summary dict ─────────────────────────────────────────────────────────────

def compute_all_metrics(prices: pd.Series,
                        benchmark_prices: pd.Series = None,
                        risk_free_rate: float = 0.05) -> dict:
    """
    Return all metrics in a single dictionary.
    benchmark_prices is optional; Beta / Calmar will be NaN if omitted.
    """
    results = {
        "CAGR":                 cagr(prices),
        "Annualised Volatility": annualised_volatility(prices),
        "Sharpe Ratio":         sharpe_ratio(prices, risk_free_rate),
        "Sortino Ratio":        sortino_ratio(prices, risk_free_rate),
        "Max Drawdown":         max_drawdown(prices),
        "Calmar Ratio":         calmar_ratio(prices),
    }
    if benchmark_prices is not None and not benchmark_prices.empty:
        results["Beta (vs SPY)"] = beta(prices, benchmark_prices)
    else:
        results["Beta (vs SPY)"] = np.nan
    return results


def get_moving_averages(prices: pd.Series) -> pd.DataFrame:
    """
    Return a DataFrame with the original Close price and MA20 / MA50.
    """
    df = prices.to_frame(name="Close")
    df["MA20"] = prices.rolling(20).mean()
    df["MA50"] = prices.rolling(50).mean()
    return df


def get_drawdown_series(prices: pd.Series) -> pd.Series:
    """Return the full rolling drawdown series (always ≤ 0)."""
    roll_max = prices.cummax()
    return prices / roll_max - 1
