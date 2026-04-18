"""
app.py
------
ACC102 Financial Analysis Dashboard
Entry point for the Streamlit web application.

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

from modules.data_fetcher import fetch_stock_data, fetch_benchmark_data, get_company_info
from modules.metrics import compute_all_metrics, get_moving_averages, get_drawdown_series
from modules.charts import (
    price_chart,
    returns_histogram,
    drawdown_chart,
    cumulative_return_chart,
)

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Dark gradient background */
  .stApp {
    background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 50%, #16213E 100%);
    color: #E2E8F0;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: rgba(255,255,255,0.04);
    border-right: 1px solid rgba(255,255,255,0.08);
  }

  /* KPI metric cards */
  .kpi-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(108,99,255,0.3);
    border-radius: 14px;
    padding: 18px 22px;
    text-align: center;
    transition: transform 0.2s, border-color 0.2s;
  }
  .kpi-card:hover {
    transform: translateY(-3px);
    border-color: rgba(108,99,255,0.8);
  }
  .kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #94A3B8;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #A5B4FC;
  }
  .kpi-value.positive { color: #22D3A5; }
  .kpi-value.negative { color: #F87171; }

  /* Section headers */
  .section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #A5B4FC;
    border-left: 3px solid #6C63FF;
    padding-left: 10px;
    margin: 24px 0 12px 0;
  }

  /* Company badge */
  .company-badge {
    background: linear-gradient(90deg, rgba(108,99,255,0.2), rgba(34,211,165,0.1));
    border: 1px solid rgba(108,99,255,0.4);
    border-radius: 10px;
    padding: 16px 24px;
    margin-bottom: 20px;
  }
  .company-name {
    font-size: 1.5rem;
    font-weight: 700;
    color: #E2E8F0;
  }
  .company-meta {
    font-size: 0.85rem;
    color: #94A3B8;
    margin-top: 4px;
  }

  /* Metric explanation table */
  .metric-note {
    font-size: 0.82rem;
    color: #64748B;
    font-style: italic;
  }

  /* Divider */
  hr { border-color: rgba(255,255,255,0.07); }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    ticker = st.text_input(
        "Stock Ticker (US)",
        value="AAPL",
        placeholder="e.g. AAPL, TSLA, MSFT",
        help="Enter a valid US stock symbol listed on NYSE or NASDAQ.",
    ).upper().strip()

    st.markdown("**Time Range**")
    range_mode = st.radio(
        "Select mode",
        ["Preset", "Custom dates"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if range_mode == "Preset":
        preset = st.select_slider(
            "Period",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            value="1y",
        )
        start_date, end_date = None, None
    else:
        preset = None
        col_s, col_e = st.columns(2)
        start_date = col_s.date_input("Start", value=date.today() - timedelta(days=365))
        end_date   = col_e.date_input("End",   value=date.today())

    st.markdown("---")
    risk_free = st.slider(
        "Risk-Free Rate (%)",
        min_value=0.0, max_value=10.0,
        value=5.0, step=0.25,
        help="Annual risk-free rate used for Sharpe & Sortino calculation.",
    ) / 100

    run = st.button("🚀 Analyse", use_container_width=True, type="primary")
    st.markdown("---")
    st.markdown(
        "<span style='font-size:0.75rem;color:#475569;'>"
        "Data provided by Yahoo Finance via yfinance.<br>"
        "For educational purposes only.</span>",
        unsafe_allow_html=True,
    )


# ── Main panel ────────────────────────────────────────────────────────────────
st.markdown("# 📊 Financial Analysis Dashboard")
st.markdown(
    "<p style='color:#64748B;margin-top:-10px;'>"
    "Intro-level quantitative analysis for US equities | ACC102 Individual Project</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

if not run:
    st.markdown(
        """
        <div style='text-align:center;padding:80px 0;'>
          <div style='font-size:4rem;'>📈</div>
          <div style='font-size:1.2rem;color:#94A3B8;margin-top:16px;'>
            Enter a ticker in the sidebar and click <strong>Analyse</strong> to begin.
          </div>
          <div style='font-size:0.88rem;color:#475569;margin-top:8px;'>
            Examples: AAPL · TSLA · MSFT · NVDA · AMZN · META
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Data fetching ─────────────────────────────────────────────────────────────
with st.spinner(f"Fetching data for **{ticker}** …"):
    try:
        if preset:
            df = fetch_stock_data(ticker, period=preset)
            bench_df = fetch_benchmark_data(period=preset)
        else:
            df = fetch_stock_data(ticker,
                                   start=str(start_date),
                                   end=str(end_date))
            bench_df = fetch_benchmark_data(start=str(start_date),
                                             end=str(end_date))
        info = get_company_info(ticker)
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Data fetch failed: {e}")
        st.stop()

