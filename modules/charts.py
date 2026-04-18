"""
charts.py
---------
Plotly chart builders.  Each function returns a plotly Figure object
ready to be passed to st.plotly_chart().
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ── palette ───────────────────────────────────────────────────────────────────
ACCENT   = "#6C63FF"   # purple-blue
POSITIVE = "#22D3A5"   # teal-green
NEGATIVE = "#F87171"   # soft red
MA20     = "#FBBF24"   # amber
MA50     = "#60A5FA"   # sky blue
BG       = "rgba(0,0,0,0)"   # transparent (lets Streamlit theme show through)

LAYOUT_DEFAULTS = dict(
    paper_bgcolor=BG,
    plot_bgcolor="rgba(15,15,25,0.6)",
    font=dict(family="Inter, sans-serif", color="#E2E8F0"),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    hovermode="x unified",
)


def _apply_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(title=dict(text=title, font=dict(size=16, color="#A5B4FC")),
                      **LAYOUT_DEFAULTS)
    return fig


# ── 1. Price + MA + Volume ────────────────────────────────────────────────────

def price_chart(df_ohlcv: pd.DataFrame, ma_df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Two-panel chart:
      - Top: Candlestick with MA20 and MA50 overlays
      - Bottom: Volume bars coloured by daily direction
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_ohlcv.index,
        open=df_ohlcv["Open"],
        high=df_ohlcv["High"],
        low=df_ohlcv["Low"],
        close=df_ohlcv["Close"],
        increasing_line_color=POSITIVE,
        decreasing_line_color=NEGATIVE,
        name="OHLC",
    ), row=1, col=1)

    # MA lines
    fig.add_trace(go.Scatter(
        x=ma_df.index, y=ma_df["MA20"],
        line=dict(color=MA20, width=1.5), name="MA20",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=ma_df.index, y=ma_df["MA50"],
        line=dict(color=MA50, width=1.5), name="MA50",
    ), row=1, col=1)

    # Volume bars
    daily_dir = (df_ohlcv["Close"] >= df_ohlcv["Open"])
    colors = [POSITIVE if d else NEGATIVE for d in daily_dir]
    fig.add_trace(go.Bar(
        x=df_ohlcv.index,
        y=df_ohlcv["Volume"],
        marker_color=colors,
        name="Volume",
        showlegend=False,
        opacity=0.7,
    ), row=2, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, **LAYOUT_DEFAULTS)
    fig.update_layout(title=dict(text=f"{ticker} — Price & Volume",
                                 font=dict(size=16, color="#A5B4FC")))
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1,
                     gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(title_text="Volume", row=2, col=1,
                     gridcolor="rgba(255,255,255,0.05)")
    return fig


# ── 2. Daily Returns Histogram ────────────────────────────────────────────────

def returns_histogram(prices: pd.Series, ticker: str) -> go.Figure:
    """Distribution of daily returns with a KDE overlay."""
    rets = prices.pct_change().dropna() * 100  # in percent

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=rets,
        nbinsx=60,
        marker_color=ACCENT,
        opacity=0.75,
        name="Daily Return %",
    ))

    # KDE via numpy
    from scipy.stats import gaussian_kde
    kde = gaussian_kde(rets)
    x_range = np.linspace(rets.min(), rets.max(), 300)
    kde_vals = kde(x_range) * len(rets) * (rets.max() - rets.min()) / 60

    fig.add_trace(go.Scatter(
        x=x_range, y=kde_vals,
        mode="lines",
        line=dict(color=MA20, width=2),
        name="KDE",
    ))

    # Zero line
    fig.add_vline(x=0, line_color=NEGATIVE, line_dash="dash", line_width=1.5)

    _apply_layout(fig, f"{ticker} — Daily Return Distribution")
    fig.update_xaxes(title_text="Daily Return (%)")
    fig.update_yaxes(title_text="Frequency")
    return fig


# ── 3. Drawdown Chart ─────────────────────────────────────────────────────────

def drawdown_chart(drawdown_series: pd.Series, ticker: str) -> go.Figure:
    """Filled area chart of rolling drawdown."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=drawdown_series.index,
        y=drawdown_series * 100,
        fill="tozeroy",
        fillcolor="rgba(248,113,113,0.20)",
        line=dict(color=NEGATIVE, width=1.5),
        name="Drawdown %",
    ))

    _apply_layout(fig, f"{ticker} — Drawdown from Peak")
    fig.update_yaxes(title_text="Drawdown (%)", ticksuffix="%")
    return fig


# ── 4. Cumulative Return Comparison ──────────────────────────────────────────

def cumulative_return_chart(stock_prices: pd.Series,
                             bench_prices: pd.Series,
                             ticker: str) -> go.Figure:
    """
    Normalised cumulative return of the stock vs SPY benchmark,
    both indexed to 100 at the start of the selected period.
    """
    # Align dates
    aligned = pd.concat(
        [stock_prices.rename("Stock"), bench_prices.rename("SPY")],
        axis=1, join="inner"
    ).dropna()

    norm = aligned / aligned.iloc[0] * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=norm.index, y=norm["Stock"],
        line=dict(color=ACCENT, width=2), name=ticker,
    ))
    fig.add_trace(go.Scatter(
        x=norm.index, y=norm["SPY"],
        line=dict(color="#94A3B8", width=1.5, dash="dot"), name="SPY (benchmark)",
    ))

    fig.add_hline(y=100, line_color="rgba(255,255,255,0.2)", line_dash="dash")

    _apply_layout(fig, f"{ticker} vs SPY — Cumulative Return (base 100)")
    fig.update_yaxes(title_text="Indexed Return")
    return fig
