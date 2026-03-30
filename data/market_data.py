"""Fetch market data from Yahoo Finance with enhanced Tadawul support.

Provides current prices, 5-year audited financials (income statement,
balance sheet, cash flow), and technical indicators for Saudi-listed
and global equities.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


def fetch_stock_data(ticker: str, collector=None) -> dict:
    """Fetch comprehensive stock data for analysis."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    if collector:
        collector.add(
            source_type="yahoo_finance",
            title=f"Yahoo Finance - {info.get('longName', ticker)} Real-time Quote",
            url=f"https://finance.yahoo.com/quote/{ticker}",
            description="Live stock price, valuation metrics, and company overview",
        )

    # Determine if Tadawul stock
    is_tadawul = ticker.endswith(".SR")

    data = {
        "ticker": ticker,
        "name": info.get("longName", info.get("shortName", ticker)),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "currency": info.get("currency", "SAR" if is_tadawul else "USD"),
        "exchange": info.get("exchange", "SAU" if is_tadawul else ""),
        "is_tadawul": is_tadawul,
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
        "previous_close": info.get("previousClose") or info.get("regularMarketPreviousClose", 0),
        "open_price": info.get("open") or info.get("regularMarketOpen", 0),
        "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh", 0),
        "day_low": info.get("dayLow") or info.get("regularMarketDayLow", 0),
        "market_cap": info.get("marketCap", 0),
        "enterprise_value": info.get("enterpriseValue", 0),
        "shares_outstanding": info.get("sharesOutstanding", 0),
    }

    # Valuation metrics
    data["pe_ratio"] = info.get("trailingPE")
    data["forward_pe"] = info.get("forwardPE")
    data["pb_ratio"] = info.get("priceToBook")
    data["ps_ratio"] = info.get("priceToSalesTrailing12Months")
    data["ev_ebitda"] = info.get("enterpriseToEbitda")
    data["ev_revenue"] = info.get("enterpriseToRevenue")
    data["peg_ratio"] = info.get("pegRatio")

    # Earnings
    data["eps_ttm"] = info.get("trailingEps")
    data["eps_forward"] = info.get("forwardEps")
    data["earnings_growth"] = info.get("earningsGrowth")
    data["revenue_growth"] = info.get("revenueGrowth")

    # Financials (latest)
    data["revenue"] = info.get("totalRevenue", 0)
    data["gross_margins"] = info.get("grossMargins")
    data["operating_margins"] = info.get("operatingMargins")
    data["profit_margins"] = info.get("profitMargins")
    data["ebitda"] = info.get("ebitda", 0)
    data["total_debt"] = info.get("totalDebt", 0)
    data["total_cash"] = info.get("totalCash", 0)
    data["debt_to_equity"] = info.get("debtToEquity")
    data["current_ratio"] = info.get("currentRatio")
    data["quick_ratio"] = info.get("quickRatio")
    data["free_cash_flow"] = info.get("freeCashflow", 0)
    data["operating_cash_flow"] = info.get("operatingCashflow", 0)
    data["return_on_equity"] = info.get("returnOnEquity")
    data["return_on_assets"] = info.get("returnOnAssets")
    data["book_value"] = info.get("bookValue")

    # Dividends
    data["dividend_rate"] = info.get("dividendRate")
    data["dividend_yield"] = info.get("dividendYield")
    data["payout_ratio"] = info.get("payoutRatio")
    data["ex_dividend_date"] = info.get("exDividendDate")
    data["five_year_avg_dividend_yield"] = info.get("fiveYearAvgDividendYield")

    # Risk metrics
    data["beta"] = info.get("beta")
    data["fifty_two_week_high"] = info.get("fiftyTwoWeekHigh")
    data["fifty_two_week_low"] = info.get("fiftyTwoWeekLow")
    data["fifty_day_avg"] = info.get("fiftyDayAverage")
    data["two_hundred_day_avg"] = info.get("twoHundredDayAverage")
    data["avg_volume"] = info.get("averageVolume")

    data["business_summary"] = info.get("longBusinessSummary", "")

    return data


