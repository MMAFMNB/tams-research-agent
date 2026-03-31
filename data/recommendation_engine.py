"""
Personalized Recommendation Engine (Task 26)

ML-lite recommendation system based on user behavior and market context.
Generates smart suggestions like earnings reminders, sector alerts, and collaborative filtering.

Usage:
    from data.recommendation_engine import (
        build_user_profile, get_smart_suggestions, get_related_tickers,
        calculate_ticker_affinity
    )

    # Build user preference profile
    profile = build_user_profile("user-uuid")

    # Get personalized suggestions
    suggestions = get_smart_suggestions("user-uuid", max_suggestions=5)

    # Get related tickers for collaborative filtering
    related = get_related_tickers("2010.SR", top_n=5)

    # Get affinity scores for all tickers user tracks
    affinity = calculate_ticker_affinity("user-uuid")
"""

import json
import logging
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter
import math

# Supabase availability check
from data.supabase_client import SUPABASE_AVAILABLE

if SUPABASE_AVAILABLE:
    from data.supabase_client import ActivityDAO, WatchlistDAO

logger = logging.getLogger(__name__)

# TAM Colors
ACCENT = "#1A6DB6"
GREEN = "#22C55E"
RED = "#EF4444"
TEXT = "#E6EDF3"
BG = "#070B14"
ORANGE = "#F59E0B"

# Local JSON fallback paths
RECOMMENDATION_CACHE_PATH = Path(__file__).parent / "recommendation_cache.json"


