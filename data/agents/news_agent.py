"""
News Agent — fetches market news from Argaam RSS feeds and article scraping.

Data sources (priority order):
1. Argaam RSS feeds (free, no API key)
2. Argaam article pages (scrape for full text)
3. DuckDuckGo news search (existing web_search.py fallback)

Output: List of news items with title, source, URL, date, sentiment.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Argaam RSS feed URLs
ARGAAM_FEEDS = {
    "main": "https://www.argaam.com/en/rss/articles",
    "saudi_market": "https://www.argaam.com/en/rss/articles-category/30",
}


class NewsAgent(BaseAgent):
    """Fetches market news from Argaam and other sources."""

    name = "news"
    cache_ttl = 1800             # 30 minutes for news
    rate_limit = 0.25            # 1 request per 4 seconds (conservative for Argaam)
    max_retries = 2
    required_fields = []         # News returns a list, not a dict with required fields

    async def fetch(self, ticker: str, **kwargs) -> Optional[List[Dict]]:
        """
        Fetch news for a Tadawul stock.

        Returns list of news items, or None on failure.
        """
        all_news = []

        # Source 1: DuckDuckGo news search (most reliable)
        ddg_news = self._fetch_from_ddg_news(ticker)
        if ddg_news:
            all_news.extend(ddg_news)

        # Source 2: Argaam RSS (may be blocked — best effort)
        rss_news = await self._fetch_from_argaam_rss(ticker)
        if rss_news:
            all_news.extend(rss_news)

        # Source 3: Argaam company news page scraping
        if not rss_news:
            company_news = await self._fetch_from_argaam_company(ticker)
            if company_news:
                all_news.extend(company_news)

        # Source 4: Existing web_search.py (legacy fallback)
        if not all_news:
            legacy_news = self._fetch_from_web_search(ticker)
            if legacy_news:
                all_news.extend(legacy_news)

        # Deduplicate by title similarity
        all_news = self._deduplicate(all_news)

        # Sort by date (most recent first)
        all_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        return all_news[:20] if all_news else None

    def validate_output(self, data) -> bool:
        """News returns a list, so override validation."""
        return isinstance(data, list) and len(data) > 0

    async def _fetch_from_argaam_rss(self, ticker: str) -> List[Dict]:
        """Parse Argaam RSS feeds for relevant news. Uses feedparser directly (handles 403 better)."""
        return self._fetch_from_argaam_rss_sync(ticker)

    def _fetch_from_argaam_rss_sync(self, ticker: str) -> List[Dict]:
        """Parse Argaam RSS feeds using feedparser with browser-like headers."""
        try:
            import feedparser
            import urllib.request
        except ImportError:
            logger.error("feedparser not installed")
            return []

        items = []
        company_names = self._get_ticker_names(ticker)

        for feed_name, feed_url in ARGAAM_FEEDS.items():
            try:
                # Use urllib with browser headers to avoid 403
                req = urllib.request.Request(feed_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/rss+xml, application/xml, text/xml, */*",
                })
                response = urllib.request.urlopen(req, timeout=15)
                feed_data = response.read()
                feed = feedparser.parse(feed_data)

                for entry in feed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    is_relevant = any(
                        name.lower() in (title + " " + summary).lower()
                        for name in company_names
                    ) if company_names else True

                    if is_relevant:
                        items.append({
                            "title": title,
                            "source": f"argaam_{feed_name}",
                            "url": entry.get("link", ""),
                            "published_at": self._parse_rss_date(entry.get("published", "")),
                            "summary": self._clean_html(summary)[:500],
                            "tickers_mentioned": [ticker],
                            "category": self._classify_category(title),
                            "sentiment_score": None,
                        })

            except urllib.error.HTTPError as e:
                logger.warning(f"[news] Argaam RSS {feed_name} HTTP {e.code}")
            except Exception as e:
                logger.warning(f"[news] RSS error for {feed_name}: {type(e).__name__}: {e}")

        return items

    async def _fetch_from_argaam_company(self, ticker: str) -> List[Dict]:
        """Scrape Argaam company-specific news page."""
        try:
            from data.agents.scraper_utils import fetch_page, parse_html

            # Argaam uses company IDs that differ from Tadawul tickers
            # Try the search/company news endpoint
            url = f"https://www.argaam.com/en/company/companynews/marketid/3/companyid/{ticker}"
            html = await fetch_page(url, timeout=20.0)

            if not html:
                return []

            soup = parse_html(html)
            if not soup:
                return []

            items = []
            # Look for news article links on the page
            for article in soup.select("article, .news-item, .article-item, .list-item"):
                title_el = article.select_one("h2, h3, h4, a.title, .article-title")
                link_el = article.select_one("a[href]")
                date_el = article.select_one("time, .date, .article-date, span.time")

                if title_el:
                    title = title_el.get_text(strip=True)
                    url = link_el.get("href", "") if link_el else ""
                    if url and not url.startswith("http"):
                        url = f"https://www.argaam.com{url}"
                    date_str = date_el.get_text(strip=True) if date_el else ""

                    items.append({
                        "title": title,
                        "source": "argaam_company",
                        "url": url,
                        "published_at": date_str,
                        "summary": "",
                        "tickers_mentioned": [ticker],
                        "category": self._classify_category(title),
                        "sentiment_score": None,
                    })

            return items[:10]

        except Exception as e:
            logger.warning(f"[news] Argaam company scrape error for {ticker}: {e}")
            return []

    def _fetch_from_ddg_news(self, ticker: str) -> List[Dict]:
        """Fetch structured news from DuckDuckGo news search."""
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return []

        company_names = self._get_ticker_names(ticker)
        query = f"{company_names[0]} Saudi stock Tadawul" if company_names else f"Tadawul {ticker}"

        items = []
        try:
            with DDGS() as ddgs:
                results = ddgs.news(query, max_results=10, region="xa-ar")
                for r in results:
                    items.append({
                        "title": r.get("title", ""),
                        "source": "ddg_news",
                        "url": r.get("url", r.get("link", "")),
                        "published_at": r.get("date", r.get("published", "")),
                        "summary": r.get("body", r.get("snippet", ""))[:500],
                        "tickers_mentioned": [ticker],
                        "category": self._classify_category(r.get("title", "")),
                        "sentiment_score": None,
                    })
        except Exception as e:
            logger.warning(f"[news] DDG news search error: {e}")

        return items

    def _fetch_from_web_search(self, ticker: str) -> List[Dict]:
        """Legacy fallback: use existing web_search.py."""
        try:
            from data.web_search import search_company_news
            company_names = self._get_ticker_names(ticker)
            query = company_names[0] if company_names else f"Tadawul {ticker}"
            news_str = search_company_news(query, ticker)

            if not news_str:
                return []

            items = []
            for line in news_str.split("\n"):
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    items.append({
                        "title": line[2:].strip(),
                        "source": "web_search",
                        "url": "",
                        "published_at": "",
                        "summary": "",
                        "tickers_mentioned": [ticker],
                        "category": "general",
                        "sentiment_score": None,
                    })

            return items

        except Exception as e:
            logger.warning(f"[news] Web search fallback error: {e}")
            return []

    # ---- Helpers ----

    def _get_ticker_names(self, ticker: str) -> List[str]:
        """Get company names associated with a ticker for relevance matching."""
        # Known Tadawul ticker -> name mappings
        NAMES = {
            "2222": ["Saudi Aramco", "Aramco", "ارامكو"],
            "2010": ["SABIC", "سابك"],
            "1120": ["Al Rajhi", "الراجحي"],
            "7010": ["STC", "الاتصالات السعودية"],
            "2280": ["Almarai", "المراعي"],
            "1180": ["Al Inma", "الإنماء"],
            "2350": ["Saudi Kayan", "كيان السعودية"],
            "2060": ["National Industrialization", "التصنيع"],
            "4030": ["Bahri", "بحري"],
            "1010": ["Riyad Bank", "بنك الرياض"],
            "2020": ["SABIC Agri", "سابك للمغذيات"],
            "1150": ["Alinma Bank", "الإنماء"],
            "3060": ["United Electronics", "إكسترا"],
            "4200": ["Aldawaa", "الدواء"],
        }
        return NAMES.get(str(ticker), [str(ticker)])

    def _classify_category(self, title: str) -> str:
        """Simple rule-based news category classification."""
        title_lower = title.lower()
        if any(w in title_lower for w in ["dividend", "توزيع", "payout"]):
            return "dividend"
        if any(w in title_lower for w in ["earnings", "profit", "revenue", "ربح", "إيرادات"]):
            return "earnings"
        if any(w in title_lower for w in ["merger", "acquisition", "استحواذ"]):
            return "m_and_a"
        if any(w in title_lower for w in ["ipo", "listing", "إدراج"]):
            return "ipo"
        if any(w in title_lower for w in ["regulation", "cma", "هيئة"]):
            return "regulatory"
        if any(w in title_lower for w in ["oil", "opec", "نفط", "أوبك"]):
            return "commodities"
        return "general"

    def _parse_rss_date(self, date_str: str) -> str:
        """Parse RSS date formats into ISO format."""
        if not date_str:
            return ""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except Exception:
            return date_str

    def _clean_html(self, text: str) -> str:
        """Strip HTML tags from text."""
        return re.sub(r'<[^>]+>', '', text).strip()

    def _deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate news items by title similarity."""
        seen_titles = set()
        unique = []
        for item in items:
            title_key = item.get("title", "").lower().strip()[:60]
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(item)
        return unique