def fetch_price_history(ticker: str, period: str = "5y", collector=None) -> pd.DataFrame:
    """Fetch historical price data (default 5 years for comprehensive analysis)."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    if collector:
        collector.add(
            source_type="yahoo_finance",
            title=f"Yahoo Finance - {ticker} Historical Prices ({period})",
            url=f"https://finance.yahoo.com/quote/{ticker}/history/",
            description=f"OHLCV price data, {period} period",
        )
    return hist


def fetch_financials(ticker: str, collector=None) -> dict:
    """Fetch 5-year audited financial statements.

    Retrieves annual income statement, balance sheet, and cash flow data.
    yfinance typically provides 4 annual periods; we request all available.
    Falls back to 3 years if 5 are not available.
    """
    stock = yf.Ticker(ticker)
    if collector:
        collector.add(
            source_type="financial_statements",
            title=f"Yahoo Finance - {ticker} Financial Statements (Audited)",
            url=f"https://finance.yahoo.com/quote/{ticker}/financials/",
            description="Annual income statement, balance sheet, and cash flow data",
        )
    result = {
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {},
        "years_available": 0,
    }

    # Annual income statement
    try:
        income = stock.income_stmt
        if income is not None and not income.empty:
            result["income_statement"] = income.to_dict()
            result["years_available"] = max(result["years_available"], len(income.columns))
    except Exception:
        pass

    # Annual balance sheet
    try:
        balance = stock.balance_sheet
        if balance is not None and not balance.empty:
            result["balance_sheet"] = balance.to_dict()
            result["years_available"] = max(result["years_available"], len(balance.columns))
    except Exception:
        pass

    # Annual cash flow
    try:
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            result["cash_flow"] = cashflow.to_dict()
            result["years_available"] = max(result["years_available"], len(cashflow.columns))
    except Exception:
        pass

    # Also fetch quarterly for more recent data
    try:
        q_income = stock.quarterly_income_stmt
        if q_income is not None and not q_income.empty:
            result["quarterly_income"] = q_income.to_dict()
    except Exception:
        pass

    return result


def fetch_dividend_history(ticker: str, collector=None) -> pd.DataFrame:
    """Fetch full dividend payment history."""
    stock = yf.Ticker(ticker)
    dividends = stock.dividends
    if collector:
        collector.add(
            source_type="yahoo_finance",
            title=f"Yahoo Finance - {ticker} Dividend History",
            url=f"https://finance.yahoo.com/quote/{ticker}/history/?filter=div",
            description="Historical dividend payments and dates",
        )
    return dividends


def calculate_technical_indicators(hist: pd.DataFrame) -> dict:
    """Calculate key technical indicators from price history."""
    if hist.empty:
        return {}

    close = hist["Close"]
    indicators = {}

    # Moving averages
    for period in [20, 50, 100, 200]:
        key = f"ma_{period}"
        indicators[key] = close.rolling(period).mean().iloc[-1] if len(close) >= period else None

    # RSI (14-day)
    if len(close) >= 15:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        indicators["rsi_14"] = rsi.iloc[-1]
    else:
        indicators["rsi_14"] = None

    # MACD
    if len(close) >= 26:
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line
        indicators["macd_line"] = macd_line.iloc[-1]
        indicators["macd_signal"] = signal_line.iloc[-1]
        indicators["macd_histogram"] = histogram.iloc[-1]
    else:
        indicators["macd_line"] = None
        indicators["macd_signal"] = None
        indicators["macd_histogram"] = None

    # Bollinger Bands
    if len(close) >= 20:
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        indicators["bb_upper"] = (sma_20 + 2 * std_20).iloc[-1]
        indicators["bb_middle"] = sma_20.iloc[-1]
        indicators["bb_lower"] = (sma_20 - 2 * std_20).iloc[-1]
    else:
        indicators["bb_upper"] = None
        indicators["bb_middle"] = None
        indicators["bb_lower"] = None

    # Volume analysis
    if len(hist) >= 20:
        avg_vol = hist["Volume"].rolling(20).mean().iloc[-1]
        current_vol = hist["Volume"].iloc[-1]
        indicators["volume_ratio"] = current_vol / avg_vol if avg_vol > 0 else 1
    else:
        indicators["volume_ratio"] = None

    # Price position in 52-week range
    if len(close) >= 252:
        high_52 = close.tail(252).max()
        low_52 = close.tail(252).min()
        current = close.iloc[-1]
        if high_52 != low_52:
            indicators["price_position_52w"] = (current - low_52) / (high_52 - low_52)
        else:
            indicators["price_position_52w"] = 0.5

    return indicators


def _format_financial_table(financials: dict, statement_type: str) -> str:
    """Format a financial statement dict into a readable table for AI prompts."""
    data = financials.get(statement_type, {})
    if not data:
        return f"  {statement_type}: No data available\n"

    lines = []
    # Sort periods (columns) chronologically
    periods = sorted(data.keys())

    # Build header with year labels
    year_labels = []
    for p in periods:
        if hasattr(p, "strftime"):
            year_labels.append(p.strftime("%Y"))
        else:
            year_labels.append(str(p)[:4])

    # Get all row keys from the first period
    if periods:
        row_keys = list(data[periods[0]].keys())
    else:
        return ""

    # Key financial metrics to highlight (order matters)
    priority_metrics = {
        "income_statement": [
            "Total Revenue", "TotalRevenue",
            "Gross Profit", "GrossProfit",
            "Operating Income", "OperatingIncome", "EBIT",
            "EBITDA",
            "Net Income", "NetIncome",
            "Basic EPS", "BasicEPS", "Diluted EPS", "DilutedEPS",
        ],
        "balance_sheet": [
            "Total Assets", "TotalAssets",
            "Total Liabilities Net Minority Interest", "TotalLiabilitiesNetMinorityInterest",
            "Total Equity Gross Minority Interest", "TotalEquityGrossMinorityInterest",
            "Stockholders Equity", "StockholdersEquity",
            "Total Debt", "TotalDebt",
            "Cash And Cash Equivalents", "CashAndCashEquivalents",
            "Net Debt", "NetDebt",
        ],
        "cash_flow": [
            "Operating Cash Flow", "OperatingCashFlow",
            "Capital Expenditure", "CapitalExpenditure",
            "Free Cash Flow", "FreeCashFlow",
            "Financing Cash Flow", "FinancingCashFlow",
        ],
    }

    # Filter to priority metrics that exist
    target_keys = priority_metrics.get(statement_type, row_keys[:15])
    shown_keys = [k for k in target_keys if k in row_keys]
    # Add remaining keys not in priority list
    remaining = [k for k in row_keys if k not in shown_keys][:10]
    shown_keys.extend(remaining)

    if not shown_keys:
        return ""

    # Format as table
    header = f"  {'Metric':<45} " + " ".join(f"{y:>14}" for y in year_labels)
    lines.append(header)
    lines.append("  " + "-" * len(header))

    for key in shown_keys:
        values = []
        for p in periods:
            val = data[p].get(key)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                values.append(f"{'N/A':>14}")
            elif abs(val) >= 1e9:
                values.append(f"{val/1e9:>13.2f}B")
            elif abs(val) >= 1e6:
                values.append(f"{val/1e6:>13.1f}M")
            else:
                values.append(f"{val:>14,.0f}")

        # Clean up key name for display
        display_key = key.replace("_", " ")
        # Add spaces before capital letters for CamelCase
        import re
        display_key = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', display_key)
        lines.append(f"  {display_key:<45} " + " ".join(values))

    return "\n".join(lines)


def format_market_data_for_prompt(data: dict, technicals: dict, hist: pd.DataFrame,
                                  financials: dict = None) -> str:
    """Format all market data into a structured string for the AI prompt.

    Includes current price, valuation, 5-year financial history, and technicals.
    """

    def fmt(val, prefix="", suffix="", decimals=2):
        if val is None:
            return "N/A"
        if isinstance(val, float):
            return f"{prefix}{val:,.{decimals}f}{suffix}"
        return f"{prefix}{val}{suffix}"

    def fmt_large(val):
        if val is None or val == 0:
            return "N/A"
        if val >= 1e12:
            return f"{val/1e12:,.2f}T"
        if val >= 1e9:
            return f"{val/1e9:,.2f}B"
        if val >= 1e6:
            return f"{val/1e6:,.2f}M"
        return f"{val:,.0f}"

    lines = []
    exchange_label = "Tadawul (Saudi Exchange)" if data.get("is_tadawul") else data.get("exchange", "")
    lines.append(f"=== STOCK DATA: {data['name']} ({data['ticker']}) ===")
    lines.append(f"Exchange: {exchange_label} | Sector: {data['sector']} | Industry: {data['industry']}")
    lines.append(f"Currency: {data['currency']}")
    lines.append("")

    # Current price with daily movement
    current = data.get("current_price", 0)
    prev = data.get("previous_close", 0)
    daily_change = ""
    if current and prev and prev > 0:
        chg = current - prev
        chg_pct = (chg / prev) * 100
        arrow = "+" if chg >= 0 else ""
        daily_change = f" ({arrow}{chg:.2f}, {arrow}{chg_pct:.2f}%)"
    lines.append("--- CURRENT PRICE ---")
    lines.append(f"Price: {data['currency']} {fmt(current)}{daily_change}")
    lines.append(f"Day Range: {fmt(data.get('day_low'))} - {fmt(data.get('day_high'))}")
    lines.append(f"52W Range: {fmt(data.get('fifty_two_week_low'))} - {fmt(data.get('fifty_two_week_high'))}")
    lines.append(f"Market Cap: {fmt_large(data['market_cap'])}")
    lines.append(f"Shares Outstanding: {fmt_large(data.get('shares_outstanding'))}")
    lines.append("")

    lines.append("--- VALUATION MULTIPLES ---")
    lines.append(f"P/E (TTM): {fmt(data['pe_ratio'])}x | Forward P/E: {fmt(data['forward_pe'])}x")
    lines.append(f"P/B: {fmt(data['pb_ratio'])}x | P/S: {fmt(data['ps_ratio'])}x")
    lines.append(f"EV/EBITDA: {fmt(data['ev_ebitda'])}x | EV/Revenue: {fmt(data.get('ev_revenue'))}x")
    lines.append(f"PEG: {fmt(data['peg_ratio'])}")
    lines.append("")

    lines.append("--- EARNINGS & GROWTH ---")
    lines.append(f"EPS (TTM): {fmt(data['eps_ttm'])} | EPS (Forward): {fmt(data['eps_forward'])}")
    lines.append(f"Earnings Growth: {fmt(data['earnings_growth'], suffix='%') if data.get('earnings_growth') else 'N/A'}")
    lines.append(f"Revenue Growth: {fmt(data['revenue_growth'], suffix='%') if data.get('revenue_growth') else 'N/A'}")
    lines.append(f"Revenue (TTM): {fmt_large(data['revenue'])} | EBITDA: {fmt_large(data.get('ebitda'))}")
    lines.append("")

    lines.append("--- PROFITABILITY ---")
    lines.append(f"Gross Margin: {fmt(data.get('gross_margins'), suffix='%') if data.get('gross_margins') else 'N/A'}")
    lines.append(f"Operating Margin: {fmt(data.get('operating_margins'), suffix='%') if data.get('operating_margins') else 'N/A'}")
    lines.append(f"Net Margin: {fmt(data.get('profit_margins'), suffix='%') if data.get('profit_margins') else 'N/A'}")
    lines.append(f"ROE: {fmt(data.get('return_on_equity'), suffix='%') if data.get('return_on_equity') else 'N/A'}")
    lines.append(f"ROA: {fmt(data.get('return_on_assets'), suffix='%') if data.get('return_on_assets') else 'N/A'}")
    lines.append("")

    lines.append("--- BALANCE SHEET ---")
    lines.append(f"Total Debt: {fmt_large(data['total_debt'])} | Total Cash: {fmt_large(data['total_cash'])}")
    lines.append(f"Debt/Equity: {fmt(data['debt_to_equity'])} | Current Ratio: {fmt(data['current_ratio'])}")
    lines.append(f"Quick Ratio: {fmt(data.get('quick_ratio'))} | Book Value/Share: {fmt(data['book_value'])}")
    lines.append("")

    lines.append("--- CASH FLOW ---")
    lines.append(f"Operating Cash Flow: {fmt_large(data['operating_cash_flow'])}")
    lines.append(f"Free Cash Flow: {fmt_large(data['free_cash_flow'])}")
    lines.append("")

    lines.append("--- DIVIDENDS ---")
    lines.append(f"Dividend Rate: {fmt(data['dividend_rate'])} | Yield: {fmt(data['dividend_yield'], suffix='%') if data.get('dividend_yield') else 'N/A'}")
    lines.append(f"Payout Ratio: {fmt(data['payout_ratio'], suffix='%') if data.get('payout_ratio') else 'N/A'}")
    lines.append(f"5Y Avg Yield: {fmt(data['five_year_avg_dividend_yield'], suffix='%') if data.get('five_year_avg_dividend_yield') else 'N/A'}")
    lines.append("")

    lines.append("--- RISK METRICS ---")
    lines.append(f"Beta: {fmt(data['beta'])}")
    lines.append(f"50D Avg: {fmt(data['fifty_day_avg'])} | 200D Avg: {fmt(data['two_hundred_day_avg'])}")
    lines.append("")

    # Historical financial statements (5 years if available)
    if financials:
        years = financials.get("years_available", 0)
        lines.append(f"=== AUDITED FINANCIAL STATEMENTS ({years} years available) ===")
        lines.append("")

        income_table = _format_financial_table(financials, "income_statement")
        if income_table:
            lines.append("--- INCOME STATEMENT (Annual) ---")
            lines.append(income_table)
            lines.append("")

        balance_table = _format_financial_table(financials, "balance_sheet")
        if balance_table:
            lines.append("--- BALANCE SHEET (Annual) ---")
            lines.append(balance_table)
            lines.append("")

        cash_table = _format_financial_table(financials, "cash_flow")
        if cash_table:
            lines.append("--- CASH FLOW STATEMENT (Annual) ---")
            lines.append(cash_table)
            lines.append("")

    # Technical indicators
    if technicals:
        lines.append("--- TECHNICAL INDICATORS ---")
        lines.append(f"MA(20): {fmt(technicals.get('ma_20'))} | MA(50): {fmt(technicals.get('ma_50'))}")
        lines.append(f"MA(100): {fmt(technicals.get('ma_100'))} | MA(200): {fmt(technicals.get('ma_200'))}")
        lines.append(f"RSI(14): {fmt(technicals.get('rsi_14'))}")
        lines.append(f"MACD: {fmt(technicals.get('macd_line'))} | Signal: {fmt(technicals.get('macd_signal'))} | Hist: {fmt(technicals.get('macd_histogram'))}")
        lines.append(f"Bollinger: {fmt(technicals.get('bb_lower'))} / {fmt(technicals.get('bb_middle'))} / {fmt(technicals.get('bb_upper'))}")
        lines.append(f"Volume Ratio (vs 20D avg): {fmt(technicals.get('volume_ratio'))}")
        lines.append("")

    # Recent price action
    if not hist.empty:
        lines.append("--- RECENT PRICE ACTION (Last 10 Trading Days) ---")
        recent = hist.tail(10)
        for date, row in recent.iterrows():
            d = date.strftime("%Y-%m-%d")
            lines.append(f"  {d}: O={row['Open']:.2f} H={row['High']:.2f} L={row['Low']:.2f} C={row['Close']:.2f} V={row['Volume']:,.0f}")

    lines.append("")
    lines.append("--- BUSINESS SUMMARY ---")
    lines.append(data.get("business_summary", "N/A")[:500])

    return "\n".join(lines)
