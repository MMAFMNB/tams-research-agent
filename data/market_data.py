"""Fetch market data with Twelve Data (primary) and yfinance (fallback).

Provides current prices, 5-year audited financials (income statement,
balance sheet, cash flow), and technical indicators for Saudi-listed
and global equities.

Data source priority:
  1. Twelve Data API (reliable, Saudi Exchange supported on paid plans)
  2. yfinance / Yahoo Finance (free fallback, rate-limit prone)
"""

import os
import time
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

# --- Twelve Data Setup ---
_TD_KEY = None
_td_client = None

def _get_td_client():
    """Lazy-init Twelve Data client."""
    global _TD_KEY, _td_client
    if _td_client is not None:
        return _td_client
    try:
        # Try Streamlit secrets first, then env
        try:
            import streamlit as st
            _TD_KEY = st.secrets.get("TWELVE_DATA_API_KEY", os.getenv("TWELVE_DATA_API_KEY", ""))
        except Exception:
            _TD_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

        if _TD_KEY:
            from twelvedata import TDClient
            _td_client = TDClient(apikey=_TD_KEY)
            print(f"[TWELVE_DATA] Client initialized (key: ...{_TD_KEY[-4:]})")
            return _td_client
    except ImportError:
        print("[TWELVE_DATA] twelvedata package not installed, using yfinance only")
    except Exception as e:
        print(f"[TWELVE_DATA] Init error: {e}")
    return None


def _td_ticker(ticker: str) -> str:
    """Convert yfinance-style ticker to Twelve Data format.
    yfinance: 2010.SR → Twelve Data: 2010 (exchange handled separately)
    """
    return ticker.replace(".SR", "")


def _is_saudi(ticker: str) -> bool:
    return ticker.endswith(".SR") or ticker.replace(".SR", "").isdigit()


# ==========================================================
# TWELVE DATA FETCHERS
# ==========================================================

def _td_fetch_quote(ticker: str) -> dict:
    """Fetch real-time quote from Twelve Data. Returns dict or empty dict on failure."""
    td = _get_td_client()
    if not td:
        return {}
    try:
        symbol = _td_ticker(ticker)
        params = {"symbol": symbol}
        if _is_saudi(ticker):
            params["exchange"] = "TADAWUL"
        data = td.quote(**params).as_json()
        if isinstance(data, dict) and data.get("symbol"):
            print(f"[TWELVE_DATA] Quote OK for {symbol}")
            return data
        print(f"[TWELVE_DATA] Quote empty/error for {symbol}: {data}")
        return {}
    except Exception as e:
        print(f"[TWELVE_DATA] Quote error for {ticker}: {e}")
        return {}


