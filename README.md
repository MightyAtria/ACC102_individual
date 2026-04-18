# 📊 Financial Analysis Dashboard

> An interactive, beginner-level quantitative finance web app built with **Streamlit**, **yfinance**, and **Plotly**.

---

## 🚀 Live Demo

*(Deploy to Streamlit Cloud and paste your URL here)*

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **Ticker Input** | Enter any US stock symbol (NYSE / NASDAQ) |
| **Flexible Time Range** | Preset (1M–5Y) or custom date picker |
| **Real-time Data** | Pulled live from Yahoo Finance via `yfinance` |
| **Quantitative Metrics** | CAGR · Sharpe Ratio · Sortino Ratio · Max Drawdown · Volatility · Calmar Ratio · Beta |
| **Interactive Charts** | Candlestick + Volume · Return Distribution · Drawdown Curve · Cumulative Return vs SPY |
| **Adjustable Risk-Free Rate** | Slider from 0 % to 10 % for Sharpe / Sortino tuning |
| **Metrics Glossary** | In-app explanation of every metric |

---

## 📂 Project Structure

```
ACC102_Dashboard/
├── app.py                   # Streamlit main application
├── modules/
│   ├── data_fetcher.py      # yfinance data retrieval
│   ├── metrics.py           # Quantitative metrics engine
│   └── charts.py            # Plotly interactive chart builders
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation & Running Locally

### Prerequisites
- Python 3.9 or higher
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/ACC102_Dashboard.git
cd ACC102_Dashboard

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run app.py
```

The app will open automatically at **http://localhost:8501**

---

## 📈 Metrics Explained

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **CAGR** | (End/Start)^(1/years) − 1 | Annualised growth rate |
| **Annualised Volatility** | σ_daily × √252 | Price uncertainty |
| **Sharpe Ratio** | (R − Rf) / σ × √252 | Return per unit of total risk; > 1 is good |
| **Sortino Ratio** | (R − Rf) / σ_downside × √252 | Only penalises downside risk |
| **Max Drawdown** | (Trough − Peak) / Peak | Worst historical loss from a peak |
| **Calmar Ratio** | CAGR / \|Max Drawdown\| | Return per unit of worst loss |
| **Beta** | Cov(stock, SPY) / Var(SPY) | Sensitivity to market movements |

---

## 🛠️ Tech Stack

- [Streamlit](https://streamlit.io/) — Web app framework
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data
- [Plotly](https://plotly.com/python/) — Interactive charts
- [Pandas](https://pandas.pydata.org/) / [NumPy](https://numpy.org/) — Data processing
- [SciPy](https://scipy.org/) — KDE for return distribution

---

## 📝 Disclaimer

This project is created for **educational purposes only** as part of ACC102.
It does not constitute financial advice. All data is sourced from Yahoo Finance.

---

## 👤 Author

**Yurong Wu** — ACC102 Individual Project