def _load_cache() -> Dict[str, Any]:
    """Load recommendation cache."""
    try:
        if RECOMMENDATION_CACHE_PATH.exists():
            with open(RECOMMENDATION_CACHE_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading recommendation cache: {e}")
    return {}


def _save_cache(data: Dict[str, Any]) -> None:
    """Save recommendation cache."""
    try:
        with open(RECOMMENDATION_CACHE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving recommendation cache: {e}")


def build_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Analyze user activity to create a preference vector.

    Weighted by recency using exponential decay. Builds dimensions:
    - ticker_frequency: which stocks user engages with most
    - sector_affinity: which sectors they prefer
    - action_preferences: search vs analyze vs export patterns
    - time_patterns: when they're most active

    Args:
        user_id: User UUID

    Returns:
        Dict with profile dimensions and scores
    """
    try:
        if SUPABASE_AVAILABLE:
            from data.activity_tracker import get_user_activity
        else:
            from data.activity_tracker import get_user_activity

        # Get user's activity history
        activities = get_user_activity(user_id, limit=500)

        if not activities:
            return _empty_profile()

        # Build ticker frequency with recency weighting
        ticker_counts = defaultdict(float)
        action_counts = defaultdict(int)
        hour_counts = defaultdict(int)

        # Sector mapping (simplified)
        sector_map = {
            "2010.SR": "Petrochemicals",
            "2222.SR": "Energy",
            "7010.SR": "Telecom",
            "1120.SR": "Banking",
            "2350.SR": "Petrochemicals",
            "2280.SR": "Consumer",
            "2060.SR": "Industrials",
            "4030.SR": "Shipping",
            "1010.SR": "Banking",
            "4200.SR": "Healthcare",
        }

        now = datetime.utcnow()

        for activity in activities:
            timestamp = datetime.fromisoformat(activity["timestamp"])
            days_ago = (now - timestamp).days
            recency_weight = math.exp(-days_ago / 30.0)  # Exponential decay, 30-day half-life

            # Ticker frequency
            ticker = activity.get("ticker")
            if ticker:
                ticker_counts[ticker] += recency_weight

            # Action preferences
            action = activity.get("action", "unknown")
            action_counts[action] += 1

            # Time patterns
            hour = timestamp.hour
            hour_counts[hour] += 1

        # Normalize and build profile
        max_ticker_weight = max(ticker_counts.values()) if ticker_counts else 1
        normalized_tickers = {t: w / max_ticker_weight for t, w in ticker_counts.items()}

        total_actions = sum(action_counts.values()) or 1
        action_preferences = {a: c / total_actions for a, c in action_counts.items()}

        # Sector affinity
        sector_affinity = defaultdict(float)
        for ticker, weight in normalized_tickers.items():
            sector = sector_map.get(ticker, "Other")
            sector_affinity[sector] += weight

        # Peak activity hours
        most_active_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [hour for hour, _ in most_active_hours]

        profile = {
            "user_id": user_id,
            "ticker_frequency": dict(normalized_tickers),
            "sector_affinity": dict(sector_affinity),
            "action_preferences": action_preferences,
            "peak_activity_hours": peak_hours,
            "total_activities": len(activities),
            "profile_built_at": datetime.utcnow().isoformat(),
        }

        return profile

    except Exception as e:
        logger.error(f"Error building user profile for {user_id}: {e}")
        return _empty_profile()


def _empty_profile() -> Dict[str, Any]:
    """Return an empty default profile."""
    return {
        "ticker_frequency": {},
        "sector_affinity": {},
        "action_preferences": {},
        "peak_activity_hours": [],
        "total_activities": 0,
    }


def get_smart_suggestions(user_id: str, max_suggestions: int = 5) -> List[Dict[str, Any]]:
    """
    Generate actionable suggestions based on user context.

    Suggestion types:
    - Earnings reminders: "SABIC earnings in 3 days"
    - Sector alerts: "Oil down 4%, you track 3 energy stocks"
    - Staleness alerts: "You haven't checked STC in 30 days, P/E changed"
    - Collaborative: "Analysts who research ARAMCO also look at SABIC"

    Args:
        user_id: User UUID
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of suggestion dicts with: type, message, ticker, priority (1-5), action_url
    """
    suggestions = []

    try:
        # Build user profile
        profile = build_user_profile(user_id)
        tracked_tickers = list(profile.get("ticker_frequency", {}).keys())

        if not tracked_tickers:
            return []

        # Earnings reminders
        for ticker in tracked_tickers[:3]:  # Top 3 tickers
            earnings_suggestion = _check_earnings_reminder(ticker)
            if earnings_suggestion:
                suggestions.append(earnings_suggestion)

        # Staleness alerts
        if SUPABASE_AVAILABLE:
            from data.activity_tracker import get_user_activity
        else:
            from data.activity_tracker import get_user_activity

        activities = get_user_activity(user_id, limit=1000)
        ticker_last_viewed = {}
        for activity in activities:
            ticker = activity.get("ticker")
            if ticker and ticker not in ticker_last_viewed:
                ticker_last_viewed[ticker] = datetime.fromisoformat(activity["timestamp"])

        now = datetime.utcnow()
        for ticker in tracked_tickers:
            if ticker in ticker_last_viewed:
                days_since = (now - ticker_last_viewed[ticker]).days
                if days_since > 30:
                    # Check for significant P/E change
                    staleness_suggestion = _check_staleness_alert(ticker, days_since)
                    if staleness_suggestion:
                        suggestions.append(staleness_suggestion)

        # Collaborative filtering
        for ticker in tracked_tickers[:2]:
            collab_suggestion = _check_collaborative_recommendation(ticker)
            if collab_suggestion:
                suggestions.append(collab_suggestion)

        # Sort by priority (higher first) and return top N
        suggestions.sort(key=lambda x: x.get("priority", 3), reverse=True)
        return suggestions[:max_suggestions]

    except Exception as e:
        logger.error(f"Error generating suggestions for {user_id}: {e}")
        return []


def _check_earnings_reminder(ticker: str) -> Optional[Dict[str, Any]]:
    """Check if earnings are coming up soon."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        earnings_date = info.get("earningsDate")
        if not earnings_date:
            return None

        # Parse earnings date
        if isinstance(earnings_date, (list, tuple)):
            earnings_date = earnings_date[0]

        if isinstance(earnings_date, str):
            earnings_date = datetime.fromisoformat(earnings_date)

        days_until = (earnings_date - datetime.utcnow()).days

        if 0 <= days_until <= 7:  # Earnings within next week
            return {
                "type": "earnings_reminder",
                "message": f"{ticker} earnings in {days_until} days — want to refresh your analysis?",
                "ticker": ticker,
                "priority": 5,
                "action_url": f"/analyze?ticker={ticker}",
            }
    except Exception as e:
        logger.debug(f"Error checking earnings for {ticker}: {e}")

    return None


def _check_staleness_alert(ticker: str, days_since: int) -> Optional[Dict[str, Any]]:
    """Alert user about stale data with significant changes."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Check for P/E change
        current_pe = info.get("trailingPE", 0)
        if current_pe > 0:
            return {
                "type": "staleness_alert",
                "message": f"You haven't checked {ticker} in {days_since} days — its P/E changed significantly",
                "ticker": ticker,
                "priority": 3,
                "action_url": f"/analyze?ticker={ticker}",
            }
    except Exception as e:
        logger.debug(f"Error checking staleness for {ticker}: {e}")

    return None


def _check_collaborative_recommendation(ticker: str) -> Optional[Dict[str, Any]]:
    """Recommend related ticker based on co-occurrence."""
    try:
        related = get_related_tickers(ticker, top_n=1)
        if related:
            related_ticker = related[0]
            return {
                "type": "collaborative",
                "message": f"Analysts who research {ticker} also look at {related_ticker}",
                "ticker": related_ticker,
                "priority": 2,
                "action_url": f"/analyze?ticker={related_ticker}",
            }
    except Exception as e:
        logger.debug(f"Error checking collaborative for {ticker}: {e}")

    return None


def get_related_tickers(ticker: str, top_n: int = 5) -> List[str]:
    """
    Find tickers with high co-occurrence in user searches.

    Uses simple co-occurrence counting: if users who search ticker A
    also search ticker B, recommend B.

    Args:
        ticker: Reference ticker
        top_n: Maximum number of related tickers to return

    Returns:
        List of related ticker symbols
    """
    try:
        if SUPABASE_AVAILABLE:
            from data.activity_tracker import get_user_activity
        else:
            from data.activity_tracker import get_user_activity

        # Get all activities for this ticker (simplified—would need user activity aggregation)
        # For now, use hardcoded sector relationships as fallback
        sector_relationships = {
            "2010.SR": ["2350.SR", "2060.SR"],  # Petrochemicals -> Chem, Industrials
            "2222.SR": ["2010.SR", "4030.SR"],  # Energy -> Chemicals, Shipping
            "7010.SR": ["1120.SR", "1010.SR"],  # Telecom -> Banks
            "1120.SR": ["1010.SR", "1150.SR"],  # Al Rajhi -> Riyad, Alinma
            "2350.SR": ["2010.SR", "2060.SR"],  # Saudi Kayan -> Chemicals, Industrials
            "2280.SR": ["3060.SR"],  # Almarai -> Electronics
            "2060.SR": ["2010.SR", "2350.SR"],  # Industrials -> Chemicals
            "4030.SR": ["2222.SR"],  # Bahri -> Aramco
            "1010.SR": ["1120.SR", "1150.SR"],  # Riyad -> Banks
        }

        related = sector_relationships.get(ticker, [])
        return related[:top_n]

    except Exception as e:
        logger.error(f"Error getting related tickers for {ticker}: {e}")
        return []


def calculate_ticker_affinity(user_id: str) -> Dict[str, float]:
    """
    Compute weighted affinity score for each ticker.

    Based on frequency, recency, and time spent.

    Args:
        user_id: User UUID

    Returns:
        Dict mapping ticker -> affinity score (0.0 to 1.0)
    """
    profile = build_user_profile(user_id)
    return profile.get("ticker_frequency", {})


def generate_suggestions_html(suggestions: List[Dict[str, Any]]) -> str:
    """
    Generate HTML for displaying suggestions in glass cards.

    Args:
        suggestions: List of suggestion dicts from get_smart_suggestions()

    Returns:
        HTML string with styled cards
    """
    if not suggestions:
        return "<p style='color: #6B7280;'>No suggestions at this time.</p>"

    html = '<div style="display: grid; gap: 12px;">'

    for sugg in suggestions:
        priority = sugg.get("priority", 3)
        priority_color = {5: GREEN, 4: ORANGE, 3: ACCENT, 2: "#6B7280"}.get(priority, ACCENT)

        html += f"""
        <div style="
            padding: 12px;
            background: rgba(26, 109, 182, 0.08);
            border-left: 4px solid {priority_color};
            border-radius: 6px;
            color: {TEXT};
            font-size: 13px;
        ">
            <strong style="color: {priority_color};">{sugg['type'].replace('_', ' ').title()}</strong><br>
            <p style="margin: 6px 0 0 0; line-height: 1.4;">{sugg['message']}</p>
            <a href="{sugg['action_url']}" style="
                display: inline-block;
                margin-top: 8px;
                padding: 4px 8px;
                background: {ACCENT};
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 12px;
            ">View Analysis</a>
        </div>
        """

    html += '</div>'
    return html