# ── Company badge ─────────────────────────────────────────────────────────────
mcap = info.get("market_cap")
mcap_str = f"${mcap/1e9:.1f}B" if mcap else "N/A"
st.markdown(
    f"""
    <div class="company-badge">
      <div class="company-name">{info['name']} &nbsp;
        <span style='font-size:1rem;color:#6C63FF;font-weight:400;'>({ticker})</span>
      </div>
      <div class="company-meta">
        {info['sector']} &nbsp;·&nbsp; {info['industry']} &nbsp;·&nbsp;
        Market Cap: {mcap_str} &nbsp;·&nbsp;
        {len(df)} trading days analysed
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Metrics calculation ───────────────────────────────────────────────────────
prices = df["Close"]
metrics = compute_all_metrics(prices, bench_df["Close"], risk_free_rate=risk_free)
ma_df  = get_moving_averages(prices)
dd_series = get_drawdown_series(prices)


def _fmt(val, pct=False, decimals=2):
    """Format a metric value; return '—' for NaN."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if pct:
        return f"{val*100:.{decimals}f}%"
    return f"{val:.{decimals}f}"


def _color(val, higher_good=True):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    return "positive" if (val > 0) == higher_good else "negative"


def _kpi(label, value, pct=False, higher_good=True, decimals=2):
    fmt = _fmt(value, pct=pct, decimals=decimals)
    cls = _color(value, higher_good=higher_good)
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value {cls}">{fmt}</div>'
        f'</div>'
    )


# ── KPI Row ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📌 Key Performance Indicators</div>',
            unsafe_allow_html=True)

cols = st.columns(7)
kpi_defs = [
    ("CAGR",                  metrics["CAGR"],                   True,  True,  1),
    ("Volatility",            metrics["Annualised Volatility"],   True,  False, 1),
    ("Sharpe Ratio",          metrics["Sharpe Ratio"],            False, True,  2),
    ("Sortino Ratio",         metrics["Sortino Ratio"],           False, True,  2),
    ("Max Drawdown",          metrics["Max Drawdown"],            True,  False, 1),
    ("Calmar Ratio",          metrics["Calmar Ratio"],            False, True,  2),
    ("Beta (vs SPY)",         metrics["Beta (vs SPY)"],           False, None,  2),
]
for col, (label, val, pct, hg, dec) in zip(cols, kpi_defs):
    with col:
        st.markdown(_kpi(label, val, pct=pct,
                         higher_good=hg if hg is not None else True,
                         decimals=dec),
                    unsafe_allow_html=True)

# ── Charts ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📉 Price History</div>',
            unsafe_allow_html=True)
st.plotly_chart(price_chart(df, ma_df, ticker), use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown('<div class="section-header">📊 Return Distribution</div>',
                unsafe_allow_html=True)
    st.plotly_chart(returns_histogram(prices, ticker), use_container_width=True)
with col_b:
    st.markdown('<div class="section-header">📉 Drawdown from Peak</div>',
                unsafe_allow_html=True)
    st.plotly_chart(drawdown_chart(dd_series, ticker), use_container_width=True)

st.markdown('<div class="section-header">⚡ Cumulative Return vs SPY</div>',
            unsafe_allow_html=True)
st.plotly_chart(
    cumulative_return_chart(prices, bench_df["Close"], ticker),
    use_container_width=True,
)

# ── Metric Glossary ───────────────────────────────────────────────────────────
with st.expander("📖 Metrics Explained (click to expand)"):
    st.markdown("""
| Metric | Formula / Definition | Interpretation |
|--------|---------------------|----------------|
| **CAGR** | (End/Start)^(1/years) − 1 | Annualised growth rate of the investment |
| **Volatility** | Std(daily returns) × √252 | Higher = more price uncertainty |
| **Sharpe Ratio** | (Return − Rf) / Std × √252 | Risk-adjusted return; > 1 is generally good |
| **Sortino Ratio** | (Return − Rf) / Downside Std | Like Sharpe but only penalises downside risk |
| **Max Drawdown** | (Trough − Peak) / Peak | Worst peak-to-trough loss; more negative = worse |
| **Calmar Ratio** | CAGR / |Max Drawdown| | Return per unit of worst loss |
| **Beta** | Cov(asset, SPY) / Var(SPY) | > 1 = more volatile than market; < 1 = more stable |
""")

# ── Raw data table ─────────────────────────────────────────────────────────────
with st.expander("🗃️ Raw OHLCV Data"):
    st.dataframe(
        df.sort_index(ascending=False).style.format({
            "Open": "${:.2f}", "High": "${:.2f}",
            "Low": "${:.2f}", "Close": "${:.2f}",
            "Volume": "{:,.0f}",
        }),
        use_container_width=True,
        height=320,
    )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;font-size:0.78rem;color:#334155;padding:8px;'>"
    "ACC102 Individual Project · Built with Streamlit + yfinance + Plotly · "
    "Data source: Yahoo Finance · For educational purposes only"
    "</div>",
    unsafe_allow_html=True,
)
