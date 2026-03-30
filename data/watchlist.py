"""JSON-based analyst watchlist for tracking tickers."""

import json
import os
from datetime import datetime
from typing import Optional

WATCHLIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "watchlist_data")
WATCHLIST_FILE = os.path.join(WATCHLIST_DIR, "watchlist.json")
MAX_WATCHLISTS = 10
MAX_ITEMS_PER_WATCHLIST = 50


def _ensure_dir():
    os.makedirs(WATCHLIST_DIR, exist_ok=True)


def _load_data() -> dict:
    """Load watchlist data from disk."""
    _ensure_dir()
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"watchlists": [], "next_id": 1}


def _save_data(data: dict):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_watchlist(name: str, description: str = "") -> dict:
    """Create a new watchlist. Returns the created watchlist dict."""
    data = _load_data()

    if len(data["watchlists"]) >= MAX_WATCHLISTS:
        raise ValueError(f"Watchlist limit reached ({MAX_WATCHLISTS})")

    if any(w["name"].lower() == name.lower() for w in data["watchlists"]):
        raise ValueError(f"Watchlist '{name}' already exists")

    wl = {
        "id": data["next_id"],
        "name": name,
        "description": description,
        "is_default": len(data["watchlists"]) == 0,
        "created_at": datetime.now().isoformat(),
        "items": [],
    }
    data["watchlists"].append(wl)
    data["next_id"] += 1
    _save_data(data)
    return wl


def get_watchlists() -> list:
    """Get all watchlists (without full item details)."""
    data = _load_data()
    result = []
    for wl in data["watchlists"]:
        result.append({
            "id": wl["id"],
            "name": wl["name"],
            "description": wl.get("description", ""),
            "is_default": wl.get("is_default", False),
            "item_count": len(wl.get("items", [])),
        })
    return result


def get_watchlist(watchlist_id: int) -> Optional[dict]:
    """Get a watchlist by ID, including all items."""
    data = _load_data()
    for wl in data["watchlists"]:
        if wl["id"] == watchlist_id:
            return wl
    return None


def get_default_watchlist() -> Optional[dict]:
    """Get the default watchlist, or the first one if none is default."""
    data = _load_data()
    for wl in data["watchlists"]:
        if wl.get("is_default"):
            return wl
    if data["watchlists"]:
        return data["watchlists"][0]
    return None


def delete_watchlist(watchlist_id: int) -> bool:
    """Delete a watchlist by ID."""
    data = _load_data()
    original_len = len(data["watchlists"])
    data["watchlists"] = [w for w in data["watchlists"] if w["id"] != watchlist_id]
    if len(data["watchlists"]) < original_len:
        _save_data(data)
        return True
    return False


def add_ticker(watchlist_id: int, ticker: str, name: str = "",
               notes: str = "") -> dict:
    """Add a ticker to a watchlist. Returns the created item."""
    data = _load_data()

    wl = None
    for w in data["watchlists"]:
        if w["id"] == watchlist_id:
            wl = w
            break
    if wl is None:
        raise ValueError(f"Watchlist {watchlist_id} not found")

    ticker = ticker.upper().strip()
    if any(item["ticker"] == ticker for item in wl["items"]):
        raise ValueError(f"{ticker} already in watchlist")

    if len(wl["items"]) >= MAX_ITEMS_PER_WATCHLIST:
        raise ValueError(f"Watchlist item limit reached ({MAX_ITEMS_PER_WATCHLIST})")

    item = {
        "ticker": ticker,
        "name": name or ticker,
        "notes": notes,
        "added_at": datetime.now().isoformat(),
    }
    wl["items"].append(item)
    _save_data(data)
    return item


def remove_ticker(watchlist_id: int, ticker: str) -> bool:
    """Remove a ticker from a watchlist."""
    data = _load_data()
    ticker = ticker.upper().strip()

    for wl in data["watchlists"]:
        if wl["id"] == watchlist_id:
            original_len = len(wl["items"])
            wl["items"] = [i for i in wl["items"] if i["ticker"] != ticker]
            if len(wl["items"]) < original_len:
                _save_data(data)
                return True
            return False
    return False


def get_all_watched_tickers() -> list:
    """Get a flat list of all unique tickers across all watchlists."""
    data = _load_data()
    tickers = set()
    for wl in data["watchlists"]:
        for item in wl.get("items", []):
            tickers.add(item["ticker"])
    return sorted(tickers)
