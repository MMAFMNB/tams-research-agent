"""Fetch market data from Yahoo Finance for stock analysis."""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


def fetch_stock_data(ticker: str) -> dict:
    """Fetch comprehensive stock data for analysis."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    # Price and basic info
    data = {
        "ticker": ticker,
        "name": info.get("longName", info.get("shortName", ticker)),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "currency": info.get("currency", "SAR"),
        "exchange": info.get("exchange", ""),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
        "market_cap": info.get("marketCap", 0),
        "enterprise_value": info.get("enterpriseValue", 0),
    }

    # Valuation metrics
    data["pe_ratio"] = info.get("trailingPE")
    data["forward_pe"] = info.get("forwardPE")
    data["pb_ratio"] = info.get("priceToBook")
    data["ps_ratio"] = info.get("priceToSalesTrailing12Months")
    data["ev_ebitda"] = info.get("enterpriseToEbitda")
    data["peg_ratio"] = info.get("pegRatio")

    # Earnings
    data["eps_ttm"] = info.get("trailingEps")
    data["eps_forward"] = info.get("forwardEps")
    data["earnings_growth"] = info.get("earningsGrowth")
    data["revenue_growth"] = info.get("revenueGrowth")

    # Financials
    data["revenue"] = info.get("totalRevenue", 0)
    data["gross_margins"] = info.get("grossMargins")
    data["operating_margins"] = info.get("operatingMargins")
    data["profit_margins"] = info.get("profitMargins")
    data["total_debt"] = info.get("totalDebt", 0)
    data["total_cash"] = info.get("totalCash", 0)
    data["debt_to_equity"] = info.get("debtToEquity")
    data["current_ratio"] = info.get("currentRatio")
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

    # Company description
    data["business_summary"] = info.get("longBusinessSummary", "")

    return data


def fetch_price_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Fetch historical price data."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    return hist


def fetch_financials(ticker: str) -> dict:
    """Fetch financial statements."""
    stock = yf.Ticker(ticker)
    result = {}

    try:
        income = stock.income_stmt
        if income is not None and not income.empty:
            result["income_statement"] = income.to_dict()
    except Exception:
        result["income_statement"] = {}

    try:
        balance = stock.balance_sheet
        if balance is not None and not balance.empty:
            result["balance_sheet"] = balance.to_dict()
    except Exception:
        result["balance_sheet"] = {}

    try:
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            result["cash_flow"] = cashflow.to_dict()
    except Exception:
        result["cash_flow"] = {}

    return result


def fetch_dividend_history(ticker: str) -> pd.DataFrame:
    """Fetch dividend payment history."""
    stock = yf.Ticker(ticker)
    dividends = stock.dividends
    return dividends


def calculate_technical_indicators(hist: pd.DataFrame) -> dict:
    """Calculate key technical indicators from price history."""
    if hist.empty:
        return {}

    close = hist["Close"]

    indicators = {}

    # Moving averages
    indicators["ma_20"] = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
    indicators["ma_50"] = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
    indicators["ma_100"] = close.rolling(100).mean().iloc[-1] if len(close) >= 100 else None
    indicators["ma_200"] = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

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


def format_market_data_for_prompt(data: dict, technicals: dict, hist: pd.DataFrame) -> str:
    """Format all market data into a structured string for the AI prompt."""

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
    lines.append(f"=== STOCK DATA: {data['name']} ({data['ticker']}) ===")
    lines.append(f"Sector: {data['sector']} | Industry: {data['industry']}")
    lines.append(f"Exchange: {data['exchange']} | Currency: {data['currency']}")
    lines.append("")

    lines.append("--- PRICE & VALUATION ---")
    lines.append(f"Current Price: {fmt(data['current_price'])}")
    lines.append(f"Market Cap: {fmt_large(data['market_cap'])}")
    lines.append(f"P/E (TTM): {fmt(data['pe_ratio'])}x")
    lines.append(f"Forward P/E: {fmt(data['forward_pe'])}x")
    lines.append(f"P/B: {fmt(data['pb_ratio'])}x")
    lines.append(f"P/S: {fmt(data['ps_ratio'])}x")
    lines.append(f"EV/EBITDA: {fmt(data['ev_ebitda'])}x")
    lines.append(f"PEG: {fmt(data['peg_ratio'])}")
    lines.append("")

    lines.append("--- EARNINGS & GROWTH ---")
    lines.append(f"EPS (TTM): {fmt(data['eps_ttm'])}")
    lines.append(f"EPS (Forward): {fmt(data['eps_forward'])}")
    lines.append(f"Earnings Growth: {fmt(data['earnings_growth'], suffix='%') if data.get('earnings_growth') else 'N/A'}")
    lines.append(f"Revenue Growth: {fmt(data['revenue_growth'], suffix='%') if data.get('revenue_growth') else 'N/A'}")
    lines.append(f"Revenue: {fmt_large(data['revenue'])}")
    lines.append("")

    lines.append("--- PROFITABILITY ---")
    lines.append(f"Gross Margin: {fmt(data.get('gross_margins'), suffix='%') if data.get('gross_margins') else 'N/A'}")
    lines.append(f"Operating Margin: {fmt(data.get('operating_margins'), suffix='%') if data.get('operating_margins') else 'N/A'}")
    lines.append(f"Net Margin: {fmt(data.get('profit_margins'), suffix='%') if data.get('profit_margins') else 'N/A'}")
    lines.append(f"ROE: {fmt(data.get('return_on_equity'), suffix='%') if data.get('return_on_equity') else 'N/A'}")
    lines.append(f"ROA: {fmt(data.get('return_on_assets'), suffix='%') if data.get('return_on_assets') else 'N/A'}")
    lines.append("")

    lines.append("--- BALANCE SHEET ---")
    lines.append(f"Total Debt: {fmt_large(data['total_debt'])}")
    lines.append(f"Total Cash: {fmt_large(data['total_cash'])}")
    lines.append(f"Debt/Equity: {fmt(data['debt_to_equity'])}")
    lines.append(f"Current Ratio: {fmt(data['current_ratio'])}")
    lines.append(f"Book Value/Share: {fmt(data['book_value'])}")
    lines.append("")

    lines.append("--- CASH FLOW ---")
    lines.append(f"Free Cash Flow: {fmt_large(data['free_cash_flow'])}")
    lines.append(f"Operating Cash Flow: {fmt_large(data['operating_cash_flow'])}")
    lines.append("")

    lines.append("--- DIVIDENDS ---")
    lines.append(f"Dividend Rate: {fmt(data['dividend_rate'])}")
    lines.append(f"Dividend Yield: {fmt(data['dividend_yield'], suffix='%') if data.get('dividend_yield') else 'N/A'}")
    lines.append(f"Payout Ratio: {fmt(data['payout_ratio'], suffix='%') if data.get('payout_ratio') else 'N/A'}")
    lines.append(f"5Y Avg Yield: {fmt(data['five_year_avg_dividend_yield'], suffix='%') if data.get('five_year_avg_dividend_yield') else 'N/A'}")
    lines.append("")

    lines.append("--- RISK METRICS ---")
    lines.append(f"Beta: {fmt(data['beta'])}")
    lines.append(f"52W High: {fmt(data['fifty_two_week_high'])}")
    lines.append(f"52W Low: {fmt(data['fifty_two_week_low'])}")
    lines.append(f"50D Avg: {fmt(data['fifty_day_avg'])}")
    lines.append(f"200D Avg: {fmt(data['two_hundred_day_avg'])}")
    lines.append("")

    if technicals:
        lines.append("--- TECHNICAL INDICATORS ---")
        lines.append(f"MA(20): {fmt(technicals.get('ma_20'))}")
        lines.append(f"MA(50): {fmt(technicals.get('ma_50'))}")
        lines.append(f"MA(100): {fmt(technicals.get('ma_100'))}")
        lines.append(f"MA(200): {fmt(technicals.get('ma_200'))}")
        lines.append(f"RSI(14): {fmt(technicals.get('rsi_14'))}")
        lines.append(f"MACD Line: {fmt(technicals.get('macd_line'))}")
        lines.append(f"MACD Signal: {fmt(technicals.get('macd_signal'))}")
        lines.append(f"MACD Histogram: {fmt(technicals.get('macd_histogram'))}")
        lines.append(f"BB Upper: {fmt(technicals.get('bb_upper'))}")
        lines.append(f"BB Middle: {fmt(technicals.get('bb_middle'))}")
        lines.append(f"BB Lower: {fmt(technicals.get('bb_lower'))}")
        lines.append(f"Volume Ratio (vs 20D avg): {fmt(technicals.get('volume_ratio'))}")
        lines.append("")

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
