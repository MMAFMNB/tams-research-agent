"""Lightweight market monitoring for watchlist tickers.

Checks price movements and flags significant changes.
Designed to be called on-demand from Streamlit (no Celery needed).
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

MONITOR_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "watchlist_data"
)
MONITOR_CACHE_FILE = os.path.join(MONITOR_CACHE_DIR, "monitor_cache.json")

# Alert thresholds
PRICE_CHANGE_THRESHOLD = 3.0    # % daily change to flag
VOLUME_SPIKE_THRESHOLD = 2.0    # multiplier vs 20-day avg to flag
CACHE_TTL_MINUTES = 15          # don't re-fetch within this window


def _load_cache() -> dict:
    os.makedirs(MONITOR_CACHE_DIR, exist_ok=True)
    if os.path.exists(MONITOR_CACHE_FILE):
        try:
            with open(MONITOR_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"tickers": {}, "last_full_scan": None}


def _save_cache(cache: dict):
    os.makedirs(MONITOR_CACHE_DIR, exist_ok=True)
    with open(MONITOR_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _is_stale(timestamp_str: Optional[str]) -> bool:
    """Check if a cached timestamp is older than TTL."""
    if not timestamp_str:
        return True
    try:
        ts = datetime.fromisoformat(timestamp_str)
        return (datetime.now() - ts).total_seconds() > CACHE_TTL_MINUTES * 60
    except (ValueError, TypeError):
        return True


def _fetch_ticker_data(ticker: str) -> dict:
    """Fetch fresh data for a single ticker from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose", 0)
        volume = info.get("volume") or info.get("regularMarketVolume", 0)
        avg_volume = info.get("averageVolume", 0)
        name = info.get("longName") or info.get("shortName", ticker)

        price_change = 0
        price_change_pct = 0
        if previous_close and previous_close > 0:
            price_change = current_price - previous_close
            price_change_pct = (price_change / previous_close) * 100

        volume_ratio = (volume / avg_volume) if avg_volume > 0 else 0

        alerts = []
        if abs(price_change_pct) >= PRICE_CHANGE_THRESHOLD:
            direction = "surged" if price_change_pct > 0 else "dropped"
            alerts.append({
                "type": "price_movement",
                "severity": "major" if abs(price_change_pct) >= 5 else "moderate",
                "message": f"{name} {direction} {abs(price_change_pct):.1f}%",
            })

        if volume_ratio >= VOLUME_SPIKE_THRESHOLD:
            alerts.append({
                "type": "volume_spike",
                "severity": "moderate",
                "message": f"{name} volume {volume_ratio:.1f}x above average",
            })

        return {
            "ticker": ticker,
            "name": name,
            "current_price": current_price,
            "previous_close": previous_close,
            "price_change": round(price_change, 2),
            "price_change_pct": round(price_change_pct, 2),
            "volume": volume,
            "avg_volume": avg_volume,
            "volume_ratio": round(volume_ratio, 2),
            "alerts": alerts,
            "checked_at": datetime.now().isoformat(),
            "error": None,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "name": ticker,
            "current_price": 0,
            "previous_close": 0,
            "price_change": 0,
            "price_change_pct": 0,
            "volume": 0,
            "avg_volume": 0,
            "volume_ratio": 0,
            "alerts": [],
            "checked_at": datetime.now().isoformat(),
            "error": str(e),
        }


def check_ticker(ticker: str, force: bool = False) -> dict:
    """Check a single ticker for significant movements.

    Returns dict with price data and alerts.
    Uses cache to avoid hammering Yahoo Finance.
    """
    cache = _load_cache()

    cached = cache["tickers"].get(ticker)
    if cached and not force and not _is_stale(cached.get("checked_at")):
        return cached

    result = _fetch_ticker_data(ticker)
    cache["tickers"][ticker] = result
    cache["last_full_scan"] = datetime.now().isoformat()
    _save_cache(cache)

    return result


def scan_watchlist(tickers: list, force: bool = False) -> list:
    """Scan a list of tickers and return results with alerts.

    Loads cache once, checks all tickers, saves once (avoids N+1 I/O).
    Returns list of dicts sorted by alert severity (most urgent first).
    """
    cache = _load_cache()
    results = []
    cache_dirty = False

    for ticker in tickers:
        # Use cached result if fresh
        cached = cache["tickers"].get(ticker)
        if cached and not force and not _is_stale(cached.get("checked_at")):
            results.append(cached)
            continue

        # Fetch fresh data
        result = _fetch_ticker_data(ticker)
        cache["tickers"][ticker] = result
        cache_dirty = True
        results.append(result)

    if cache_dirty:
        cache["last_full_scan"] = datetime.now().isoformat()
        _save_cache(cache)


    # Sort: items with alerts first, then by absolute price change
    results.sort(key=lambda r: (-len(r["alerts"]), -abs(r["price_change_pct"])))
    return results


def get_all_alerts(tickers: list) -> list:
    """Get only the alerts from a watchlist scan (flattened)."""
    results = scan_watchlist(tickers)
    alerts = []
    for r in results:
        for a in r.get("alerts", []):
            alerts.append({**a, "ticker": r["ticker"]})
    return alerts
