"""Portfolio tracker with position management, P&L, and allocation metrics."""

import json
import os
from datetime import datetime
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "watchlist_data")
_PORTFOLIO_FILE = os.path.join(_DATA_DIR, "portfolio.json")


def _load() -> dict:
    """Load portfolio data from disk."""
    if os.path.exists(_PORTFOLIO_FILE):
        with open(_PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"positions": [], "created": datetime.now().isoformat()}


def _save(data: dict):
    """Persist portfolio data."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    data["updated"] = datetime.now().isoformat()
    with open(_PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_portfolio() -> dict:
    """Return the full portfolio dict."""
    return _load()


def get_positions() -> list:
    """Return list of positions."""
    return _load().get("positions", [])


def add_position(
    ticker: str,
    name: str,
    shares: float,
    cost_basis: float,
    date_added: Optional[str] = None,
) -> dict:
    """Add a new position to the portfolio."""
    data = _load()
    position = {
        "id": f"pos_{len(data['positions']) + 1}_{int(datetime.now().timestamp())}",
        "ticker": ticker,
        "name": name,
        "shares": shares,
        "cost_basis": cost_basis,  # per-share cost
        "total_cost": round(shares * cost_basis, 2),
        "date_added": date_added or datetime.now().strftime("%Y-%m-%d"),
    }
    data["positions"].append(position)
    _save(data)
    return position


def remove_position(position_id: str):
    """Remove a position by ID."""
    data = _load()
    data["positions"] = [p for p in data["positions"] if p["id"] != position_id]
    _save(data)


def update_position(position_id: str, shares: float = None, cost_basis: float = None):
    """Update shares or cost basis for an existing position."""
    data = _load()
    for p in data["positions"]:
        if p["id"] == position_id:
            if shares is not None:
                p["shares"] = shares
            if cost_basis is not None:
                p["cost_basis"] = cost_basis
            p["total_cost"] = round(p["shares"] * p["cost_basis"], 2)
            break
    _save(data)


def calculate_portfolio_metrics(positions: list, current_prices: dict) -> dict:
    """Calculate portfolio-level metrics given current prices.

    Args:
        positions: List of position dicts
        current_prices: Dict of {ticker: current_price}

    Returns:
        Dict with total_value, total_cost, total_pnl, total_pnl_pct,
        allocations (list), and per-position metrics.
    """
    if not positions:
        return {
            "total_value": 0, "total_cost": 0, "total_pnl": 0,
            "total_pnl_pct": 0, "positions": [], "allocations": [],
        }

    enriched = []
    total_value = 0
    total_cost = 0

    for pos in positions:
        ticker = pos["ticker"]
        current_price = current_prices.get(ticker, pos["cost_basis"])
        market_value = round(pos["shares"] * current_price, 2)
        pnl = round(market_value - pos["total_cost"], 2)
        pnl_pct = round((pnl / pos["total_cost"]) * 100, 2) if pos["total_cost"] else 0

        enriched.append({
            **pos,
            "current_price": current_price,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })
        total_value += market_value
        total_cost += pos["total_cost"]

    # Calculate allocations
    allocations = []
    for e in enriched:
        weight = round((e["market_value"] / total_value) * 100, 1) if total_value else 0
        e["weight"] = weight
        allocations.append({"name": e["name"], "ticker": e["ticker"], "weight": weight})

    total_pnl = round(total_value - total_cost, 2)
    total_pnl_pct = round((total_pnl / total_cost) * 100, 2) if total_cost else 0

    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "positions": enriched,
        "allocations": allocations,
    }
