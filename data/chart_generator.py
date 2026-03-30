"""Generate charts for the research reports matching TAMS style."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import os
from datetime import datetime

# TAMS color scheme
# TAM Capital brand colors
DARK_BLUE = "#222F62"
LIGHT_BLUE = "#1A6DB6"
TURQUOISE = "#6CB9B6"
GRAY = "#4A4A4A"
SOFT_CARBON = "#B1B3B6"
LIGHT_GRAY = "#F0F0F0"
RED = "#D32F2F"
ORANGE = "#FF9800"
GREEN = TURQUOISE  # Chart accent

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans", "Helvetica"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#CCCCCC",
    "grid.color": "#E0E0E0",
    "grid.linewidth": 0.5,
})


def _save_chart(fig, output_dir: str, name: str) -> str:
    """Save chart to file and return path."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def generate_price_chart(hist: pd.DataFrame, technicals: dict, output_dir: str, ticker: str) -> str:
    """Generate technical price chart with moving averages."""
    if hist.empty:
        return ""

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)

    # Price chart
    dates = hist.index
    ax1.plot(dates, hist["Close"], color=DARK_BLUE, linewidth=1.5, label="Price")

    # Moving averages
    for period, color, label in [(20, GREEN, "MA(20)"), (50, ORANGE, "MA(50)"), (200, RED, "MA(200)")]:
        if len(hist) >= period:
            ma = hist["Close"].rolling(period).mean()
            ax1.plot(dates, ma, color=color, linewidth=1, alpha=0.8, label=label)

    ax1.set_title(f"{ticker} - Technical Price Chart", color=DARK_BLUE, pad=10)
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Price", color=GRAY)

    # Volume chart
    colors = [GREEN if hist["Close"].iloc[i] >= hist["Open"].iloc[i] else RED
              for i in range(len(hist))]
    ax2.bar(dates, hist["Volume"], color=colors, alpha=0.6, width=1)
    ax2.set_ylabel("Volume", color=GRAY)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    return _save_chart(fig, output_dir, "chart_technical")


def generate_revenue_earnings_chart(financials_data: dict, output_dir: str) -> str:
    """Generate revenue and earnings bar chart."""
    # Parse from financial statements if available
    income = financials_data.get("income_statement", {})
    if not income:
        return ""

    try:
        periods = sorted(income.keys())[-4:]  # Last 4 periods
        revenues = []
        net_incomes = []
        labels = []

        for period in periods:
            data = income[period]
            rev = data.get("Total Revenue", data.get("TotalRevenue", 0))
            ni = data.get("Net Income", data.get("NetIncome", 0))
            if rev:
                revenues.append(rev / 1e9)
                net_incomes.append((ni or 0) / 1e9)
                if hasattr(period, "strftime"):
                    labels.append(period.strftime("%Y"))
                else:
                    labels.append(str(period)[:4])
    except Exception:
        return ""

    if not revenues:
        return ""

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    width = 0.35

    bars1 = ax.bar(x - width / 2, revenues, width, label="Revenue", color=DARK_BLUE, alpha=0.9)
    bars2 = ax.bar(x + width / 2, net_incomes, width, label="Net Income", color=GREEN, alpha=0.9)

    ax.set_title("Revenue & Earnings Trend", color=DARK_BLUE, pad=10)
    ax.set_ylabel("Amount (Billions)", color=GRAY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    # Value labels on bars
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                f"{bar.get_height():.1f}B", ha="center", fontsize=8, color=DARK_BLUE)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                f"{bar.get_height():.1f}B", ha="center", fontsize=8, color=GREEN)

    fig.tight_layout()
    return _save_chart(fig, output_dir, "chart_revenue_earnings")


def generate_dividend_chart(dividends: pd.Series, output_dir: str) -> str:
    """Generate dividend history chart."""
    if dividends.empty:
        return ""

    # Group by year
    yearly = dividends.groupby(dividends.index.year).sum()
    if yearly.empty:
        return ""

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(yearly.index.astype(str), yearly.values, color=GREEN, alpha=0.9)

    ax.set_title("Dividend History (Annual)", color=DARK_BLUE, pad=10)
    ax.set_ylabel("Dividend Per Share", color=GRAY)
    ax.grid(True, alpha=0.3, axis="y")

    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{bar.get_height():.2f}", ha="center", fontsize=8, color=GREEN)

    fig.tight_layout()
    return _save_chart(fig, output_dir, "chart_dividend")


def generate_valuation_chart(stock_data: dict, output_dir: str) -> str:
    """Generate valuation comparison chart (stock vs peers)."""
    metrics = []
    stock_vals = []
    peer_vals = []

    pe = stock_data.get("pe_ratio")
    if pe:
        metrics.append("P/E")
        stock_vals.append(pe)
        peer_vals.append(20)  # Generic peer avg

    ev_ebitda = stock_data.get("ev_ebitda")
    if ev_ebitda:
        metrics.append("EV/EBITDA")
        stock_vals.append(ev_ebitda)
        peer_vals.append(12)

    pb = stock_data.get("pb_ratio")
    if pb:
        metrics.append("P/B")
        stock_vals.append(pb)
        peer_vals.append(2.5)

    div_yield = stock_data.get("dividend_yield")
    if div_yield:
        metrics.append("Div Yield %")
        stock_vals.append(div_yield * 100 if div_yield < 1 else div_yield)
        peer_vals.append(3.0)

    if not metrics:
        return ""

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(metrics))
    width = 0.35

    ax.bar(x - width / 2, stock_vals, width, label=stock_data.get("name", "Stock"), color=DARK_BLUE)
    ax.bar(x + width / 2, peer_vals, width, label="Peer Average", color=LIGHT_BLUE, edgecolor=DARK_BLUE)

    ax.set_title("Valuation Comparison vs Peers", color=DARK_BLUE, pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    return _save_chart(fig, output_dir, "chart_valuation")


def generate_all_charts(stock_data: dict, technicals: dict, hist: pd.DataFrame,
                        financials: dict, dividends: pd.Series, output_dir: str) -> dict:
    """Generate all charts and return paths."""
    charts = {}

    path = generate_price_chart(hist, technicals, output_dir, stock_data.get("ticker", ""))
    if path:
        charts["technical"] = path

    path = generate_revenue_earnings_chart(financials, output_dir)
    if path:
        charts["revenue_earnings"] = path

    path = generate_dividend_chart(dividends, output_dir)
    if path:
        charts["dividend"] = path

    path = generate_valuation_chart(stock_data, output_dir)
    if path:
        charts["valuation"] = path

    return charts
