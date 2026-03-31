"""Peer comparison and benchmarking for Saudi equities (Tadawul).

Provides sector classification, peer identification, metrics fetching,
ranking calculations, and interactive visualizations for peer comparison
analysis on the Saudi stock exchange.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Optional, Tuple, List, Dict

# TAM Liquid Glass color palette
TAM_COLORS = {
    "deep": "#222F62",
    "blue": "#1A6DB6",
    "turquoise": "#6CB9B6",
    "green": "#22C55E",
    "red": "#EF4444",
    "orange": "#F59E0B",
    "bg": "#070B14",
    "card": "#0C1220",
    "text": "#E6EDF3",
    "text2": "#8B949E",
    "border": "rgba(108,185,182,0.08)",
    "glass": "rgba(34,47,98,0.12)",
}

# Tadawul sector classification with major companies
TADAWUL_SECTORS = {
    "banks": [
        ("1120.SR", "Al Rajhi Bank"),
        ("1180.SR", "SNB"),
        ("1010.SR", "Riyad Bank"),
        ("1150.SR", "Alinma Bank"),
        ("1050.SR", "BSF"),
    ],
    "petrochemicals": [
        ("2010.SR", "SABIC"),
        ("2020.SR", "SABIC AN"),
        ("2350.SR", "Saudi Kayan"),
        ("2060.SR", "Nat. Industrialization"),
        ("2250.SR", "Maaden"),
    ],
    "telecom": [
        ("7010.SR", "STC"),
        ("7020.SR", "Etihad Etisalat"),
        ("7030.SR", "Zain KSA"),
    ],
    "energy": [
        ("2222.SR", "Saudi Aramco"),
        ("4030.SR", "Bahri"),
        ("2030.SR", "Sarco"),
    ],
    "retail": [
        ("4001.SR", "Petromin"),
        ("4200.SR", "Aldawaa"),
        ("3060.SR", "United Electronics"),
        ("2280.SR", "Almarai"),
    ],
    "healthcare": [
        ("4002.SR", "Mouwasat"),
        ("4004.SR", "Dallah Healthcare"),
        ("4007.SR", "SPIMACO"),
    ],
    "realestate": [
        ("4300.SR", "Dar Al Arkan"),
        ("4310.SR", "Jabal Omar"),
        ("4320.SR", "Emaar Economic City"),
    ],
    "cement": [
        ("3010.SR", "Saudi Cement"),
        ("3020.SR", "Yamama Cement"),
        ("3030.SR", "Saudi White Cement"),
    ],
}


def get_sector_for_ticker(ticker: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get the sector key and name for a given ticker.

    Args:
        ticker: Stock ticker symbol (e.g., '1120.SR')

    Returns:
        Tuple of (sector_key, sector_name) or (None, None) if not found
    """
    for sector_key, companies in TADAWUL_SECTORS.items():
        for tick, name in companies:
            if tick.upper() == ticker.upper():
                return (sector_key, sector_key.replace("_", " ").title())
    return (None, None)


def get_peers(ticker: str, max_peers: int = 8) -> List[Tuple[str, str]]:
    """
    Get peer companies in the same sector for a given ticker.

    Args:
        ticker: Stock ticker symbol (e.g., '1120.SR')
        max_peers: Maximum number of peers to return (default 8)

    Returns:
        List of (ticker, company_name) tuples for companies in the same sector
    """
    sector_key, _ = get_sector_for_ticker(ticker)

    if sector_key is None:
        return []

    sector_companies = TADAWUL_SECTORS[sector_key]

    # Filter out the target ticker and return up to max_peers
    peers = [
        (tick, name)
        for tick, name in sector_companies
        if tick.upper() != ticker.upper()
    ]

    return peers[:max_peers]


