"""
Interactive Plotly technical charts for Streamlit stock research app.
Provides candlestick, RSI, MACD, and comparison charts with TAM Liquid Glass theming.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# TAM Liquid Glass color palette and layout constants
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
    "muted": "#8B949E",
    "grid": "rgba(30,41,59,0.5)",
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0C1220",
    font=dict(family="Inter, sans-serif", color="#E6EDF3"),
    xaxis=dict(gridcolor="rgba(30,41,59,0.5)", showgrid=True),
    yaxis=dict(gridcolor="rgba(30,41,59,0.5)", showgrid=True),
    margin=dict(l=50, r=20, t=40, b=30),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    hovermode="x unified",
)


def calculate_technical_indicators(hist: pd.DataFrame) -> dict:
    """
    Calculate technical indicators for a given price history DataFrame.

    Args:
        hist: DataFrame with OHLCV data from yfinance (DatetimeIndex)

    Returns:
        Dictionary containing indicator arrays:
        - ma20, ma50, ma200: Moving averages
        - rsi: Relative Strength Index (14)
        - macd: MACD line
        - macd_signal: MACD signal line
        - macd_histogram: MACD histogram
        - bb_upper, bb_middle, bb_lower: Bollinger Bands
        - fib_levels: Fibonacci retracement levels
    """
    df = hist.copy()
    indicators = {}

    # Moving Averages
    indicators["ma20"] = df["Close"].rolling(window=20).mean()
    indicators["ma50"] = df["Close"].rolling(window=50).mean()
    indicators["ma200"] = df["Close"].rolling(window=200).mean()

    # RSI (14-period)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    indicators["rsi"] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    indicators["macd"] = ema12 - ema26
    indicators["macd_signal"] = indicators["macd"].ewm(span=9, adjust=False).mean()
    indicators["macd_histogram"] = indicators["macd"] - indicators["macd_signal"]

    # Bollinger Bands (20, 2)
    sma20 = df["Close"].rolling(window=20).mean()
    std20 = df["Close"].rolling(window=20).std()
    indicators["bb_middle"] = sma20
    indicators["bb_upper"] = sma20 + (std20 * 2)
    indicators["bb_lower"] = sma20 - (std20 * 2)

    # Fibonacci Levels (based on 52-week high/low)
    if len(df) >= 252:
        year_high = df["High"].tail(252).max()
        year_low = df["Low"].tail(252).min()
    else:
        year_high = df["High"].max()
        year_low = df["Low"].min()

    diff = year_high - year_low
    indicators["fib_levels"] = {
        "0.0": year_low,
        "0.236": year_low + diff * 0.236,
        "0.382": year_low + diff * 0.382,
        "0.5": year_low + diff * 0.5,
        "0.618": year_low + diff * 0.618,
        "0.786": year_low + diff * 0.786,
        "1.0": year_high,
    }

    return indicators


def generate_candlestick_chart(
    hist: pd.DataFrame, ticker: str, indicators: dict = None
) -> go.Figure:
    """
    Generate an interactive candlestick chart with volume subplot.

    Args:
        hist: DataFrame with OHLCV data from yfinance (DatetimeIndex)
        ticker: Stock ticker symbol (for title)
        indicators: Optional dict of technical indicators from calculate_technical_indicators()

    Returns:
        Plotly Figure with candlestick chart, volume bars, and optional indicators
    """
    df = hist.copy()

    # Create subplots: candlestick (larger) and volume (smaller)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{ticker} Price", "Volume"),
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="OHLC",
            increasing_line_color=TAM_COLORS["green"],
            decreasing_line_color=TAM_COLORS["red"],
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>"
            "Open: $%{open:.2f}<br>"
            "High: $%{high:.2f}<br>"
            "Low: $%{low:.2f}<br>"
            "Close: $%{close:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Volume bars
    colors = [
        TAM_COLORS["green"] if df["Close"].iloc[i] >= df["Open"].iloc[i] else TAM_COLORS["red"]
        for i in range(len(df))
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            marker=dict(color=colors, opacity=0.6),
            name="Volume",
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Volume: %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Add technical indicators if provided
    if indicators:
        # MA20
        if "ma20" in indicators and indicators["ma20"] is not None:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=indicators["ma20"],
                    name="MA20",
                    line=dict(color=TAM_COLORS["orange"], width=1.5),
                    hovertemplate="<b>MA20</b><br>%{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
            )

        # MA50
        if "ma50" in indicators and indicators["ma50"] is not None:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=indicators["ma50"],
                    name="MA50",
                    line=dict(color=TAM_COLORS["turquoise"], width=1.5),
                    hovertemplate="<b>MA50</b><br>%{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
            )

        # MA200
        if "ma200" in indicators and indicators["ma200"] is not None:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=indicators["ma200"],
                    name="MA200",
                    line=dict(color=TAM_COLORS["blue"], width=1.5),
                    hovertemplate="<b>MA200</b><br>%{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
            )

        # Bollinger Bands
        if all(k in indicators for k in ["bb_upper", "bb_middle", "bb_lower"]):
            bb_upper = indicators["bb_upper"]
            bb_middle = indicators["bb_middle"]
            bb_lower = indicators["bb_lower"]

            # Upper band
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=bb_upper,
                    name="BB Upper",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )

            # Fill between upper and middle
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=bb_middle,
                    name="Bollinger Bands",
                    fill="tonexty",
                    fillcolor="rgba(108, 185, 182, 0.1)",
                    line=dict(width=0),
                    showlegend=True,
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )

            # Lower band
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=bb_lower,
                    name="BB Lower",
                    fill="tonexty",
                    fillcolor="rgba(108, 185, 182, 0.1)",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )

    # Update layout with TAM theme
    fig.update_layout(
        title=dict(
            text=f"{ticker} Technical Analysis",
            font=dict(size=16, color=TAM_COLORS["text"]),
            x=0.5,
            xanchor="center",
        ),
        **CHART_LAYOUT,
        height=700,
    )

    # Update x-axes
    fig.update_xaxes(
        rangeslider=dict(visible=False),
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=1, label="1M", step="month"),
                    dict(count=3, label="3M", step="month"),
                    dict(count=6, label="6M", step="month"),
                    dict(count=1, label="1Y", step="year"),
                    dict(count=5, label="5Y", step="year"),
                    dict(step="all", label="MAX"),
                ]
            ),
            bgcolor=TAM_COLORS["card"],
            activecolor=TAM_COLORS["blue"],
            font=dict(color=TAM_COLORS["text"]),
        ),
        row=1,
    )

    # Update y-axes
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    # Update legend
    fig.update_layout(legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.3)"))

    return fig


def generate_rsi_chart(hist: pd.DataFrame) -> go.Figure:
    """
    Generate an RSI (14-period) chart with overbought/oversold zones.

    Args:
        hist: DataFrame with OHLCV data from yfinance (DatetimeIndex)

    Returns:
        Plotly Figure with RSI chart
    """
    indicators = calculate_technical_indicators(hist)
    rsi = indicators["rsi"]

    fig = go.Figure()

    # RSI line
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=rsi,
            name="RSI (14)",
            line=dict(color=TAM_COLORS["blue"], width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>RSI: %{y:.2f}<extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(26, 109, 182, 0.1)",
        )
    )

    # Overbought line (70)
    fig.add_hline(
        y=70,
        line_dash="dash",
        line_color=TAM_COLORS["red"],
        annotation_text="Overbought (70)",
        annotation_position="right",
        annotation_font=dict(color=TAM_COLORS["red"], size=10),
    )

    # Oversold line (30)
    fig.add_hline(
        y=30,
        line_dash="dash",
        line_color=TAM_COLORS["green"],
        annotation_text="Oversold (30)",
        annotation_position="right",
        annotation_font=dict(color=TAM_COLORS["green"], size=10),
    )

    # Midline (50)
    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color=TAM_COLORS["muted"],
        annotation_text="Neutral (50)",
        annotation_position="right",
        annotation_font=dict(color=TAM_COLORS["muted"], size=10),
    )

    # Add overbought/oversold background zones
    fig.add_vrect(
        x0=hist.index[0],
        x1=hist.index[-1],
        y0=70,
        y1=100,
        fillcolor=TAM_COLORS["red"],
        opacity=0.1,
        layer="below",
        line_width=0,
        annotation_text="Overbought",
        annotation_position="top left",
        annotation_font=dict(color=TAM_COLORS["red"], size=9),
    )

    fig.add_vrect(
        x0=hist.index[0],
        x1=hist.index[-1],
        y0=0,
        y1=30,
        fillcolor=TAM_COLORS["green"],
        opacity=0.1,
        layer="below",
        line_width=0,
        annotation_text="Oversold",
        annotation_position="bottom left",
        annotation_font=dict(color=TAM_COLORS["green"], size=9),
    )

    fig.update_layout(
        title="Relative Strength Index (RSI)",
        yaxis_title="RSI",
        **CHART_LAYOUT,
        height=400,
        yaxis=dict(range=[0, 100], **CHART_LAYOUT["yaxis"]),
    )

    fig.update_xaxes(rangeslider=dict(visible=False))

    return fig


def generate_macd_chart(hist: pd.DataFrame) -> go.Figure:
    """
    Generate a MACD chart with signal line and histogram.

    Args:
        hist: DataFrame with OHLCV data from yfinance (DatetimeIndex)

    Returns:
        Plotly Figure with MACD chart
    """
    indicators = calculate_technical_indicators(hist)
    macd = indicators["macd"]
    macd_signal = indicators["macd_signal"]
    macd_histogram = indicators["macd_histogram"]

    fig = go.Figure()

    # MACD histogram (colored green/red)
    colors = [
        TAM_COLORS["green"] if val >= 0 else TAM_COLORS["red"]
        for val in macd_histogram
    ]
    fig.add_trace(
        go.Bar(
            x=hist.index,
            y=macd_histogram,
            name="MACD Histogram",
            marker=dict(color=colors, opacity=0.6),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Histogram: %{y:.4f}<extra></extra>",
        )
    )

    # MACD line
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=macd,
            name="MACD",
            line=dict(color=TAM_COLORS["blue"], width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>MACD: %{y:.4f}<extra></extra>",
        )
    )

    # Signal line
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=macd_signal,
            name="Signal",
            line=dict(color=TAM_COLORS["orange"], width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Signal: %{y:.4f}<extra></extra>",
        )
    )

    # Zero line
    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color=TAM_COLORS["muted"],
        line_width=1,
    )

    fig.update_layout(
        title="MACD (12, 26, 9)",
        yaxis_title="MACD",
        **CHART_LAYOUT,
        height=400,
    )

    fig.update_xaxes(rangeslider=dict(visible=False))

    return fig


def generate_comparison_chart(
    tickers_data: dict, normalized: bool = True
) -> go.Figure:
    """
    Generate a multi-ticker comparison chart.

    Args:
        tickers_data: Dictionary mapping ticker symbols to DataFrames
                     (each with DatetimeIndex and Close column)
        normalized: If True, show percentage change from start date.
                   If False, show absolute prices.

    Returns:
        Plotly Figure with overlaid ticker comparisons
    """
    colors_list = [
        TAM_COLORS["blue"],
        TAM_COLORS["turquoise"],
        TAM_COLORS["green"],
        TAM_COLORS["red"],
        TAM_COLORS["orange"],
        TAM_COLORS["deep"],
    ]

    fig = go.Figure()

    for idx, (ticker, df) in enumerate(tickers_data.items()):
        color = colors_list[idx % len(colors_list)]

        if normalized:
            # Calculate percentage change from first price
            first_price = df["Close"].iloc[0]
            close_data = ((df["Close"] - first_price) / first_price) * 100
            y_label = "% Change"
            hover_template = (
                f"<b>{ticker}</b><br>"
                "%{x|%Y-%m-%d}<br>"
                "% Change: %{y:.2f}%<extra></extra>"
            )
        else:
            # Use absolute prices
            close_data = df["Close"]
            y_label = "Price (USD)"
            hover_template = (
                f"<b>{ticker}</b><br>"
                "%{x|%Y-%m-%d}<br>"
                "Price: $%{y:.2f}<extra></extra>"
            )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=close_data,
                name=ticker,
                line=dict(color=color, width=2.5),
                hovertemplate=hover_template,
            )
        )

    title = "Stock Price Comparison"
    if normalized:
        title += " (% Change from Start)"

    fig.update_layout(
        title=title,
        yaxis_title=y_label,
        **CHART_LAYOUT,
        height=500,
    )

    fig.update_xaxes(rangeslider=dict(visible=False))

    # Add zero line if normalized
    if normalized:
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color=TAM_COLORS["muted"],
            line_width=1,
        )

    return fig
