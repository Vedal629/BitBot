
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import os

# -----------------------------
# Settings
# -----------------------------
START = "2015-01-01"
END = None  # use latest
TICKERS = {"GLD":"Gold (GLD)", "SPY":"S&P 500 (SPY)", "BTC-USD":"Bitcoin (BTC-USD)"}
FEE = 0.001  # 0.10% per notional traded
RISK_FREE = 0.0  # for Sharpe

# -----------------------------
# Data
# -----------------------------
def download_prices(tickers, start=START, end=END):
    df = yf.download(list(tickers.keys()), start=start, end=end, auto_adjust=True, progress=False)["Close"]
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    return df

prices = download_prices(TICKERS, START, END)
prices = prices.dropna()
prices = prices.asfreq("B").fillna(method="ffill")  # business days forward-fill

# Align names
prices = prices[list(TICKERS.keys())]
prices.columns = list(TICKERS.values())

rets = prices.pct_change().fillna(0.0)

# -----------------------------
# Utilities
# -----------------------------
def perf_stats(equity):
    """equity as series of cumulative returns (starting at 1.0)"""
    daily = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = equity.iloc[-1] ** (1/years) - 1 if years > 0 else np.nan
    vol = daily.std() * np.sqrt(252)
    sharpe = (daily.mean() * 252 - RISK_FREE) / (daily.std() * np.sqrt(252)) if daily.std() > 0 else np.nan
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    mdd = dd.min()
    return {
        "CAGR": cagr,
        "Volatility": vol,
        "Sharpe": sharpe,
        "Max Drawdown": mdd
    }

def apply_fees(prev_w, new_w, fee=FEE):
    """Return portfolio turnover (sum abs(delta_w)) and cost factor (1 - fee*turnover)"""
    turnover = np.abs(new_w - prev_w).sum()
    cost_factor = 1 - fee * turnover
    return turnover, max(cost_factor, 0.0)

# -----------------------------
# Strategy A: Equal-Weight, Quarterly Rebalance
# -----------------------------
def strat_equal_weight_quarterly(prices, fee=FEE):
    rets = prices.pct_change().fillna(0.0)
    months = prices.resample("M").last().index
    # quarterly markers
    rebal_dates = [d for i, d in enumerate(months) if (i % 3 == 0)]
    rebal_dates = [d for d in rebal_dates if d in prices.index]

    w = pd.Series(1/len(prices.columns), index=prices.columns)
    prev_w = w.copy()

    equity = pd.Series(index=prices.index, dtype=float)
    equity.iloc[0] = 1.0

    for i in range(1, len(prices.index)):
        date = prices.index[i]
        y = equity.iloc[i-1]

        # Rebalance at quarter-end
        if date in rebal_dates:
            new_w = pd.Series(1/len(prices.columns), index=prices.columns)
            _, cf = apply_fees(prev_w, new_w, fee)
            prev_w = new_w.copy()
        else:
            new_w = prev_w.copy()
            cf = 1.0

        port_ret = (rets.iloc[i] * new_w).sum()
        equity.iloc[i] = y * (1 + port_ret) * cf

        prev_w = new_w

    return equity

# -----------------------------
# Strategy B: 6-Month Momentum (Top-1 = 60%, others 20%/20%), Monthly Rebalance
# -----------------------------
def total_return(prices, lookback_days):
    return prices / prices.shift(lookback_days) - 1.0

def strat_momentum_6m(prices, fee=FEE):
    rets = prices.pct_change().fillna(0.0)
    month_ends = prices.resample("M").last().index
    month_ends = [d for d in month_ends if d in prices.index]

    lookback = 21 * 6  # ~6 months
    mom = total_return(prices, lookback).replace([np.inf, -np.inf], np.nan)

    prev_w = pd.Series(1/len(prices.columns), index=prices.columns)
    equity = pd.Series(index=prices.index, dtype=float)
    equity.iloc[0] = 1.0

    for i in range(1, len(prices.index)):
        date = prices.index[i]
        y = equity.iloc[i-1]

        if date in month_ends and i >= lookback:
            rank = mom.iloc[i].dropna().sort_values(ascending=False)
            if len(rank) < len(prices.columns):
                # if any NaN, fallback to equal weight
                new_w = pd.Series(1/len(prices.columns), index=prices.columns)
            else:
                top = rank.index[0]
                others = [c for c in prices.columns if c != top]
                new_w = pd.Series(0.0, index=prices.columns)
                new_w[top] = 0.60
                for c in others:
                    new_w[c] = 0.20

            _, cf = apply_fees(prev_w, new_w, fee)
            prev_w = new_w.copy()
        else:
            new_w = prev_w.copy()
            cf = 1.0

        port_ret = (rets.iloc[i] * new_w).sum()
        equity.iloc[i] = y * (1 + port_ret) * cf
        prev_w = new_w

    return equity

