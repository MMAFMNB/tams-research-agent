"""
User Activity Tracking System (Task 24)

Tracks every user action for ML and admin analytics. Works with both Supabase
(when available) and a local JSON fallback.

Usage:
    from data.activity_tracker import (
        track_activity, get_user_activity, get_activity_summary,
        get_ticker_frequency, get_feature_adoption
    )

    # Track an action
    track_activity("user-uuid", "search", ticker="AAPL", metadata={"query": "growth stocks"})

    # Query activity
    recent = get_user_activity("user-uuid", limit=50)
    summary = get_activity_summary(user_id="user-uuid", days=30)
    tickers = get_ticker_frequency("user-uuid", top_n=10)
    adoption = get_feature_adoption(days=30)
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Supabase availability check
from data.supabase_client import SUPABASE_AVAILABLE

if SUPABASE_AVAILABLE:
    from data.supabase_client import ActivityDAO

logger = logging.getLogger(__name__)

# Color constants for HTML output
C_ACCENT = "#1A6DB6"
C_TEXT = "#E6EDF3"
C_MUTED = "#4A5568"

# Local JSON fallback
ACTIVITY_LOG_PATH = Path(__file__).parent / "activity_log.json"

# Valid action types
VALID_ACTIONS = {
    "search",
    "analyze",
    "view_report",
    "export",
    "add_watchlist",
    "view_chart",
    "set_alert",
    "login",
    "page_view",
    "dcf_run",
}


def _load_activity_log() -> List[Dict[str, Any]]:
    """Load activity log from JSON file. Returns empty list if file doesn't exist."""
    try:
        if ACTIVITY_LOG_PATH.exists():
            with open(ACTIVITY_LOG_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading activity log: {e}")
    return []


def _save_activity_log(activities: List[Dict[str, Any]]) -> None:
    """Save activity log to JSON file."""
    try:
        with open(ACTIVITY_LOG_PATH, "w") as f:
            json.dump(activities, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving activity log: {e}")


def track_activity(
    user_id: str,
    action_type: str,
    ticker: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Track a user activity event. Safe to call - never raises exceptions.

    Args:
        user_id: Unique user identifier
        action_type: Type of action (must be in VALID_ACTIONS)
        ticker: Optional stock ticker symbol
        metadata: Optional metadata dict (JSON-serializable)

    Returns:
        None (always succeeds silently)
    """
    try:
        # Validate action type
        if action_type not in VALID_ACTIONS:
            logger.warning(f"Unknown action type: {action_type}. Skipping activity tracking.")
            return

        # Normalize ticker
        if ticker:
            ticker = ticker.upper()

        # Use Supabase if available
        if SUPABASE_AVAILABLE:
            try:
                ActivityDAO.log(user_id, action_type, ticker=ticker, metadata=metadata or {})
                return
            except Exception as e:
                logger.error(f"Error logging activity to Supabase: {e}. Falling back to JSON.")

        # Fallback to JSON
        activities = _load_activity_log()
        activities.append({
            "user_id": user_id,
            "action_type": action_type,
            "ticker": ticker,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        })
        _save_activity_log(activities)

    except Exception as e:
        logger.error(f"Error tracking activity: {e}")
        # Never raise - this is a logging function


def get_user_activity(
    user_id: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get recent activity for a specific user.

    Args:
        user_id: Unique user identifier
        limit: Maximum number of activities to return

    Returns:
        List of activity dicts, newest first
    """
    try:
        if SUPABASE_AVAILABLE:
            try:
                # Query Supabase
                from data.supabase_client import get_client
                client = get_client()
                if client:
                    response = client.table("user_activity").select("*").eq(
                        "user_id", user_id
                    ).order("created_at", desc=True).limit(limit).execute()
                    return response.data if response.data else []
            except Exception as e:
                logger.error(f"Error querying Supabase: {e}. Falling back to JSON.")

        # Fallback to JSON
        activities = _load_activity_log()
        user_activities = [
            a for a in activities if a.get("user_id") == user_id
        ]
        # Sort by timestamp descending (newest first)
        user_activities.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )
        return user_activities[:limit]

    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return []


def get_activity_summary(
    user_id: Optional[str] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Get aggregated activity statistics.

    Args:
        user_id: Optional filter by user (None = all users)
        days: Number of days to include

    Returns:
        Dict with keys:
            - total_events: Total number of events
            - top_actions: List of (action_type, count) tuples
            - top_tickers: List of (ticker, count) tuples
            - daily_counts: Dict of date -> count
            - users_active: Number of unique users (if user_id is None)
    """
    try:
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        if SUPABASE_AVAILABLE:
            try:
                from data.supabase_client import get_client
                client = get_client()
                if client:
                    query = client.table("user_activity").select("*").gte(
                        "created_at", cutoff_date
                    )
                    if user_id:
                        query = query.eq("user_id", user_id)
                    response = query.execute()
                    activities = response.data if response.data else []
                    return _compute_summary(activities)
            except Exception as e:
                logger.error(f"Error querying Supabase: {e}. Falling back to JSON.")

        # Fallback to JSON
        activities = _load_activity_log()
        activities = [
            a for a in activities
            if a.get("timestamp", "") >= cutoff_date
        ]
        if user_id:
            activities = [a for a in activities if a.get("user_id") == user_id]

        return _compute_summary(activities)

    except Exception as e:
        logger.error(f"Error computing activity summary: {e}")
        return {
            "total_events": 0,
            "top_actions": [],
            "top_tickers": [],
            "daily_counts": {},
            "users_active": 0,
        }


def _compute_summary(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to compute summary from activity list."""
    action_counts = defaultdict(int)
    ticker_counts = defaultdict(int)
    daily_counts = defaultdict(int)
    users_seen = set()

    for activity in activities:
        action = activity.get("action_type")
        ticker = activity.get("ticker")
        timestamp = activity.get("timestamp", "")
        user_id = activity.get("user_id")

        if action:
            action_counts[action] += 1
        if ticker:
            ticker_counts[ticker] += 1
        if user_id:
            users_seen.add(user_id)

        # Daily count
        if timestamp:
            date_key = timestamp[:10]  # YYYY-MM-DD
            daily_counts[date_key] += 1

    return {
        "total_events": len(activities),
        "top_actions": sorted(
            action_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10],
        "top_tickers": sorted(
            ticker_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10],
        "daily_counts": dict(sorted(daily_counts.items(), reverse=True)),
        "users_active": len(users_seen),
    }


def get_ticker_frequency(
    user_id: str,
    top_n: int = 10,
) -> List[tuple]:
    """
    Get the most researched tickers for a user.

    Args:
        user_id: Unique user identifier
        top_n: Number of top tickers to return

    Returns:
        List of (ticker, count) tuples, sorted by frequency
    """
    try:
        user_activities = get_user_activity(user_id, limit=10000)
        ticker_counts = defaultdict(int)

        for activity in user_activities:
            ticker = activity.get("ticker")
            if ticker:
                ticker_counts[ticker] += 1

        return sorted(
            ticker_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]

    except Exception as e:
        logger.error(f"Error getting ticker frequency: {e}")
        return []


def get_feature_adoption(days: int = 30) -> Dict[str, Any]:
    """
    Get feature adoption metrics across all users for admin dashboard.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with keys:
            - search: count
            - analyze: count
            - view_report: count
            - export: count
            - add_watchlist: count
            - view_chart: count
            - set_alert: count
            - login: count
            - page_view: count
            - dcf_run: count
            - total_users: count of unique users
            - total_events: count
    """
    try:
        summary = get_activity_summary(user_id=None, days=days)

        adoption = {
            "total_users": summary.get("users_active", 0),
            "total_events": summary.get("total_events", 0),
        }

        # Add counts for each action type
        for action, count in summary.get("top_actions", []):
            adoption[action] = count

        # Ensure all action types are present
        for action in VALID_ACTIONS:
            if action not in adoption:
                adoption[action] = 0

        return adoption

    except Exception as e:
        logger.error(f"Error computing feature adoption: {e}")
        return {
            "total_users": 0,
            "total_events": 0,
        }
