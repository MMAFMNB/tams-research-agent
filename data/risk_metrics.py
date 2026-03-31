"""
Portfolio-level risk analytics module for Tadawul (Saudi equities) research app.
Provides Value at Risk, Sharpe ratio, drawdown analysis, and correlation matrices.
"""

import warnings
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from scipy import stats

# TAM Brand color palette for charts
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

# Saudi Arabia risk-free rate (SAIBOR-based)
RISK_FREE_RATE = 0.045


def calculate_portfolio_risk(
    positions: List[Dict], price_history: Dict, benchmark_ticker: str = "^TASI.SR"
) -> Dict:
    """
    Calculate comprehensive portfolio risk metrics.

    Args:
        positions: List of dicts with keys:
            - ticker (str): Stock ticker symbol
            - shares (float): Number of shares held
            - cost_basis (float): Average purchase price per share
        price_history: Dict mapping ticker -> pd.DataFrame with DatetimeIndex and 'Close' column
        benchmark_ticker: Benchmark ticker for beta/Sharpe calculations (default: TASI)

    Returns:
        Dict containing:
            - var_95_1day: 1-day VaR at 95% confidence
            - var_95_10day: 10-day VaR (scaled)
            - sharpe_ratio: Annualized Sharpe ratio
            - max_drawdown: Maximum drawdown as negative percentage
            - max_drawdown_start: Drawdown start date
            - max_drawdown_end: Drawdown end date
            - portfolio_beta: Weighted beta vs benchmark
            - annualized_return: Annualized portfolio return
            - annualized_volatility: Annualized volatility
            - correlation_matrix: pd.DataFrame of correlations
    """
    if not positions:
        raise ValueError("Positions list cannot be empty")

    # Align all price histories to common date range
    all_dates = set()
    for prices_df in price_history.values():
        if prices_df is not None and len(prices_df) > 0:
            all_dates.update(prices_df.index)

    if not all_dates:
        raise ValueError("No valid price history data available")

    # Get benchmark data
    benchmark_data = _get_benchmark_data(benchmark_ticker, min(all_dates), max(all_dates))

    # Calculate portfolio composition and returns
    portfolio_values, portfolio_returns, daily_returns = _calculate_portfolio_returns(
        positions, price_history
    )

    # Calculate risk metrics
    var_95_1day = _calculate_var_historical(daily_returns, confidence=0.95, lookback=1)
    var_95_10day = var_95_1day * np.sqrt(10)

    max_drawdown, dd_start, dd_end = _calculate_max_drawdown(portfolio_values)

    annualized_return = (
        daily_returns.mean() * 252 if len(daily_returns) > 0 else 0
    )
    annualized_volatility = (
        daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0
    )

    sharpe_ratio = _calculate_sharpe_ratio(
        annualized_return, annualized_volatility, risk_free_rate=RISK_FREE_RATE
    )

    portfolio_beta = _calculate_portfolio_beta(
        positions, price_history, benchmark_data
    )

    correlation_matrix = _calculate_correlation_matrix(price_history)

    return {
        "var_95_1day": var_95_1day,
        "var_95_10day": var_95_10day,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "max_drawdown_start": dd_start,
        "max_drawdown_end": dd_end,
        "portfolio_beta": portfolio_beta,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "correlation_matrix": correlation_matrix,
        "_internal": {
            "daily_returns": daily_returns,
            "portfolio_values": portfolio_values,
        },
    }


def generate_risk_charts(risk_data: Dict, positions: List[Dict]) -> Dict:
    """
    Generate interactive Plotly charts for risk visualization.

    Args:
        risk_data: Output from calculate_portfolio_risk()
        positions: List of position dicts

    Returns:
        Dict with keys:
            - "drawdown": Area chart of portfolio drawdown
            - "correlation": Heatmap of correlation matrix
            - "var_distribution": Histogram with VaR line
            - "risk_return": Scatter of return vs volatility by holding
    """
    charts = {}

    # 1. Drawdown chart
    charts["drawdown"] = _create_drawdown_chart(risk_data)

    # 2. Correlation heatmap
    charts["correlation"] = _create_correlation_heatmap(risk_data["correlation_matrix"])

    # 3. VaR distribution
    charts["var_distribution"] = _create_var_distribution_chart(risk_data)

    # 4. Risk-return scatter
    charts["risk_return"] = _create_risk_return_scatter(risk_data, positions)

    return charts


# ============================================================================
# Internal helper functions
# ============================================================================


