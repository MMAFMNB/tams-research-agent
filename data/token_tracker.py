"""
Token Usage Tracking System

Tracks API token consumption per user for billing, analytics, and admin dashboards.
Works with both Supabase (when available) and a local JSON fallback.

Usage:
    from data.token_tracker import (
        track_tokens, get_user_token_usage, get_all_token_usage,
        get_token_summary, get_top_consumers
    )

    # Track tokens after an API call
    track_tokens("user-uuid", model="claude-opus-4", input_tokens=1200, output_tokens=800,
                 action="research", ticker="2222")

    # Query usage
    usage = get_user_token_usage("user-uuid", days=30)
    summary = get_token_summary(days=30)
    top = get_top_consumers(top_n=10, days=30)
"""

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

# Local JSON fallback
TOKEN_LOG_PATH = Path(__file__).parent / "token_usage.json"
_lock = threading.Lock()

# Supabase check
try:
    from data.supabase_client import SUPABASE_AVAILABLE
except ImportError:
    SUPABASE_AVAILABLE = False

# Token cost estimates (per 1M tokens, USD)
MODEL_COSTS = {
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-sonnet-3.5": {"input": 3.0, "output": 15.0},
    "claude-haiku-3.5": {"input": 0.25, "output": 1.25},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "perplexity": {"input": 1.0, "output": 1.0},
}


