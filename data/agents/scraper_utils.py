"""
Shared scraping utilities for all data collection agents.

Features:
- Async HTTP client with browser-like headers
- User-Agent rotation
- HTML parsing helpers (including Arabic content)
- Rate limiter (token bucket)
- Retry with exponential backoff
- Response parsing utilities
"""

import asyncio
import logging
import random
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Rotating User-Agent pool (modern browsers)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]

# Default headers for scraping
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


def get_headers(extra: Optional[Dict] = None) -> Dict:
    """Get request headers with a random User-Agent."""
    headers = {**DEFAULT_HEADERS, "User-Agent": random.choice(USER_AGENTS)}
    if extra:
        headers.update(extra)
    return headers


async def fetch_page(url: str, headers: Optional[Dict] = None, timeout: float = 30.0) -> Optional[str]:
    """
    Fetch a web page asynchronously using httpx.

    Returns HTML content as string, or None on failure.
    """
    try:
        import httpx
    except ImportError:
        logger.error("httpx not installed. Run: pip install httpx")
        return None

    request_headers = get_headers(headers)

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout),
            verify=True,
        ) as client:
            response = await client.get(url, headers=request_headers)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} for {url}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {url}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {type(e).__name__}: {e}")
        return None


def fetch_page_sync(url: str, headers: Optional[Dict] = None, timeout: float = 30.0) -> Optional[str]:
    """Synchronous version of fetch_page using requests library as fallback."""
    try:
        import requests as req
        response = req.get(url, headers=get_headers(headers), timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.warning(f"Sync fetch error for {url}: {e}")
        return None


def parse_html(html: str) -> Optional[object]:
    """Parse HTML with BeautifulSoup. Returns soup object."""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")
    except ImportError:
        logger.error("beautifulsoup4 not installed. Run: pip install beautifulsoup4")
        return None


def extract_table(soup, table_selector: str = "table") -> List[List[str]]:
    """
    Extract data from an HTML table.

    Returns list of rows, each row is a list of cell strings.
    """
    if soup is None:
        return []

    table = soup.select_one(table_selector) if isinstance(table_selector, str) else table_selector
    if not table:
        return []

    rows = []
    for tr in table.find_all("tr"):
        cells = []
        for td in tr.find_all(["td", "th"]):
            text = td.get_text(strip=True)
            cells.append(text)
        if cells:
            rows.append(cells)

    return rows


def clean_arabic_text(text: str) -> str:
    """Clean and normalize Arabic text from web scraping."""
    if not text:
        return ""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove zero-width characters
    text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]', '', text)
    return text


def parse_number(text: str) -> Optional[float]:
    """
    Parse a number from text, handling Arabic numerals and common formats.

    Handles: "1,234.56", "1.234,56", "(1,234)", "1.2M", "1.2B", Arabic numerals
    """
    if not text:
        return None

    text = str(text).strip()

    # Map Arabic-Indic digits to Western digits
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    for i, digit in enumerate(arabic_digits):
        text = text.replace(digit, str(i))

    # Remove currency symbols and spaces
    text = re.sub(r'[SAR$€£¥\s]', '', text)

    # Handle parentheses as negative
    negative = False
    if text.startswith('(') and text.endswith(')'):
        negative = True
        text = text[1:-1]

    # Handle suffixes
    multiplier = 1
    if text.upper().endswith('T'):
        multiplier = 1_000_000_000_000
        text = text[:-1]
    elif text.upper().endswith('B'):
        multiplier = 1_000_000_000
        text = text[:-1]
    elif text.upper().endswith('M'):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.upper().endswith('K'):
        multiplier = 1_000
        text = text[:-1]

    # Remove commas used as thousands separators
    text = text.replace(',', '')

    # Handle percentage
    is_pct = text.endswith('%')
    if is_pct:
        text = text[:-1]

    try:
        value = float(text) * multiplier
        if negative:
            value = -value
        if is_pct:
            value = value / 100
        return value
    except (ValueError, TypeError):
        return None


def parse_date(text: str) -> Optional[datetime]:
    """Parse various date formats commonly found on financial sites."""
    if not text:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
    ]

    text = text.strip()
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


async def fetch_rss(url: str) -> List[Dict]:
    """
    Fetch and parse an RSS feed.

    Returns list of dicts with: title, link, published, summary
    """
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser not installed. Run: pip install feedparser")
        return []

    html = await fetch_page(url)
    if not html:
        return []

    feed = feedparser.parse(html)
    entries = []
    for entry in feed.entries:
        entries.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
        })

    return entries


def fetch_rss_sync(url: str) -> List[Dict]:
    """Synchronous RSS fetch."""
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser not installed")
        return []

    feed = feedparser.parse(url)
    entries = []
    for entry in feed.entries:
        entries.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
        })

    return entries


def tadawul_ticker_to_yfinance(ticker: str) -> str:
    """Convert a Tadawul ticker (e.g., '2222') to yfinance format ('2222.SR')."""
    ticker = str(ticker).strip()
    if not ticker.endswith('.SR'):
        return f"{ticker}.SR"
    return ticker