def _td_fetch_time_series(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch OHLCV time series from Twelve Data."""
    td = _get_td_client()
    if not td:
        return pd.DataFrame()
    try:
        symbol = _td_ticker(ticker)
        # Map period to outputsize (trading days)
        period_map = {"1y": 252, "2y": 504, "5y": 1260, "10y": 2520}
        outputsize = period_map.get(period, 1260)

        params = {"symbol": symbol, "interval": "1day", "outputsize": outputsize}
        if _is_saudi(ticker):
            params["exchange"] = "TADAWUL"

        ts = td.time_series(**params)
        df = ts.as_pandas()
        if df is not None and not df.empty:
            # Standardize column names to match yfinance format
            col_map = {"open": "Open", "high": "High", "low": "Low",
                       "close": "Close", "volume": "Volume"}
            df = df.rename(columns=col_map)
            print(f"[TWELVE_DATA] Time series OK for {symbol}: {len(df)} rows")
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"[TWELVE_DATA] Time series error for {ticker}: {e}")
        return pd.DataFrame()


def _td_fetch_statistics(ticker: str) -> dict:
    """Fetch key statistics/fundamentals from Twelve Data."""
    td = _get_td_client()
    if not td:
        return {}
    try:
        import requests
        symbol = _td_ticker(ticker)
        exchange = "&exchange=TADAWUL" if _is_saudi(ticker) else ""
        url = f"https://api.twelvedata.com/statistics?symbol={symbol}{exchange}&apikey={_TD_KEY}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if "statistics" in data or "valuations_metrics" in data:
                print(f"[TWELVE_DATA] Statistics OK for {symbol}")
                return data
        return {}
    except Exception as e:
        print(f"[TWELVE_DATA] Statistics error for {ticker}: {e}")
        return {}


# ==========================================================
# YFINANCE FETCHERS (fallback)
# ==========================================================

def _yf_fetch_stock_data(ticker: str) -> dict:
    """Fetch stock info from yfinance with retry logic."""
    stock = yf.Ticker(ticker)
    info = {}
    for attempt in range(3):
        try:
            info = stock.info or {}
            break
        except Exception as err:
            err_str = str(err).lower()
            if "rate" in err_str or "too many" in err_str or "429" in err_str:
                print(f"[YFINANCE] Rate limited on {ticker}, attempt {attempt+1}/3, waiting...")
                time.sleep(5 * (attempt + 1))
            else:
                print(f"[YFINANCE] Error fetching {ticker}: {err}")
                break
    return info


def _yf_fetch_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch price history from yfinance with retry."""
    stock = yf.Ticker(ticker)
    for attempt in range(3):
        try:
            return stock.history(period=period)
        except Exception as err:
            err_str = str(err).lower()
            if "rate" in err_str or "too many" in err_str or "429" in err_str:
                print(f"[YFINANCE] Rate limited on {ticker} history, attempt {attempt+1}/3")
                time.sleep(5 * (attempt + 1))
            else:
                print(f"[YFINANCE] Error fetching {ticker} history: {err}")
                break
    return pd.DataFrame()


# ==========================================================
# PUBLIC API — used by app.py
# ==========================================================

def fetch_stock_data(ticker: str, collector=None) -> dict:
    """Fetch comprehensive stock data. Twelve Data first, yfinance fallback."""
    is_tadawul = _is_saudi(ticker)

    # --- Try Twelve Data quote ---
    td_quote = _td_fetch_quote(ticker)
    td_stats = {}
    if td_quote:
        td_stats = _td_fetch_statistics(ticker)

    # --- Fallback to yfinance ---
    yf_info = {}
    if not td_quote:
        print(f"[DATA] Twelve Data unavailable for {ticker}, trying yfinance...")
        yf_info = _yf_fetch_stock_data(ticker)

    # --- Merge data (prefer Twelve Data) ---
    def _get(*keys, default=None):
        """Try Twelve Data quote, then stats, then yfinance."""
        for key in keys:
            for source in [td_quote, td_stats, yf_info]:
                val = source.get(key)
                if val is not None and val != "" and val != 0:
                    return val
        return default

    def _float(val, default=0):
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    name = _get("name", "longName", "shortName", default=ticker)

    if collector:
        source_name = "Twelve Data" if td_quote else "Yahoo Finance"
        collector.add(
            source_type="market_data",
            title=f"{source_name} - {name} ({ticker}) Real-time Quote",
            url=f"https://finance.yahoo.com/quote/{ticker}",
            description="Live stock price, valuation metrics, and company overview",
        )

    data = {
        "ticker": ticker,
        "name": name,
        "sector": _get("sector", default="N/A"),
        "industry": _get("industry", default="N/A"),
        "currency": _get("currency", default="SAR" if is_tadawul else "USD"),
        "exchange": _get("exchange", default="SAU" if is_tadawul else ""),
        "is_tadawul": is_tadawul,
        "current_price": _float(_get("close", "currentPrice", "regularMarketPrice")),
        "previous_close": _float(_get("previous_close", "previousClose", "regularMarketPreviousClose")),
        "open_price": _float(_get("open", "regularMarketOpen")),
        "day_high": _float(_get("high", "dayHigh", "regularMarketDayHigh")),
        "day_low": _float(_get("low", "dayLow", "regularMarketDayLow")),
        "market_cap": _float(_get("market_cap", "marketCap")),
        "enterprise_value": _float(_get("enterpriseValue")),
        "shares_outstanding": _float(_get("sharesOutstanding")),
    }

    # Valuation metrics
    data["pe_ratio"] = _float(_get("pe", "trailingPE"), None)
    data["forward_pe"] = _float(_get("forwardPE"), None)
    data["pb_ratio"] = _float(_get("priceToBook"), None)
    data["ps_ratio"] = _float(_get("priceToSalesTrailing12Months"), None)
    data["ev_ebitda"] = _float(_get("enterpriseToEbitda"), None)
    data["ev_revenue"] = _float(_get("enterpriseToRevenue"), None)
    data["peg_ratio"] = _float(_get("pegRatio"), None)

    # Earnings
    data["eps_ttm"] = _float(_get("eps", "trailingEps"), None)
    data["eps_forward"] = _float(_get("forwardEps"), None)
    data["earnings_growth"] = _float(_get("earningsGrowth"), None)
    data["revenue_growth"] = _float(_get("revenueGrowth"), None)

    # Financials
    data["revenue"] = _float(_get("totalRevenue"))
    data["gross_margins"] = _float(_get("grossMargins"), None)
    data["operating_margins"] = _float(_get("operatingMargins"), None)
    data["profit_margins"] = _float(_get("profitMargins"), None)
    data["ebitda"] = _float(_get("ebitda"))
    data["total_debt"] = _float(_get("totalDebt"))
    data["total_cash"] = _float(_get("totalCash"))
    data["debt_to_equity"] = _float(_get("debtToEquity"), None)
    data["current_ratio"] = _float(_get("currentRatio"), None)
    data["quick_ratio"] = _float(_get("quickRatio"), None)
    data["free_cash_flow"] = _float(_get("freeCashflow"))
    data["operating_cash_flow"] = _float(_get("operatingCashflow"))
    data["return_on_equity"] = _float(_get("returnOnEquity"), None)
    data["return_on_assets"] = _float(_get("returnOnAssets"), None)
    data["book_value"] = _float(_get("bookValue"), None)

    # Dividends
    data["dividend_rate"] = _float(_get("dividendRate"), None)
    data["dividend_yield"] = _float(_get("dividendYield"), None)
    data["payout_ratio"] = _float(_get("payoutRatio"), None)
    data["ex_dividend_date"] = _get("exDividendDate")
    data["five_year_avg_dividend_yield"] = _float(_get("fiveYearAvgDividendYield"), None)

    # Risk metrics
    data["beta"] = _float(_get("beta"), None)
    data["fifty_two_week_high"] = _float(_get("fifty_two_week_high", "fiftyTwoWeekHigh"), None)
    data["fifty_two_week_low"] = _float(_get("fifty_two_week_low", "fiftyTwoWeekLow"), None)
    data["fifty_day_avg"] = _float(_get("fiftyDayAverage"), None)
    data["two_hundred_day_avg"] = _float(_get("twoHundredDayAverage"), None)
    data["avg_volume"] = _float(_get("average_volume", "averageVolume"), None)

    data["business_summary"] = _get("longBusinessSummary", default="")

    return data


def fetch_price_history(ticker: str, period: str = "5y", collector=None) -> pd.DataFrame:
    """Fetch historical price data. Twelve Data first, yfinance fallback."""
    # Try Twelve Data
    df = _td_fetch_time_series(ticker, period)

    # Fallback to yfinance
    if df.empty:
        print(f"[DATA] Twelve Data history unavailable for {ticker}, trying yfinance...")
        df = _yf_fetch_history(ticker, period)

    if collector:
        source = "Twelve Data" if not df.empty and _get_td_client() else "Yahoo Finance"
        collector.add(
            source_type="market_data",
            title=f"{source} - {ticker} Historical Prices ({period})",
            url=f"https://finance.yahoo.com/quote/{ticker}/history/",
            description=f"OHLCV price data, {period} period",
        )
    return df


def fetch_financials(ticker: str, collector=None) -> dict:
    """Fetch 5-year audited financial statements (yfinance — Twelve Data fundamentals
    require higher-tier plan)."""
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

    try:
        income = stock.income_stmt
        if income is not None and not income.empty:
            result["income_statement"] = income.to_dict()
            result["years_available"] = max(result["years_available"], len(income.columns))
    except Exception:
        pass

    try:
        balance = stock.balance_sheet
        if balance is not None and not balance.empty:
            result["balance_sheet"] = balance.to_dict()
            result["years_available"] = max(result["years_available"], len(balance.columns))
    except Exception:
        pass

    try:
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            result["cash_flow"] = cashflow.to_dict()
            result["years_available"] = max(result["years_available"], len(cashflow.columns))
    except Exception:
        pass

    try:
        q_income = stock.quarterly_income_stmt
        if q_income is not None and not q_income.empty:
            result["quarterly_income"] = q_income.to_dict()
    except Exception:
        pass

    return result


def fetch_dividend_history(ticker: str, collector=None) -> pd.DataFrame:
    """Fetch full dividend payment history (yfinance)."""
    stock = yf.Ticker(ticker)
    dividends = pd.Series(dtype=float)
    for attempt in range(3):
        try:
            dividends = stock.dividends
            break
        except Exception as err:
            err_str = str(err).lower()
            if "rate" in err_str or "too many" in err_str or "429" in err_str:
                print(f"[YFINANCE] Rate limited on {ticker} dividends, attempt {attempt+1}/3")
                time.sleep(5 * (attempt + 1))
            else:
                print(f"[YFINANCE] Error fetching {ticker} dividends: {err}")
                break
    if collector:
        collector.add(
            source_type="yahoo_finance",
            title=f"Yahoo Finance - {ticker} Dividend History",
            url=f"https://finance.yahoo.com/quote/{ticker}/history/?filter=div",
            description="Historical dividend payments and dates",
        )
    return dividends


# ==========================================================
# TECHNICAL INDICATORS
# ==========================================================

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


# ==========================================================
# PROMPT FORMATTING
# ==========================================================

def _format_financial_table(financials: dict, statement_type: str) -> str:
    """Format a financial statement dict into a readable table for AI prompts."""
    data = financials.get(statement_type, {})
    if not data:
        return f"  {statement_type}: No data available\n"

    lines = []
    periods = sorted(data.keys())

    year_labels = []
    for p in periods:
        if hasattr(p, "strftime"):
            year_labels.append(p.strftime("%Y"))
        else:
            year_labels.append(str(p)[:4])

    if periods:
        row_keys = list(data[periods[0]].keys())
    else:
        return ""

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

    target_keys = priority_metrics.get(statement_type, row_keys[:15])
    shown_keys = [k for k in target_keys if k in row_keys]
    remaining = [k for k in row_keys if k not in shown_keys][:10]
    shown_keys.extend(remaining)

    if not shown_keys:
        return ""

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

        display_key = key.replace("_", " ")
        import re
        display_key = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', display_key)
        lines.append(f"  {display_key:<45} " + " ".join(values))

    return "\n".join(lines)


def format_market_data_for_prompt(data: dict, technicals: dict, hist: pd.DataFrame,
                                  financials: dict = None) -> str:
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
    exchange_label = "Tadawul (Saudi Exchange)" if data.get("is_tadawul") else data.get("exchange", "")
    lines.append(f"=== STOCK DATA: {data['name']} ({data['ticker']}) ===")
    lines.append(f"Exchange: {exchange_label} | Sector: {data['sector']} | Industry: {data['industry']}")
    lines.append(f"Currency: {data['currency']}")
    lines.append("")

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

    if technicals:
        lines.append("--- TECHNICAL INDICATORS ---")
        lines.append(f"MA(20): {fmt(technicals.get('ma_20'))} | MA(50): {fmt(technicals.get('ma_50'))}")
        lines.append(f"MA(100): {fmt(technicals.get('ma_100'))} | MA(200): {fmt(technicals.get('ma_200'))}")
        lines.append(f"RSI(14): {fmt(technicals.get('rsi_14'))}")
        lines.append(f"MACD: {fmt(technicals.get('macd_line'))} | Signal: {fmt(technicals.get('macd_signal'))} | Hist: {fmt(technicals.get('macd_histogram'))}")
        lines.append(f"Bollinger: {fmt(technicals.get('bb_lower'))} / {fmt(technicals.get('bb_middle'))} / {fmt(technicals.get('bb_upper'))}")
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
