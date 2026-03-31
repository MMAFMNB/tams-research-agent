"""
Financial Statement Viewer for Streamlit Stock Research App

Provides interactive 5-year financial statement viewing with growth rates,
margins, and styled HTML output using TAM Liquid Glass theme.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Optional, List, Tuple
import warnings

warnings.filterwarnings('ignore')


def fetch_financial_statements(ticker: str) -> Dict[str, pd.DataFrame]:
    """
    Fetch 5 years of annual financial statements using yfinance.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Dictionary with keys:
        - "income_statement": Income statement DataFrame
        - "balance_sheet": Balance sheet DataFrame
        - "cash_flow": Cash flow statement DataFrame

        Each DataFrame has years as columns and line items as rows.
        Data is sorted chronologically (oldest to newest).

    Raises:
        ValueError: If ticker not found or no data available
    """
    try:
        stock = yf.Ticker(ticker)

        # Fetch annual financial statements
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow

        # Check if we have data
        if income_stmt.empty or balance_sheet.empty or cash_flow.empty:
            raise ValueError(f"No financial data available for {ticker}")

        # Keep only the last 5 years and sort chronologically
        income_stmt = income_stmt.iloc[:5].sort_index(axis=1)
        balance_sheet = balance_sheet.iloc[:5].sort_index(axis=1)
        cash_flow = cash_flow.iloc[:5].sort_index(axis=1)

        return {
            "income_statement": income_stmt,
            "balance_sheet": balance_sheet,
            "cash_flow": cash_flow
        }

    except Exception as e:
        raise ValueError(f"Error fetching financial data for {ticker}: {str(e)}")


def calculate_growth_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate year-over-year growth rates for each line item.

    Args:
        df: DataFrame with years as columns and line items as rows

    Returns:
        DataFrame with same shape containing YoY growth rates as percentages.
        First year will be NaN. Negative denominator returns NaN.
    """
    growth_df = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)

    # Sort columns to ensure chronological order
    sorted_cols = sorted(df.columns)

    for i, col in enumerate(sorted_cols):
        if i == 0:
            # First year has no prior year to compare
            growth_df[col] = np.nan
        else:
            prev_col = sorted_cols[i - 1]
            prev_values = df[prev_col].values
            curr_values = df[col].values

            # Calculate growth rate, handling division by zero
            with np.errstate(divide='ignore', invalid='ignore'):
                growth = ((curr_values - prev_values) / np.abs(prev_values)) * 100

            # Handle cases where denominator was 0 or values are NaN
            growth = np.where(np.isfinite(growth), growth, np.nan)
            growth_df[col] = growth

    return growth_df


