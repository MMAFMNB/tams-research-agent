"""
Fundamentals Agent — fetches company financials from Argaam and yfinance.

Data sources (priority order):
1. Argaam company pages (web scraping)
2. yfinance financials (fallback)

Output: Financial statements, ratios, company profile.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from data.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class FundamentalsAgent(BaseAgent):
    """Fetches company fundamental data from Argaam and yfinance."""

    name = "fundamentals"
    cache_ttl = 86400            # 24 hours (fundamentals don't change intraday)
    rate_limit = 0.25            # 1 request per 4 seconds
    max_retries = 2
    required_fields = ["ticker"]

    async def fetch(self, ticker: str, **kwargs) -> Optional[Dict]:
        """
        Fetch fundamental data for a Tadawul stock.

        Returns dict with financials, ratios, and company profile.
        """
        # Try Argaam scraping first
        result = await self._fetch_from_argaam(ticker)
        if result and result.get("revenue") or result.get("pe_ratio"):
            return result

        # Fallback to yfinance
        logger.info(f"[fundamentals] Argaam scrape insufficient for {ticker}, using yfinance")
        yf_result = self._fetch_from_yfinance(ticker)
        if yf_result:
            # Merge Argaam partial data with yfinance
            if result:
                for k, v in yf_result.items():
                    if k not in result or result[k] is None:
                        result[k] = v
                return result
            return yf_result

        return result  # Return whatever Argaam gave us, even if partial

    async def _fetch_from_argaam(self, ticker: str) -> Optional[Dict]:
        """Scrape fundamental data from Argaam company page."""
        try:
            from data.agents.scraper_utils import fetch_page, parse_html, parse_number, extract_table

            # Argaam company overview
            url = f"https://www.argaam.com/en/company/companyoverview/marketid/3/companyid/{ticker}"
            html = await fetch_page(url, timeout=20.0)

            if not html:
                return None

            soup = parse_html(html)
            if not soup:
                return None

            result = {
                "ticker": ticker,
                "source": "argaam_scrape",
                "fetched_at": datetime.now().isoformat(),
            }

            # Extract company name
            name_el = soup.select_one("h1, .company-name, .stock-name")
            if name_el:
                result["name"] = name_el.get_text(strip=True)

            # Extract sector
            for el in soup.select(".sector, .company-sector, [data-field='sector']"):
                text = el.get_text(strip=True)
                if text and len(text) < 50:
                    result["sector"] = text
                    break

            # Extract key ratios from tables or data fields
            ratio_map = {
                "pe_ratio": ["p/e", "pe ratio", "price/earnings", "مكرر الربحية"],
                "pb_ratio": ["p/b", "pb ratio", "price/book", "مكرر القيمة الدفترية"],
                "dividend_yield": ["dividend yield", "عائد التوزيعات"],
                "eps": ["eps", "earnings per share", "ربحية السهم"],
                "market_cap": ["market cap", "القيمة السوقية"],
                "revenue": ["revenue", "الإيرادات", "sales"],
                "net_income": ["net income", "net profit", "صافي الربح"],
                "roe": ["roe", "return on equity"],
                "roa": ["roa", "return on assets"],
                "debt_to_equity": ["d/e", "debt/equity", "debt to equity"],
                "current_ratio": ["current ratio", "النسبة الجارية"],
                "payout_ratio": ["payout ratio", "نسبة التوزيع"],
            }

            # Method 1: Look for key-value pairs in tables
            for table in soup.select("table"):
                rows = extract_table(table)
                for row in rows:
                    if len(row) >= 2:
                        label = row[0].lower().strip()
                        value_text = row[-1].strip()
                        for field, keywords in ratio_map.items():
                            if any(kw in label for kw in keywords):
                                val = parse_number(value_text)
                                if val is not None:
                                    result[field] = val
                                    break

            # Method 2: Look for labeled spans/divs
            for el in soup.select("[class*='ratio'], [class*='metric'], [class*='financial'], dl dt, .data-label"):
                label_text = el.get_text(strip=True).lower()
                # Get the adjacent value element
                value_el = el.find_next_sibling() or el.find_next("span") or el.find_next("dd")
                if not value_el:
                    continue
                value_text = value_el.get_text(strip=True)

                for field, keywords in ratio_map.items():
                    if any(kw in label_text for kw in keywords):
                        val = parse_number(value_text)
                        if val is not None:
                            result[field] = val
                            break

            # Try to get financial statements page
            fin_result = await self._fetch_argaam_financials(ticker)
            if fin_result:
                result["financial_statements"] = fin_result

            return result

        except Exception as e:
            logger.warning(f"[fundamentals] Argaam scrape error for {ticker}: {e}")
            return None

    async def _fetch_argaam_financials(self, ticker: str) -> Optional[Dict]:
        """Scrape financial statements from Argaam."""
        try:
            from data.agents.scraper_utils import fetch_page, parse_html, extract_table, parse_number

            url = f"https://www.argaam.com/en/company/companyfinancials/marketid/3/companyid/{ticker}"
            html = await fetch_page(url, timeout=20.0)
            if not html:
                return None

            soup = parse_html(html)
            if not soup:
                return None

            statements = {}

            # Find financial tables
            for table in soup.select("table"):
                rows = extract_table(table)
                if len(rows) < 2:
                    continue

                # First row is usually headers (years)
                headers = rows[0]
                table_data = {}

                for row in rows[1:]:
                    if len(row) >= 2:
                        label = row[0].strip()
                        values = {}
                        for i, cell in enumerate(row[1:], 1):
                            if i < len(headers):
                                year = headers[i].strip()
                                val = parse_number(cell)
                                if val is not None:
                                    values[year] = val
                        if values:
                            table_data[label] = values

                if table_data:
                    # Classify the table type
                    labels = " ".join(table_data.keys()).lower()
                    if "revenue" in labels or "sales" in labels:
                        statements["income_statement"] = table_data
                    elif "total assets" in labels or "assets" in labels:
                        statements["balance_sheet"] = table_data
                    elif "operating" in labels and "cash" in labels:
                        statements["cash_flow"] = table_data
                    else:
                        statements.setdefault("other", {}).update(table_data)

            return statements if statements else None

        except Exception as e:
            logger.warning(f"[fundamentals] Argaam financials scrape error: {e}")
            return None

    def _fetch_from_yfinance(self, ticker: str) -> Optional[Dict]:
        """Fetch fundamental data from yfinance as fallback."""
        try:
            import yfinance as yf
            from data.agents.scraper_utils import tadawul_ticker_to_yfinance

            yf_ticker = tadawul_ticker_to_yfinance(ticker)
            stock = yf.Ticker(yf_ticker)
            info = stock.info or {}

            result = {
                "ticker": ticker,
                "yf_ticker": yf_ticker,
                "source": "yfinance",
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "eps": info.get("trailingEps"),
                "revenue": info.get("totalRevenue"),
                "net_income": info.get("netIncomeToCommon"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "gross_margins": info.get("grossMargins"),
                "operating_margins": info.get("operatingMargins"),
                "profit_margins": info.get("profitMargins"),
                "free_cashflow": info.get("freeCashflow"),
                "operating_cashflow": info.get("operatingCashflow"),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),
                "book_value": info.get("bookValue"),
                "payout_ratio": info.get("payoutRatio"),
                "business_summary": info.get("longBusinessSummary", "")[:500],
                "fetched_at": datetime.now().isoformat(),
            }

            # Get financial statements
            statements = {}
            try:
                income = stock.income_stmt
                if income is not None and not income.empty:
                    statements["income_statement"] = {
                        str(col.date()): {
                            str(idx): float(val) if val == val else None  # NaN check
                            for idx, val in income[col].items()
                        }
                        for col in income.columns[:4]  # Last 4 years
                    }
            except Exception:
                pass

            try:
                balance = stock.balance_sheet
                if balance is not None and not balance.empty:
                    statements["balance_sheet"] = {
                        str(col.date()): {
                            str(idx): float(val) if val == val else None
                            for idx, val in balance[col].items()
                        }
                        for col in balance.columns[:4]
                    }
            except Exception:
                pass

            try:
                cashflow = stock.cashflow
                if cashflow is not None and not cashflow.empty:
                    statements["cash_flow"] = {
                        str(col.date()): {
                            str(idx): float(val) if val == val else None
                            for idx, val in cashflow[col].items()
                        }
                        for col in cashflow.columns[:4]
                    }
            except Exception:
                pass

            if statements:
                result["financial_statements"] = statements

            # Clean None values
            result = {k: v for k, v in result.items() if v is not None}

            return result if result.get("ticker") else None

        except Exception as e:
            logger.warning(f"[fundamentals] yfinance error for {ticker}: {e}")
            return None