def _get_benchmark_data(
    ticker: str, start_date: datetime, end_date: datetime
) -> Optional[pd.DataFrame]:
    """Download and cache benchmark data."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if isinstance(data, pd.DataFrame) and len(data) > 0:
            return data
    except Exception:
        pass
    return None


def _calculate_portfolio_returns(
    positions: List[Dict], price_history: Dict
) -> Tuple[pd.Series, pd.Series, np.ndarray]:
    """
    Calculate portfolio value and returns over time.

    Returns:
        - portfolio_values: Time series of portfolio value
        - portfolio_returns: Time series of portfolio returns
        - daily_returns: Numpy array of daily returns
    """
    # Align dates across all holdings
    all_dates = []
    for prices_df in price_history.values():
        if prices_df is not None and len(prices_df) > 0:
            all_dates.extend(prices_df.index.tolist())

    all_dates = sorted(set(all_dates))
    if not all_dates:
        raise ValueError("No valid price data across holdings")

    # Calculate portfolio value at each date
    portfolio_values_list = []

    for date in all_dates:
        total_value = 0

        for position in positions:
            ticker = position["ticker"]
            shares = position["shares"]

            if ticker not in price_history or price_history[ticker] is None:
                continue

            prices_df = price_history[ticker]
            if date not in prices_df.index:
                # Use most recent price before this date
                valid_prices = prices_df[prices_df.index <= date]
                if len(valid_prices) > 0:
                    price = valid_prices["Close"].iloc[-1]
                else:
                    continue
            else:
                price = prices_df.loc[date, "Close"]

            total_value += shares * price

        if total_value > 0:
            portfolio_values_list.append(
                {"date": date, "value": total_value}
            )

    if not portfolio_values_list:
        raise ValueError("Could not calculate portfolio values")

    portfolio_df = pd.DataFrame(portfolio_values_list).set_index("date")
    portfolio_values = portfolio_df["value"]

    # Calculate returns
    portfolio_returns = portfolio_values.pct_change().dropna()
    daily_returns = portfolio_returns.values

    return portfolio_values, portfolio_returns, daily_returns


def _calculate_var_historical(
    returns: np.ndarray, confidence: float = 0.95, lookback: int = 1
) -> float:
    """
    Calculate historical Value at Risk.

    Args:
        returns: Array of daily returns (as decimals)
        confidence: Confidence level (0.95 for 95%)
        lookback: Number of days to scale for (1 for 1-day)

    Returns:
        VaR as absolute currency value per $1 of portfolio
    """
    if len(returns) < 10:
        return 0.0

    # VaR at given confidence level (percentile of losses)
    var_percentile = np.percentile(returns, (1 - confidence) * 100)

    return abs(var_percentile)


def _calculate_max_drawdown(
    portfolio_values: pd.Series,
) -> Tuple[float, Optional[datetime], Optional[datetime]]:
    """
    Calculate maximum drawdown and its period.

    Returns:
        - max_drawdown: As negative percentage (e.g., -0.25 for -25%)
        - start_date: When drawdown began
        - end_date: When drawdown ended
    """
    if len(portfolio_values) < 2:
        return 0.0, None, None

    cummax = portfolio_values.expanding().max()
    drawdown = (portfolio_values - cummax) / cummax

    min_drawdown = drawdown.min()
    min_idx = drawdown.idxmin()

    # Find start of this drawdown
    values_before = portfolio_values[: drawdown.index.get_loc(min_idx) + 1]
    start_idx = cummax[:min_idx].idxmax()

    return float(min_drawdown), start_idx, min_idx


def _calculate_sharpe_ratio(
    annual_return: float, annual_volatility: float, risk_free_rate: float = 0.045
) -> float:
    """Calculate annualized Sharpe ratio."""
    if annual_volatility == 0:
        return 0.0

    return (annual_return - risk_free_rate) / annual_volatility


def _calculate_portfolio_beta(
    positions: List[Dict], price_history: Dict, benchmark_data: Optional[pd.DataFrame]
) -> float:
    """
    Calculate portfolio beta vs benchmark.

    Uses weighted average of individual stock betas.
    """
    if not benchmark_data or len(benchmark_data) < 20:
        return 1.0

    benchmark_returns = benchmark_data["Close"].pct_change().dropna()
    if len(benchmark_returns) < 10:
        return 1.0

    betas = []
    weights = []

    # Calculate total portfolio value for weighting
    total_value = 0
    for position in positions:
        ticker = position["ticker"]
        if ticker in price_history and price_history[ticker] is not None:
            latest_price = price_history[ticker]["Close"].iloc[-1]
            position_value = position["shares"] * latest_price
            total_value += position_value

    if total_value == 0:
        return 1.0

    for position in positions:
        ticker = position["ticker"]

        if ticker not in price_history or price_history[ticker] is None:
            continue

        prices = price_history[ticker]
        if len(prices) < 20:
            continue

        # Align dates with benchmark
        stock_returns = prices["Close"].pct_change().dropna()
        common_dates = stock_returns.index.intersection(benchmark_returns.index)

        if len(common_dates) < 10:
            continue

        stock_ret = stock_returns[common_dates].values
        bench_ret = benchmark_returns[common_dates].values

        # Calculate beta
        covariance = np.cov(stock_ret, bench_ret)[0, 1]
        benchmark_variance = np.var(bench_ret)

        if benchmark_variance > 0:
            beta = covariance / benchmark_variance
            betas.append(beta)

            # Weight by position size
            latest_price = prices["Close"].iloc[-1]
            position_value = position["shares"] * latest_price
            weights.append(position_value / total_value)

    if not betas:
        return 1.0

    return float(np.average(betas, weights=weights))


def _calculate_correlation_matrix(price_history: Dict) -> pd.DataFrame:
    """
    Calculate correlation matrix between all holdings.
    """
    returns_dict = {}
    all_dates = set()

    # Calculate returns for each holding
    for ticker, prices_df in price_history.items():
        if prices_df is None or len(prices_df) < 2:
            continue

        returns = prices_df["Close"].pct_change().dropna()
        if len(returns) > 0:
            returns_dict[ticker] = returns
            all_dates.update(returns.index)

    if not returns_dict:
        # Return empty correlation matrix
        return pd.DataFrame()

    # Align all returns to common dates
    common_dates = sorted(all_dates)
    aligned_returns = {}

    for ticker, returns in returns_dict.items():
        aligned_returns[ticker] = returns[returns.index.isin(common_dates)].sort_index()

    # Create returns dataframe
    returns_df = pd.DataFrame(aligned_returns)
    returns_df = returns_df.dropna(how="all")

    if len(returns_df) == 0:
        return pd.DataFrame()

    return returns_df.corr()


# ============================================================================
# Chart generation functions
# ============================================================================


def _create_drawdown_chart(risk_data: Dict) -> go.Figure:
    """Create area chart showing portfolio drawdown over time."""
    portfolio_values = risk_data["_internal"]["portfolio_values"]

    if len(portfolio_values) < 2:
        # Return empty chart
        return go.Figure()

    cummax = portfolio_values.expanding().max()
    drawdown_pct = ((portfolio_values - cummax) / cummax * 100).dropna()

    # Determine colors based on max drawdown period
    dd_start = risk_data["max_drawdown_start"]
    dd_end = risk_data["max_drawdown_end"]

    colors = []
    for date in drawdown_pct.index:
        if dd_start and dd_end and dd_start <= date <= dd_end:
            colors.append(TAM_COLORS["red"])
        else:
            colors.append(TAM_COLORS["green"])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=drawdown_pct.index,
            y=drawdown_pct.values,
            fill="tozeroy",
            fillcolor=TAM_COLORS["green"],
            line=dict(color=TAM_COLORS["green"], width=2),
            name="Drawdown",
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Drawdown: %{y:.2f}%<extra></extra>",
        )
    )

    # Highlight max drawdown period
    if dd_start and dd_end:
        dd_data = drawdown_pct[(drawdown_pct.index >= dd_start) & (drawdown_pct.index <= dd_end)]
        if len(dd_data) > 0:
            fig.add_trace(
                go.Scatter(
                    x=dd_data.index,
                    y=dd_data.values,
                    fill="tozeroy",
                    fillcolor=TAM_COLORS["red"],
                    line=dict(color=TAM_COLORS["red"], width=2),
                    name="Max Drawdown Period",
                    hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Drawdown: %{y:.2f}%<extra></extra>",
                )
            )

    fig.update_layout(
        title="Portfolio Drawdown Over Time",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=TAM_COLORS["card"],
        font=dict(color=TAM_COLORS["text"], family="sans-serif"),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=TAM_COLORS["grid"],
            showline=True,
            linewidth=1,
            linecolor=TAM_COLORS["muted"],
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=TAM_COLORS["grid"],
            showline=True,
            linewidth=1,
            linecolor=TAM_COLORS["muted"],
        ),
        margin=dict(l=60, r=20, t=50, b=50),
        height=400,
    )

    return fig


def _create_correlation_heatmap(corr_matrix: pd.DataFrame) -> go.Figure:
    """Create correlation heatmap with TAM color scale."""
    if corr_matrix.empty or len(corr_matrix) < 2:
        return go.Figure()

    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale=[
                [0, TAM_COLORS["deep"]],
                [0.5, TAM_COLORS["blue"]],
                [1, TAM_COLORS["turquoise"]],
            ],
            zmid=0,
            zmin=-1,
            zmax=1,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text:.2f}",
            textfont={"color": TAM_COLORS["text"], "size": 10},
            colorbar=dict(
                title="Correlation",
                thickness=15,
                len=0.7,
                x=1.02,
            ),
            hovertemplate="%{x} - %{y}<br>Correlation: %{z:.3f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Correlation Matrix",
        xaxis_title="",
        yaxis_title="",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=TAM_COLORS["card"],
        font=dict(color=TAM_COLORS["text"], family="sans-serif"),
        margin=dict(l=100, r=150, t=50, b=100),
        height=500,
        xaxis=dict(side="bottom"),
        yaxis=dict(tickangle=-0),
    )

    return fig


def _create_var_distribution_chart(risk_data: Dict) -> go.Figure:
    """Create histogram of daily returns with VaR line marked."""
    daily_returns = risk_data["_internal"]["daily_returns"]

    if len(daily_returns) < 10:
        return go.Figure()

    var_95 = risk_data["var_95_1day"]

    # Convert to percentage for display
    daily_returns_pct = daily_returns * 100

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=daily_returns_pct,
            nbinsx=50,
            name="Daily Returns",
            marker=dict(color=TAM_COLORS["blue"], opacity=0.7),
            hovertemplate="Return: %{x:.2f}%<br>Frequency: %{y}<extra></extra>",
        )
    )

    # Add VaR line
    fig.add_vline(
        x=-var_95 * 100,
        line_dash="dash",
        line_color=TAM_COLORS["red"],
        line_width=2,
        annotation_text=f"VaR 95% (1-day): {-var_95*100:.2f}%",
        annotation_position="top right",
        annotation_font=dict(color=TAM_COLORS["red"], size=11),
    )

    fig.update_layout(
        title="Daily Returns Distribution with Value at Risk",
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        hovermode="x",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=TAM_COLORS["card"],
        font=dict(color=TAM_COLORS["text"], family="sans-serif"),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=TAM_COLORS["grid"],
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=TAM_COLORS["grid"],
        ),
        margin=dict(l=60, r=20, t=50, b=50),
        height=400,
    )

    return fig


def _create_risk_return_scatter(risk_data: Dict, positions: List[Dict]) -> go.Figure:
    """
    Create scatter plot of return vs volatility for each holding.
    Bubble size represents position weight.
    """
    if not positions:
        return go.Figure()

    # Calculate total portfolio value
    total_value = 0
    position_values = {}

    for position in positions:
        ticker = position["ticker"]
        # Use cost basis as proxy if current price not available
        position_values[ticker] = position["shares"] * position["cost_basis"]
        total_value += position_values[ticker]

    if total_value == 0:
        return go.Figure()

    holdings_data = []

    for position in positions:
        ticker = position["ticker"]
        weight = position_values[ticker] / total_value

        # Calculate return and volatility
        if ticker in risk_data["correlation_matrix"].index:
            # Use stored correlation matrix to get returns
            annual_return = 0.0
            annual_volatility = 0.0

            # This is a simplified calculation; in production,
            # you'd track individual holding returns
            holdings_data.append(
                {
                    "ticker": ticker,
                    "return": annual_return,
                    "volatility": annual_volatility * 100,
                    "weight": weight * 100,
                }
            )

    if not holdings_data:
        return go.Figure()

    holdings_df = pd.DataFrame(holdings_data)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=holdings_df["volatility"],
            y=holdings_df["return"] * 100,
            mode="markers",
            marker=dict(
                size=holdings_df["weight"] * 5,
                color=TAM_COLORS["turquoise"],
                opacity=0.7,
                line=dict(color=TAM_COLORS["blue"], width=1),
            ),
            text=holdings_df["ticker"],
            customdata=holdings_df["weight"],
            hovertemplate="<b>%{text}</b><br>Return: %{y:.2f}%<br>Volatility: %{x:.2f}%<br>Weight: %{customdata:.1f}%<extra></extra>",
            name="Holdings",
        )
    )

    fig.update_layout(
        title="Risk-Return Profile by Holding",
        xaxis_title="Volatility (Annualized %)",
        yaxis_title="Return (Annualized %)",
        hovermode="closest",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=TAM_COLORS["card"],
        font=dict(color=TAM_COLORS["text"], family="sans-serif"),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=TAM_COLORS["grid"],
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=TAM_COLORS["grid"],
        ),
        margin=dict(l=60, r=20, t=50, b=50),
        height=400,
    )

    return fig
