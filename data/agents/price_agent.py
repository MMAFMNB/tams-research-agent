"""
Price Agent — fetches stock prices from Tadawul website with yfinance fallback.

Data sources (priority order):
1. saudiexchange.sa — Official Tadawul market watch (web scraping)
2. yfinance — Fallback using .SR suffix (e.g., 2222.SR)

Output: OHLCV price data, current quote, change percentage.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PriceAgent(BaseAgent):
    """Fetches stock price data from Tadawul and yfinance."""

    name = "price"
    cache_ttl = 300              # 5 minutes for real-time quotes
    rate_limit = 0.5             # 1 request per 2 seconds
    max_retries = 2
    required_fields = ["ticker", "close"]

    async def fetch(self, ticker: str, **kwargs) -> Optional[Dict]:
        """
        Fetch price data for a Tadawul stock.

        Args:
            ticker: Tadawul ticker (e.g., "2222")

        Returns:
            Dict with price data or None on failure.
        """
        # Try Tadawul scraping first
        result = await self._fetch_from_tadawul(ticker)
        if result and self.validate_output(result):
            return result

        # Fallback to yfinance
        logger.info(f"[price] Tadawul scrape failed for {ticker}, falling back to yfinance")
        result = self._fetch_from_yfinance(ticker)
        if result and self.validate_output(result):
            return result

        return None

    async def _fetch_from_tadawul(self, ticker: str) -> Optional[Dict]:
        """Scrape price data from saudiexchange.sa."""
        try:
            from data.agents.scraper_utils import fetch_page, parse_html, parse_number

            # Tadawul stock detail page
            url = f"https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/equities-trading/companies/{ticker}"
            html = await fetch_page(url, timeout=20.0)

            if not html:
                return None

            soup = parse_html(html)
            if not soup:
                return None

            # Try to extract price data from the page
            # Tadawul uses various class names for price display
            result = {"ticker": ticker, "source": "tadawul_scrape"}

            # Look for price data in common Tadawul page structures
            # The site uses a mix of static HTML and JS-rendered content
            for selector in [
                "span.lastTradePrice", "span.last-trade-price",
                "[data-field='lastTradePrice']", ".stock-price",
                "td.last-price", ".current-price",
            ]:
                el = soup.select_one(selector)
                if el:
                    price = parse_number(el.get_text())
                    if price and price > 0:
                        result["close"] = price
                        break

            # Look for change data
            for selector in [
                "span.changePercent", "span.change-percent",
                "[data-field='changePercent']", ".price-change-pct",
            ]:
                el = soup.select_one(selector)
                if el:
                    pct = parse_number(el.get_text())
                    if pct is not None:
                        result["change_pct"] = pct * 100 if abs(pct) < 1 else pct

            # Look for OHLV data in tables or structured elements
            field_map = {
                "open": ["open", "openPrice", "open-price"],
                "high": ["high", "highPrice", "high-price", "dayHigh"],
                "low": ["low", "lowPrice", "low-price", "dayLow"],
                "volume": ["volume", "totalVolume", "total-volume"],
            }

            for field, selectors in field_map.items():
                for sel in selectors:
                    el = soup.select_one(f"[data-field='{sel}']") or soup.select_one(f".{sel}")
                    if el:
                        val = parse_number(el.get_text())
                        if val is not None:
                            result[field] = val
                            break

            # Extract company name
            for selector in ["h1.company-name", "h1", ".stock-name", ".company-title"]:
                el = soup.select_one(selector)
                if el:
                    name = el.get_text(strip=True)
                    if name and len(name) < 100:
                        result["name"] = name
                        break

            if "close" in result:
                result["fetched_at"] = datetime.now().isoformat()
                return result

            logger.debug(f"[price] Could not extract price from Tadawul page for {ticker}")
            return None

        except Exception as e:
            logger.warning(f"[price] Tadawul scrape error for {ticker}: {e}")
            return None

    def _fetch_from_yfinance(self, ticker: str) -> Optional[Dict]:
        """Fetch price data from yfinance as fallback."""
        try:
            import yfinance as yf
            from data.agents.scraper_utils import tadawul_ticker_to_yfinance

            yf_ticker = tadawul_ticker_to_yfinance(ticker)
            stock = yf.Ticker(yf_ticker)

            # Get current quote
            info = stock.info or {}

            # Get recent history for OHLCV
            hist = stock.history(period="5d")

            result = {
                "ticker": ticker,
                "yf_ticker": yf_ticker,
                "source": "yfinance",
                "name": info.get("longName") or info.get("shortName") or ticker,
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "currency": info.get("currency", "SAR"),
                "close": info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"),
                "open": info.get("regularMarketOpen") or info.get("open"),
                "high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
                "low": info.get("regularMarketDayLow") or info.get("dayLow"),
                "volume": info.get("regularMarketVolume") or info.get("volume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "eps": info.get("trailingEps"),
                "beta": info.get("beta"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "fetched_at": datetime.now().isoformat(),
            }

            # Add recent price history
            if not hist.empty:
                result["history_5d"] = []
                for date, row in hist.tail(5).iterrows():
                    result["history_5d"].append({
                        "date": date.strftime("%Y-%m-%d"),
                        "open": round(row.get("Open", 0), 2),
                        "high": round(row.get("High", 0), 2),
                        "low": round(row.get("Low", 0), 2),
                        "close": round(row.get("Close", 0), 2),
                        "volume": int(row.get("Volume", 0)),
                    })
                # Use last close if no current price
                if not result["close"] and len(result["history_5d"]) > 0:
                    result["close"] = result["history_5d"][-1]["close"]

            # Calculate change percentage
            if result.get("close") and result.get("open") and result["open"] > 0:
                result["change_pct"] = round(
                    (result["close"] - result["open"]) / result["open"] * 100, 2
                )

            # Clean None values
            result = {k: v for k, v in result.items() if v is not None}

            if result.get("close"):
                return result

            logger.warning(f"[price] yfinance returned no price for {ticker}")
            return None

        except Exception as e:
            logger.warning(f"[price] yfinance error for {ticker}: {e}")
            return None