def _load_log() -> list:
    """Load token usage log from JSON."""
    if TOKEN_LOG_PATH.exists():
        try:
            with open(TOKEN_LOG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_log(log: list):
    """Save token usage log to JSON."""
    TOKEN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with open(TOKEN_LOG_PATH, "w") as f:
            json.dump(log, f, indent=2, default=str)


def track_tokens(
    user_id: str,
    model: str = "claude-opus-4",
    input_tokens: int = 0,
    output_tokens: int = 0,
    action: str = "research",
    ticker: str = "",
    metadata: dict = None,
    agent_name: str = "",
    cached: bool = False,
):
    """
    Record a token usage event.

    Args:
        user_id: The user who triggered the API call
        model: The AI model used
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        action: What the tokens were used for (research, dcf, export, etc.)
        ticker: Stock ticker if applicable
        metadata: Additional metadata
    """
    total_tokens = input_tokens + output_tokens

    # Estimate cost
    costs = MODEL_COSTS.get(model, {"input": 5.0, "output": 15.0})
    estimated_cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000

    entry = {
        "id": f"tok_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id[:8]}",
        "user_id": user_id,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
        "action": action,
        "ticker": ticker,
        "agent_name": agent_name,
        "cached": cached,
        "metadata": metadata or {},
        "timestamp": datetime.now().isoformat(),
    }

    # Try Supabase first
    if SUPABASE_AVAILABLE:
        try:
            from data.supabase_client import get_client
            client = get_client()
            client.table("token_usage").insert(entry).execute()
            return entry
        except Exception as e:
            logger.warning(f"Supabase token tracking failed, using local: {e}")

    # Local fallback
    log = _load_log()
    log.append(entry)

    # Keep last 50000 entries to prevent file bloat
    if len(log) > 50000:
        log = log[-50000:]

    _save_log(log)

    # Also update user's total in users.json
    _update_user_total(user_id, total_tokens)

    return entry


def _update_user_total(user_id: str, tokens: int):
    """Update the cumulative token count on the user record."""
    try:
        users_path = Path(__file__).parent / "users.json"
        if users_path.exists():
            with open(users_path, "r") as f:
                users = json.load(f)
            for u in users:
                if u.get("id") == user_id:
                    u["token_usage"] = u.get("token_usage", 0) + tokens
                    break
            with open(users_path, "w") as f:
                json.dump(users, f, indent=2, default=str)
    except Exception:
        pass


def get_user_token_usage(user_id: str, days: int = 30) -> List[Dict]:
    """Get token usage for a specific user."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    if SUPABASE_AVAILABLE:
        try:
            from data.supabase_client import get_client
            client = get_client()
            result = (client.table("token_usage")
                      .select("*")
                      .eq("user_id", user_id)
                      .gte("timestamp", cutoff)
                      .order("timestamp", desc=True)
                      .execute())
            if result.data:
                return result.data
        except Exception:
            pass

    # Local fallback
    log = _load_log()
    return [e for e in log if e.get("user_id") == user_id and e.get("timestamp", "") >= cutoff]


def get_all_token_usage(days: int = 30) -> List[Dict]:
    """Get all token usage for the time period."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    if SUPABASE_AVAILABLE:
        try:
            from data.supabase_client import get_client
            client = get_client()
            result = (client.table("token_usage")
                      .select("*")
                      .gte("timestamp", cutoff)
                      .order("timestamp", desc=True)
                      .execute())
            if result.data:
                return result.data
        except Exception:
            pass

    log = _load_log()
    return [e for e in log if e.get("timestamp", "") >= cutoff]


def get_token_summary(days: int = 30) -> Dict:
    """
    Get aggregate token usage summary.

    Returns:
        {
            "total_tokens": int,
            "total_input": int,
            "total_output": int,
            "total_cost_usd": float,
            "total_requests": int,
            "by_model": { "model": { tokens, cost, requests } },
            "by_action": { "action": { tokens, cost, requests } },
            "by_user": { "user_id": { tokens, cost, requests } },
            "daily_trend": [{ "date": str, "tokens": int, "cost": float }],
        }
    """
    entries = get_all_token_usage(days)

    summary = {
        "total_tokens": 0,
        "total_input": 0,
        "total_output": 0,
        "total_cost_usd": 0.0,
        "total_requests": len(entries),
        "by_model": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
        "by_action": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
        "by_user": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
        "daily_trend": [],
    }

    daily = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0})

    for e in entries:
        total = e.get("total_tokens", 0)
        cost = e.get("estimated_cost_usd", 0.0)
        model = e.get("model", "unknown")
        action = e.get("action", "unknown")
        user = e.get("user_id", "unknown")
        day = e.get("timestamp", "")[:10]

        summary["total_tokens"] += total
        summary["total_input"] += e.get("input_tokens", 0)
        summary["total_output"] += e.get("output_tokens", 0)
        summary["total_cost_usd"] += cost

        summary["by_model"][model]["tokens"] += total
        summary["by_model"][model]["cost"] += cost
        summary["by_model"][model]["requests"] += 1

        summary["by_action"][action]["tokens"] += total
        summary["by_action"][action]["cost"] += cost
        summary["by_action"][action]["requests"] += 1

        summary["by_user"][user]["tokens"] += total
        summary["by_user"][user]["cost"] += cost
        summary["by_user"][user]["requests"] += 1

        daily[day]["tokens"] += total
        daily[day]["cost"] += cost
        daily[day]["requests"] += 1

    # Convert daily to sorted list
    summary["daily_trend"] = [
        {"date": k, "tokens": v["tokens"], "cost": v["cost"], "requests": v["requests"]}
        for k, v in sorted(daily.items())
    ]

    # Convert defaultdicts to regular dicts
    summary["by_model"] = dict(summary["by_model"])
    summary["by_action"] = dict(summary["by_action"])
    summary["by_user"] = dict(summary["by_user"])

    summary["total_cost_usd"] = round(summary["total_cost_usd"], 4)

    return summary


def get_top_consumers(top_n: int = 10, days: int = 30) -> List[Dict]:
    """
    Get top token-consuming users.

    Returns list of { user_id, tokens, cost, requests, avg_per_request }
    """
    summary = get_token_summary(days)
    by_user = summary.get("by_user", {})

    ranked = []
    for user_id, data in by_user.items():
        avg = data["tokens"] / max(data["requests"], 1)
        ranked.append({
            "user_id": user_id,
            "tokens": data["tokens"],
            "cost": round(data["cost"], 4),
            "requests": data["requests"],
            "avg_per_request": round(avg),
        })

    ranked.sort(key=lambda x: x["tokens"], reverse=True)
    return ranked[:top_n]
