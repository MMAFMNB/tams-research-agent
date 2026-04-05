"""
Prompt optimization through caching and section-based truncation.

Reduces token spend by:
1. Caching analysis responses (same ticker + action + day = cache hit)
2. Truncating market data to only sections relevant to each analysis type
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "cache"

# Which market data sections each analysis type actually needs
# Sections are delimited by "---" or "===" in the formatted prompt
SECTION_RELEVANCE = {
    "fundamental": [
        "CURRENT PRICE", "VALUATION", "EARNINGS", "PROFITABILITY",
        "BALANCE SHEET", "CASH FLOW", "BUSINESS SUMMARY", "FINANCIAL STATEMENTS",
    ],
    "technical": [
        "CURRENT PRICE", "TECHNICAL INDICATORS", "RECENT PRICE ACTION",
        "MOVING AVERAGES", "RSI", "MACD",
    ],
    "dividend": [
        "CURRENT PRICE", "DIVIDENDS", "DIVIDEND", "CASH FLOW",
        "EARNINGS", "PAYOUT",
    ],
    "earnings": [
        "CURRENT PRICE", "EARNINGS", "REVENUE", "PROFITABILITY",
        "FINANCIAL STATEMENTS", "GROWTH",
    ],
    "risk": [
        "CURRENT PRICE", "VALUATION", "BALANCE SHEET", "RISK",
        "BETA", "VOLATILITY", "DEBT",
    ],
    "sector": [
        "CURRENT PRICE", "VALUATION", "BUSINESS SUMMARY", "SECTOR",
    ],
    "news_impact": [
        "CURRENT PRICE",
    ],
    "war_impact": [
        "CURRENT PRICE", "BUSINESS SUMMARY",
    ],
    "executive_summary": [],  # Needs everything — no truncation
    "morning_brief": [
        "CURRENT PRICE",
    ],
}


def get_or_generate(
    cache_key: str,
    generate_fn: Callable[[], str],
    ttl_hours: int = 12,
) -> str:
    """
    Return cached result if fresh, otherwise generate and cache.

    Args:
        cache_key: Unique key (e.g., "2222_fundamental_20260405")
        generate_fn: Function that produces the result when cache misses
        ttl_hours: Cache time-to-live in hours

    Returns:
        The result string (from cache or freshly generated)
    """
    cached = _read_cache(cache_key)
    if cached and not _is_expired(cached, ttl_hours):
        logger.info(f"Cache HIT: {cache_key}")
        return cached["content"]

    logger.info(f"Cache MISS: {cache_key}")
    result = generate_fn()

    if result:
        _write_cache(cache_key, result)

    return result


def make_cache_key(ticker: str, action: str, date: Optional[str] = None) -> str:
    """Generate a standardized cache key."""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    return f"{ticker}_{action}_{date}"


def truncate_market_data(full_data: str, action: str) -> str:
    """
    Trim market data to only sections relevant for the given analysis type.

    This can reduce prompt tokens by 30-50% for specialized analysis types.
    """
    relevant_keywords = SECTION_RELEVANCE.get(action)

    # If no relevance filter defined (e.g., executive_summary), return full data
    if relevant_keywords is None or len(relevant_keywords) == 0:
        return full_data

    # Split by section separators (--- or === or ## headers)
    sections = re.split(r'(?m)^(?:---+|===+|\#{2,}\s)', full_data)

    if len(sections) <= 1:
        return full_data

    kept = []
    for section in sections:
        section_upper = section.upper()[:200]  # Check first 200 chars for keywords
        if any(kw in section_upper for kw in relevant_keywords):
            kept.append(section)

    if not kept:
        return full_data

    truncated = "\n---\n".join(kept)
    reduction = 1 - (len(truncated) / max(len(full_data), 1))
    if reduction > 0.05:
        logger.info(f"Truncated {action} prompt by {reduction:.0%} ({len(full_data)} -> {len(truncated)} chars)")

    return truncated


def deduplicate_news(news: str, max_items: int = 10) -> str:
    """Limit news items to prevent prompt bloat."""
    if not news:
        return news

    lines = news.split("\n")
    # Simple heuristic: each news item is ~4 lines (title, source, date, summary)
    max_lines = max_items * 4 + 5  # +5 for headers
    if len(lines) <= max_lines:
        return news

    truncated = "\n".join(lines[:max_lines])
    logger.info(f"Truncated news from {len(lines)} to {max_lines} lines")
    return truncated


# --- Cache internals ---

def _read_cache(key: str) -> Optional[dict]:
    """Read a cached entry."""
    path = CACHE_DIR / f"{_safe_filename(key)}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Cache read error for {key}: {e}")
        return None


def _write_cache(key: str, content: str):
    """Write a cache entry."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_safe_filename(key)}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "key": key,
                "content": content,
                "cached_at": datetime.now().isoformat(),
            }, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Cache write error for {key}: {e}")


def _is_expired(cached: dict, ttl_hours: int) -> bool:
    """Check if a cache entry has expired."""
    try:
        cached_at = datetime.fromisoformat(cached["cached_at"])
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        return age_hours > ttl_hours
    except (KeyError, ValueError):
        return True


def _safe_filename(key: str) -> str:
    """Convert a cache key to a safe filename."""
    # Use hash for safety but keep key prefix readable
    prefix = re.sub(r'[^a-zA-Z0-9_]', '_', key)[:50]
    suffix = hashlib.md5(key.encode()).hexdigest()[:8]
    return f"{prefix}_{suffix}"