# -----------------------------
# Strategy C: Risk-Parity (Inverse 60D Vol), Monthly Rebalance, BTC cap 20%
# -----------------------------
def strat_risk_parity(prices, fee=FEE, lookback=60, btc_cap=0.20):
    rets = prices.pct_change().fillna(0.0)
    month_ends = prices.resample("M").last().index
    month_ends = [d for d in month_ends if d in prices.index]

    prev_w = pd.Series(1/len(prices.columns), index=prices.columns)
    equity = pd.Series(index=prices.index, dtype=float)
    equity.iloc[0] = 1.0

    for i in range(1, len(prices.index)):
        date = prices.index[i]
        y = equity.iloc[i-1]

        if date in month_ends and i >= lookback:
            vol = rets.iloc[i-lookback+1:i+1].std() * np.sqrt(252)
            inv_vol = 1.0 / vol.replace(0.0, np.nan)
            if inv_vol.isna().any():
                new_w = pd.Series(1/len(prices.columns), index=prices.columns)
            else:
                w = (inv_vol / inv_vol.sum())
                # cap BTC
                if "Bitcoin (BTC-USD)" in w.index and w["Bitcoin (BTC-USD)"] > btc_cap:
                    excess = w["Bitcoin (BTC-USD)"] - btc_cap
                    w["Bitcoin (BTC-USD)"] = btc_cap
                    # redistribute excess to others proportionally
                    others = [c for c in w.index if c != "Bitcoin (BTC-USD)"]
                    if len(others) > 0:
                        w_others = w[others]
                        w_others = w_others / w_others.sum()
                        w[others] = w[others] + excess * w_others
                new_w = w

            _, cf = apply_fees(prev_w, new_w, fee)
            prev_w = new_w.copy()
        else:
            new_w = prev_w.copy()
            cf = 1.0

        port_ret = (rets.iloc[i] * new_w).sum()
        equity.iloc[i] = y * (1 + port_ret) * cf
        prev_w = new_w

    return equity

# -----------------------------
# Run Backtests
# -----------------------------
eq_A = strat_equal_weight_quarterly(prices, FEE)
eq_B = strat_momentum_6m(prices, FEE)
eq_C = strat_risk_parity(prices, FEE, lookback=60, btc_cap=0.20)

equities = pd.DataFrame({
    "A_EqualWeight_Q": eq_A,
    "B_Momentum6M": eq_B,
    "C_RiskParity": eq_C
}).dropna()

# -----------------------------
# Performance Table
# -----------------------------
summary = {}
for col in equities.columns:
    summary[col] = perf_stats(equities[col])

summary_df = pd.DataFrame(summary).T
summary_df = summary_df[["CAGR","Volatility","Sharpe","Max Drawdown"]]
summary_df = summary_df.sort_values("CAGR", ascending=False)

print("\n=== Performance Summary (2015-~) ===")
print(summary_df.to_string(float_format=lambda x: f"{x:,.2%}"))

# Save
save_dir = r"C:\Users\lsh06\PycharmProjects\BitBot\or"
os.makedirs(save_dir, exist_ok=True)  # 폴더 없으면 생성

summary_df.to_csv(os.path.join(save_dir, "3asset_summary.csv"), index=False)
equities.to_csv(os.path.join(save_dir, "3asset_daily_equity.csv"), index=False)

# -----------------------------
# Plot Equity Curves
# -----------------------------
plt.figure(figsize=(10,6))
(equities / equities.iloc[0]).plot(ax=plt.gca())
plt.title("3-Asset Strategies: Equity Curves (Start=1.0)")
plt.ylabel("Growth of 1")
plt.xlabel("Date")
plt.tight_layout()
plt.show()