def calculate_margins(income_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate key profitability margins from income statement.

    Args:
        income_df: Income statement DataFrame

    Returns:
        DataFrame with original data plus margin rows:
        - Gross Margin (%)
        - Operating Margin (%)
        - Net Margin (%)
        - EBITDA Margin (%)
    """
    margins_df = income_df.copy()

    # Look for relevant line items (case-insensitive)
    row_names_lower = {name.lower(): name for name in income_df.index}

    revenue = None
    gross_profit = None
    operating_income = None
    net_income = None
    ebitda = None

    # Find revenue
    for key in ['total revenue', 'revenue', 'net revenue', 'net sales']:
        if key in row_names_lower:
            revenue = income_df.loc[row_names_lower[key]]
            break

    # Find gross profit
    for key in ['gross profit', 'cost of revenue', 'cost of goods sold']:
        if key in row_names_lower:
            if key == 'cost of revenue' or key == 'cost of goods sold':
                revenue_row = revenue if revenue is not None else None
                cost_row = income_df.loc[row_names_lower[key]]
                if revenue_row is not None:
                    gross_profit = revenue_row - cost_row
            else:
                gross_profit = income_df.loc[row_names_lower[key]]
            break

    # Find operating income
    for key in ['operating income', 'ebit', 'operating expenses']:
        if key in row_names_lower:
            if key == 'operating income' or key == 'ebit':
                operating_income = income_df.loc[row_names_lower[key]]
            break

    # Find net income
    for key in ['net income', 'net income common', 'net income attributable', 'net income continuous operations']:
        if key in row_names_lower:
            net_income = income_df.loc[row_names_lower[key]]
            break

    # Find EBITDA
    for key in ['ebitda', 'operating income', 'income from operations']:
        if key in row_names_lower:
            ebitda = income_df.loc[row_names_lower[key]]
            break

    # Calculate and add margins
    if revenue is not None:
        if gross_profit is not None:
            gross_margin = (gross_profit / revenue) * 100
            margins_df.loc['Gross Margin'] = gross_margin

        if operating_income is not None:
            op_margin = (operating_income / revenue) * 100
            margins_df.loc['Operating Margin'] = op_margin

        if net_income is not None:
            net_margin = (net_income / revenue) * 100
            margins_df.loc['Net Margin'] = net_margin

        if ebitda is not None:
            ebitda_margin = (ebitda / revenue) * 100
            margins_df.loc['EBITDA Margin'] = ebitda_margin

    return margins_df


def format_financial_value(value: Optional[float], abbreviate: bool = True) -> str:
    """
    Format financial values with abbreviations for billions, millions, thousands.

    Args:
        value: Numeric value to format
        abbreviate: If True, use B/M/K abbreviations; else use full number

    Returns:
        Formatted string. Returns "—" for None/NaN values.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"

    try:
        num = float(value)
    except (ValueError, TypeError):
        return "—"

    is_negative = num < 0
    num = abs(num)

    if not abbreviate:
        return f"{'-' if is_negative else ''}{num:,.0f}"

    if num >= 1_000_000_000:
        formatted = f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        formatted = f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        formatted = f"{num / 1_000:.1f}K"
    else:
        formatted = f"{num:.2f}"

    return f"{'-' if is_negative else ''}{formatted}"


def generate_sparkline_svg(values: List[Optional[float]], color: str = "#6CB9B6",
                          width: int = 60, height: int = 20) -> str:
    """
    Generate an inline SVG sparkline for a series of values.

    Args:
        values: List of numeric values (may contain None)
        color: Hex color for the line (default TAM turquoise)
        width: SVG width in pixels
        height: SVG height in pixels

    Returns:
        SVG string that can be embedded in HTML
    """
    # Filter out None values and get indices
    valid_indices = [(i, v) for i, v in enumerate(values) if v is not None and not np.isnan(v)]

    if len(valid_indices) < 2:
        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"></svg>'

    # Extract valid values
    valid_values = [v for _, v in valid_indices]
    min_val = min(valid_values)
    max_val = max(valid_values)

    # Handle case where all values are the same
    val_range = max_val - min_val
    if val_range == 0:
        val_range = 1

    # Calculate points
    points = []
    for idx, (orig_idx, val) in enumerate(valid_indices):
        x = (idx / (len(valid_indices) - 1)) * width if len(valid_indices) > 1 else width / 2
        y = height - ((val - min_val) / val_range) * (height - 2) - 1
        points.append(f"{x},{y}")

    points_str = " ".join(points)

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="vertical-align: middle;">
    <polyline points="{points_str}" fill="none" stroke="{color}" stroke-width="1.5" vector-effect="non-scaling-stroke"/>
    </svg>'''

    return svg


def generate_statement_html(df: pd.DataFrame, growth_df: pd.DataFrame,
                           title: str, highlight_rows: Optional[List[str]] = None) -> str:
    """
    Generate styled HTML table for a financial statement with growth rates and CAGR.

    Args:
        df: DataFrame with years as columns and line items as rows
        growth_df: Growth rates DataFrame (from calculate_growth_rates)
        title: Statement title (e.g., "Income Statement")
        highlight_rows: List of row names to highlight with subtle background

    Returns:
        Styled HTML string with TAM Liquid Glass theme
    """
    if df.empty:
        return f"<p>No data available for {title}</p>"

    if highlight_rows is None:
        highlight_rows = []

    # Sort columns chronologically
    sorted_cols = sorted(df.columns)

    # Calculate CAGR for each row
    cagr_values = []
    for row_idx, row_name in enumerate(df.index):
        values = [df.loc[row_name, col] for col in sorted_cols]
        valid_values = [v for v in values if v is not None and not np.isnan(v)]

        if len(valid_values) >= 2:
            first_val = valid_values[0]
            last_val = valid_values[-1]

            if first_val > 0:
                cagr = ((last_val / first_val) ** (1 / (len(valid_values) - 1)) - 1) * 100
            else:
                cagr = np.nan
        else:
            cagr = np.nan

        cagr_values.append(cagr)

    # Build HTML table
    html = f"""
    <div style="margin: 20px 0;">
        <h3 style="color: #E6EDF3; font-size: 1rem; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">{title}</h3>
        <table style="border-collapse: collapse; width: 100%; font-size: 0.8rem; font-family: Inter, sans-serif;">
            <thead>
                <tr style="background: rgba(34,47,98,0.15); color: #E6EDF3; font-weight: 600; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em;">
                    <th style="padding: 8px 12px; border-bottom: 2px solid rgba(108,185,182,0.15); text-align: left;">Line Item</th>
    """

    # Add year columns
    for col in sorted_cols:
        year = col.year if hasattr(col, 'year') else str(col)[:4]
        html += f'<th style="padding: 8px 12px; border-bottom: 2px solid rgba(108,185,182,0.15); text-align: right; color: #E6EDF3;">{year}</th>'

    html += '<th style="padding: 8px 12px; border-bottom: 2px solid rgba(108,185,182,0.15); text-align: right; color: #E6EDF3;">CAGR</th>\n'
    html += '</tr>\n</thead>\n<tbody>\n'

    # Add data rows
    for row_idx, row_name in enumerate(df.index):
        is_highlighted = row_name in highlight_rows
        bg_style = 'background: rgba(26,109,182,0.08);' if is_highlighted else ''

        html += f'<tr style="{bg_style}">\n'
        html += f'<td style="padding: 8px 12px; border-bottom: 1px solid rgba(108,185,182,0.08); color: #E6EDF3; text-align: left; font-weight: 500;">{row_name}</td>\n'

        # Add value columns with growth rates
        for col in sorted_cols:
            value = df.loc[row_name, col]
            growth = growth_df.loc[row_name, col]

            formatted_value = format_financial_value(value)

            # Format growth rate
            if growth is not None and not np.isnan(growth):
                growth_color = '#22C55E' if growth >= 0 else '#EF4444'
                growth_text = f"{'+' if growth >= 0 else ''}{growth:.1f}%"
                growth_html = f'<div style="font-size: 0.65rem; color: {growth_color}; margin-top: 2px;">{growth_text}</div>'
            else:
                growth_html = ''

            html += f'<td style="padding: 8px 12px; border-bottom: 1px solid rgba(108,185,182,0.08); color: #E6EDF3; text-align: right;">{formatted_value}{growth_html}</td>\n'

        # Add CAGR column
        cagr = cagr_values[row_idx]
        if cagr is not None and not np.isnan(cagr):
            cagr_color = '#22C55E' if cagr >= 0 else '#EF4444'
            cagr_text = f"{'+' if cagr >= 0 else ''}{cagr:.1f}%"
            cagr_html = f'<span style="color: {cagr_color}; font-weight: 600;">{cagr_text}</span>'
        else:
            cagr_html = '<span style="color: #888;">—</span>'

        html += f'<td style="padding: 8px 12px; border-bottom: 1px solid rgba(108,185,182,0.08); color: #E6EDF3; text-align: right;">{cagr_html}</td>\n'
        html += '</tr>\n'

    html += '</tbody>\n</table>\n</div>\n'

    return html


def generate_financial_overview(ticker: str) -> Dict:
    """
    Master function to fetch and format all financial data for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with keys:
        - "income_html": Formatted income statement HTML
        - "balance_html": Formatted balance sheet HTML
        - "cashflow_html": Formatted cash flow statement HTML
        - "key_metrics": Dictionary of important metrics with CAGRs
        - "raw_data": Dictionary with raw DataFrames
        - "error": Error message if data fetch fails (optional)

    Example:
        >>> overview = generate_financial_overview('AAPL')
        >>> print(overview['income_html'])
        >>> print(overview['key_metrics'])
    """
    result = {
        "income_html": "",
        "balance_html": "",
        "cashflow_html": "",
        "key_metrics": {},
        "raw_data": {}
    }

    try:
        # Fetch financial statements
        statements = fetch_financial_statements(ticker)
        income_stmt = statements["income_statement"]
        balance_sheet = statements["balance_sheet"]
        cash_flow = statements["cash_flow"]

        # Store raw data
        result["raw_data"] = statements

        # Calculate growth rates
        income_growth = calculate_growth_rates(income_stmt)
        balance_growth = calculate_growth_rates(balance_sheet)
        cashflow_growth = calculate_growth_rates(cash_flow)

        # Calculate margins
        income_with_margins = calculate_margins(income_stmt)
        income_growth_with_margins = calculate_growth_rates(income_with_margins)

        # Generate HTML statements
        income_highlight = ['Revenue', 'Gross Profit', 'Operating Income', 'Net Income',
                          'Total Revenue', 'Net Income Common', 'Net Income Attributable']
        result["income_html"] = generate_statement_html(
            income_with_margins,
            income_growth_with_margins,
            "Income Statement",
            highlight_rows=income_highlight
        )

        balance_highlight = ['Total Assets', 'Total Liabilities', 'Total Equity',
                            'Cash And Cash Equivalents', 'Total Debt']
        result["balance_html"] = generate_statement_html(
            balance_sheet,
            balance_growth,
            "Balance Sheet",
            highlight_rows=balance_highlight
        )

        cashflow_highlight = ['Operating Cash Flow', 'Free Cash Flow', 'Capital Expenditure',
                             'Financing Cash Flow', 'Investing Cash Flow']
        result["cashflow_html"] = generate_statement_html(
            cash_flow,
            cashflow_growth,
            "Cash Flow Statement",
            highlight_rows=cashflow_highlight
        )

        # Extract key metrics
        sorted_cols = sorted(income_stmt.columns)

        # Helper function to get metric and calculate CAGR
        def get_metric_with_cagr(df: pd.DataFrame, metric_names: List[str]) -> Tuple[Optional[float], Optional[float]]:
            """Find metric by checking multiple possible names."""
            for metric_name in metric_names:
                for idx in df.index:
                    if metric_name.lower() in idx.lower():
                        values = [df.loc[idx, col] for col in sorted_cols]
                        valid_values = [v for v in values if v is not None and not np.isnan(v)]

                        if len(valid_values) >= 2:
                            first_val = valid_values[0]
                            last_val = valid_values[-1]

                            if first_val > 0:
                                cagr = ((last_val / first_val) ** (1 / (len(valid_values) - 1)) - 1) * 100
                            else:
                                cagr = np.nan
                        else:
                            cagr = np.nan

                        latest_value = valid_values[-1] if valid_values else None
                        return latest_value, cagr

            return None, None

        # Revenue
        revenue, revenue_cagr = get_metric_with_cagr(income_stmt, ['Total Revenue', 'Revenue', 'Net Revenue', 'Net Sales'])
        if revenue is not None:
            result["key_metrics"]["revenue"] = {
                "value": format_financial_value(revenue),
                "cagr": revenue_cagr,
                "cagr_str": f"{'+' if revenue_cagr >= 0 else ''}{revenue_cagr:.1f}%" if revenue_cagr is not None and not np.isnan(revenue_cagr) else "—"
            }

        # Net Income
        net_income, ni_cagr = get_metric_with_cagr(income_stmt, ['Net Income', 'Net Income Common', 'Net Income Attributable'])
        if net_income is not None:
            result["key_metrics"]["net_income"] = {
                "value": format_financial_value(net_income),
                "cagr": ni_cagr,
                "cagr_str": f"{'+' if ni_cagr >= 0 else ''}{ni_cagr:.1f}%" if ni_cagr is not None and not np.isnan(ni_cagr) else "—"
            }

        # Total Assets
        total_assets, ta_cagr = get_metric_with_cagr(balance_sheet, ['Total Assets'])
        if total_assets is not None:
            result["key_metrics"]["total_assets"] = {
                "value": format_financial_value(total_assets),
                "cagr": ta_cagr,
                "cagr_str": f"{'+' if ta_cagr >= 0 else ''}{ta_cagr:.1f}%" if ta_cagr is not None and not np.isnan(ta_cagr) else "—"
            }

        # Free Cash Flow
        fcf, fcf_cagr = get_metric_with_cagr(cash_flow, ['Free Cash Flow', 'Operating Cash Flow'])
        if fcf is not None:
            result["key_metrics"]["free_cash_flow"] = {
                "value": format_financial_value(fcf),
                "cagr": fcf_cagr,
                "cagr_str": f"{'+' if fcf_cagr >= 0 else ''}{fcf_cagr:.1f}%" if fcf_cagr is not None and not np.isnan(fcf_cagr) else "—"
            }

        # Net Margin (latest)
        for idx in income_with_margins.index:
            if 'Net Margin' in idx:
                latest_margin = income_with_margins.loc[idx, sorted_cols[-1]]
                if latest_margin is not None and not np.isnan(latest_margin):
                    result["key_metrics"]["net_margin"] = {
                        "value": f"{latest_margin:.1f}%",
                        "cagr": None
                    }
                break

    except Exception as e:
        result["error"] = str(e)

    return result


# Example usage and testing
if __name__ == "__main__":
    # Test with Apple
    overview = generate_financial_overview("AAPL")

    if "error" in overview:
        print(f"Error: {overview['error']}")
    else:
        print("Financial Overview Generated Successfully")
        print("\nKey Metrics:")
        for metric, data in overview["key_metrics"].items():
            print(f"  {metric}: {data.get('value', '—')} (CAGR: {data.get('cagr_str', '—')})")

        print("\nRaw data shapes:")
        for key, df in overview["raw_data"].items():
            print(f"  {key}: {df.shape}")