def fetch_peer_metrics(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch key metrics for all tickers using yfinance.

    Args:
        tickers: List of ticker symbols

    Returns:
        DataFrame with columns:
        - Ticker, Name, Price, Market Cap, P/E, P/B, EV/EBITDA, ROE, ROA,
          Debt/Equity, Dividend Yield, Revenue Growth, Profit Margin,
          Current Ratio, Beta, 52W Return
    """
    data = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}

            # Fetch historical data for 52W return calculation
            hist = stock.history(period="1y")
            price_52w_ago = None
            if len(hist) > 0:
                price_52w_ago = hist["Close"].iloc[0]

            current_price = info.get("currentPrice") or info.get(
                "regularMarketPrice"
            )

            # Calculate 52W return
            ret_52w = None
            if current_price and price_52w_ago:
                ret_52w = ((current_price - price_52w_ago) / price_52w_ago) * 100

            # Get beta
            beta = info.get("beta")

            # Get financial metrics
            market_cap = info.get("marketCap")
            pe_ratio = info.get("trailingPE")
            pb_ratio = info.get("priceToBook")
            ev_ebitda = info.get("enterpriseToEbitda")
            roe = info.get("returnOnEquity")
            roa = None  # Not directly available in yfinance
            debt_to_equity = info.get("debtToEquity")
            dividend_yield = info.get("dividendYield")
            revenue_growth = None  # Requires financial statements
            profit_margin = info.get("profitMargins")
            current_ratio = info.get("currentRatio")

            row = {
                "Ticker": ticker,
                "Name": info.get("longName") or info.get("shortName", ticker),
                "Price": current_price,
                "Market Cap": market_cap,
                "P/E": pe_ratio,
                "P/B": pb_ratio,
                "EV/EBITDA": ev_ebitda,
                "ROE": roe,
                "ROA": roa,
                "Debt/Equity": debt_to_equity,
                "Dividend Yield": dividend_yield,
                "Revenue Growth": revenue_growth,
                "Profit Margin": profit_margin,
                "Current Ratio": current_ratio,
                "Beta": beta,
                "52W Return": ret_52w,
            }

            data.append(row)

        except Exception as e:
            # Log error and continue with next ticker
            print(f"Error fetching data for {ticker}: {str(e)}")
            continue

    return pd.DataFrame(data)


def calculate_peer_rankings(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate rankings for each metric column.

    For each metric, rank tickers (1=best, N=worst).
    "Best" depends on metric:
    - Higher is better: ROE, ROA, margins, growth, dividend yield, current ratio, 52W return, Beta (inverse)
    - Lower is better: P/E, P/B, EV/EBITDA, Debt/Equity

    Args:
        metrics_df: DataFrame with metrics from fetch_peer_metrics

    Returns:
        DataFrame with rank columns alongside value columns
    """
    rankings_df = metrics_df.copy()

    # Define which metrics are "higher is better"
    higher_is_better = {
        "ROE",
        "ROA",
        "Profit Margin",
        "Revenue Growth",
        "Dividend Yield",
        "Current Ratio",
        "52W Return",
    }

    # Define which metrics are "lower is better"
    lower_is_better = {"P/E", "P/B", "EV/EBITDA", "Debt/Equity"}

    # Beta: lower is better (less volatile)
    beta_is_lower_better = {"Beta"}

    metric_columns = [
        "Price",
        "Market Cap",
        "P/E",
        "P/B",
        "EV/EBITDA",
        "ROE",
        "ROA",
        "Debt/Equity",
        "Dividend Yield",
        "Revenue Growth",
        "Profit Margin",
        "Current Ratio",
        "Beta",
        "52W Return",
    ]

    for metric in metric_columns:
        if metric not in metrics_df.columns:
            continue

        # Create ranking column
        rank_col = f"{metric} Rank"

        if metric in higher_is_better:
            # Higher is better: rank descending (highest value = rank 1)
            rankings_df[rank_col] = (
                metrics_df[metric].rank(method="min", na_option="bottom", ascending=False).astype("Int64")
            )
        elif metric in lower_is_better:
            # Lower is better: rank ascending (lowest value = rank 1)
            rankings_df[rank_col] = (
                metrics_df[metric].rank(method="min", na_option="bottom", ascending=True).astype("Int64")
            )
        elif metric in beta_is_lower_better:
            # Lower beta is better: rank ascending
            rankings_df[rank_col] = (
                metrics_df[metric].rank(method="min", na_option="bottom", ascending=True).astype("Int64")
            )
        else:
            # Default to higher is better
            rankings_df[rank_col] = (
                metrics_df[metric].rank(method="min", na_option="bottom", ascending=False).astype("Int64")
            )

    return rankings_df


def generate_peer_heatmap(
    metrics_df: pd.DataFrame,
    rankings_df: pd.DataFrame,
    highlight_ticker: str = None,
) -> go.Figure:
    """
    Generate an interactive Plotly heatmap for peer comparison.

    Rows are tickers, columns are metrics. Color scale based on rankings:
    green (top quartile) to red (bottom quartile). Target ticker highlighted.

    Args:
        metrics_df: DataFrame with metrics
        rankings_df: DataFrame with rankings from calculate_peer_rankings
        highlight_ticker: Ticker to highlight with border/different styling

    Returns:
        Plotly Figure object
    """
    if metrics_df.empty or rankings_df.empty:
        return go.Figure().add_annotation(text="No data available")

    # Get metric columns (exclude Ticker and Name)
    metric_columns = [
        col for col in metrics_df.columns if col not in ["Ticker", "Name"]
    ]

    # Build color matrix based on rankings
    tickers = metrics_df["Ticker"].tolist()
    names = metrics_df["Name"].tolist()

    z_values = []
    hover_texts = []

    for idx, ticker in enumerate(tickers):
        row_values = []
        row_hovers = []

        for metric in metric_columns:
            rank_col = f"{metric} Rank"

            if rank_col in rankings_df.columns:
                rank = rankings_df.iloc[idx][rank_col]
                value = metrics_df.iloc[idx][metric]

                if pd.isna(rank):
                    row_values.append(None)
                    row_hovers.append(f"{metric}<br>N/A")
                else:
                    # Normalize rank to 0-1 scale (1=best, n=worst)
                    max_rank = rankings_df[rank_col].max()
                    normalized = 1 - (rank / max_rank)
                    row_values.append(normalized)

                    # Format value for hover
                    if isinstance(value, float):
                        formatted_val = f"{value:.2f}" if not pd.isna(value) else "N/A"
                    else:
                        formatted_val = str(value) if not pd.isna(value) else "N/A"

                    row_hovers.append(
                        f"{metric}<br>Value: {formatted_val}<br>Rank: {int(rank)}/{int(max_rank)}"
                    )
            else:
                row_values.append(None)
                row_hovers.append(f"{metric}<br>N/A")

        z_values.append(row_values)
        hover_texts.append(row_hovers)

    # Create figure
    fig = go.Figure()

    # Add heatmap with custom colors
    fig.add_trace(
        go.Heatmap(
            z=z_values,
            x=metric_columns,
            y=[f"{tick}<br>{name}" for tick, name in zip(tickers, names)],
            colorscale=[
                [0, TAM_COLORS["red"]],
                [0.33, TAM_COLORS["orange"]],
                [0.67, "#FFD700"],
                [1, TAM_COLORS["green"]],
            ],
            hovertext=hover_texts,
            hoverinfo="text",
            colorbar=dict(
                title="Rank<br>Percentile",
                thickness=15,
                len=0.7,
                x=1.02,
                tickvals=[0, 0.5, 1],
                ticktext=["Bottom", "Mid", "Top"],
            ),
            showscale=True,
            hoverongaps=False,
        )
    )

    # Highlight target ticker if provided
    if highlight_ticker and highlight_ticker in tickers:
        highlight_idx = tickers.index(highlight_ticker)
        # Add a shape to highlight the row
        y_pos = len(tickers) - highlight_idx - 0.5

        fig.add_shape(
            type="rect",
            x0=-0.5,
            x1=len(metric_columns) - 0.5,
            y0=y_pos - 0.5,
            y1=y_pos + 0.5,
            line=dict(color=TAM_COLORS["turquoise"], width=3),
            fillcolor="rgba(0,0,0,0)",
            layer="above",
        )

    # Update layout
    fig.update_layout(
        title=dict(
            text="Peer Comparison Heatmap",
            x=0.5,
            xanchor="center",
            font=dict(size=20, color=TAM_COLORS["text"]),
        ),
        xaxis=dict(
            side="bottom",
            tickangle=-45,
            tickfont=dict(size=11, color=TAM_COLORS["text2"]),
        ),
        yaxis=dict(tickfont=dict(size=11, color=TAM_COLORS["text2"])),
        paper_bgcolor=TAM_COLORS["bg"],
        plot_bgcolor=TAM_COLORS["card"],
        font=dict(family="Inter, sans-serif", color=TAM_COLORS["text"]),
        width=1200,
        height=600,
        margin=dict(l=200, r=100, t=80, b=120),
        hovermode="closest",
    )

    return fig


def generate_peer_comparison_table(
    metrics_df: pd.DataFrame,
    rankings_df: pd.DataFrame,
    highlight_ticker: str = None,
) -> str:
    """
    Generate an HTML string for a styled peer comparison table.

    Uses glass card styling with TAM colors. Highlighted row for target ticker.
    Color-coded cells: green for top quartile, yellow for mid, red for bottom.

    Args:
        metrics_df: DataFrame with metrics
        rankings_df: DataFrame with rankings
        highlight_ticker: Ticker to highlight

    Returns:
        HTML string for the styled table
    """
    if metrics_df.empty:
        return "<p>No data available</p>"

    # Select key metrics to display
    display_columns = [
        "Ticker",
        "Name",
        "Price",
        "Market Cap",
        "P/E",
        "P/B",
        "ROE",
        "ROA",
        "Profit Margin",
        "Dividend Yield",
        "Beta",
        "52W Return",
    ]

    # Filter to columns that exist
    display_cols = [col for col in display_columns if col in metrics_df.columns]

    html = """
    <style>
        .peer-table-container {
            background: rgba(34, 47, 98, 0.12);
            border: 1px solid rgba(108, 185, 182, 0.08);
            border-radius: 12px;
            padding: 20px;
            overflow-x: auto;
        }
        .peer-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Inter', sans-serif;
            background: rgba(12, 18, 32, 0.8);
        }
        .peer-table th {
            background: rgba(34, 47, 98, 0.3);
            color: #E6EDF3;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid rgba(108, 185, 182, 0.15);
            font-size: 13px;
        }
        .peer-table td {
            padding: 12px 8px;
            color: #E6EDF3;
            border-bottom: 1px solid rgba(108, 185, 182, 0.08);
            font-size: 13px;
        }
        .peer-table tr:hover {
            background: rgba(108, 185, 182, 0.05);
        }
        .peer-table tr.highlight {
            background: rgba(108, 185, 182, 0.15);
            border-left: 4px solid #6CB9B6;
        }
        .peer-table tr.highlight:hover {
            background: rgba(108, 185, 182, 0.25);
        }
        .ticker-col {
            font-weight: 600;
            color: #1A6DB6;
        }
        .cell-top {
            background: rgba(34, 197, 94, 0.15);
            color: #86EFAC;
        }
        .cell-mid {
            background: rgba(245, 158, 11, 0.1);
            color: #FCD34D;
        }
        .cell-bottom {
            background: rgba(239, 68, 68, 0.15);
            color: #FCA5A5;
        }
        .cell-neutral {
            background: transparent;
        }
    </style>
    <div class="peer-table-container">
        <table class="peer-table">
            <thead>
                <tr>
    """

    # Add header
    for col in display_cols:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    # Add rows
    for idx, row in metrics_df.iterrows():
        ticker = row["Ticker"]
        row_class = "highlight" if ticker == highlight_ticker else ""
        html += f'<tr class="{row_class}">'

        for col in display_cols:
            value = row[col]

            # Determine cell styling based on ranking
            cell_class = "cell-neutral"
            if col not in ["Ticker", "Name", "Price"]:
                rank_col = f"{col} Rank"
                if rank_col in rankings_df.columns:
                    rank_value = rankings_df.iloc[idx][rank_col]
                    max_rank = rankings_df[rank_col].max()

                    if pd.notna(rank_value) and pd.notna(max_rank):
                        # Determine quartile
                        percentile = rank_value / max_rank

                        if percentile <= 0.25:
                            cell_class = "cell-top"
                        elif percentile <= 0.75:
                            cell_class = "cell-mid"
                        else:
                            cell_class = "cell-bottom"

            # Format ticker specially
            if col == "Ticker":
                html += f'<td class="ticker-col {cell_class}">{value}</td>'
            else:
                # Format numeric values
                if isinstance(value, float):
                    if col == "Price":
                        formatted = f"{value:.2f}"
                    elif col in ["P/E", "P/B", "Beta"]:
                        formatted = f"{value:.2f}"
                    elif col in ["ROE", "ROA", "Profit Margin", "Dividend Yield", "52W Return"]:
                        formatted = f"{value:.2%}" if value < 10 else f"{value:.2f}%"
                    else:
                        formatted = f"{value:.2f}"
                elif col == "Market Cap" and isinstance(value, (int, float)):
                    # Format market cap in billions
                    if value >= 1e9:
                        formatted = f"${value/1e9:.1f}B"
                    elif value >= 1e6:
                        formatted = f"${value/1e6:.1f}M"
                    else:
                        formatted = str(value)
                else:
                    formatted = str(value) if pd.notna(value) else "N/A"

                html += f'<td class="{cell_class}">{formatted}</td>'

        html += "</tr>"

    html += """
            </tbody>
        </table>
    </div>
    """

    return html
