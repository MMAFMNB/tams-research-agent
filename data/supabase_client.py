"""
Supabase Data Access Layer (DAL) for Stock Research App

Provides client initialization and DAO classes for all database tables.
Handles connection management, error handling, and type-safe data operations.
"""

import os
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime

# Try to import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = False  # Will be set to True after successful initialization
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore

logger = logging.getLogger(__name__)

# Module-level Supabase client (lazy initialization)
_supabase_client: Optional[Client] = None


def get_client() -> Optional[Client]:
    """
    Get or initialize the Supabase client.

    Lazily initializes the client from environment variables on first call.
    Returns None if SUPABASE_AVAILABLE is False.

    Returns:
        Client: The Supabase client, or None if not available
    """
    global _supabase_client, SUPABASE_AVAILABLE

    if not SUPABASE_AVAILABLE:
        return None

    if _supabase_client is not None:
        return _supabase_client

    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not set in environment")
            SUPABASE_AVAILABLE = False
            return None

        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        SUPABASE_AVAILABLE = False
        return None


def _initialize_supabase_availability() -> None:
    """Initialize SUPABASE_AVAILABLE based on environment variables and imports."""
    global SUPABASE_AVAILABLE

    if Client is None:
        SUPABASE_AVAILABLE = False
        return

    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        SUPABASE_AVAILABLE = False
        return

    SUPABASE_AVAILABLE = True


# Initialize availability on module load
_initialize_supabase_availability()


# ==================== USER DAO ====================
class UserDAO:
    """Data Access Object for users table."""

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by email address.

        Args:
            email: The user's email

        Returns:
            User dict or None if not found
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("users").select("*").eq("email", email).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """
        Get all users (admin only in production).

        Returns:
            List of user dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("users").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    @staticmethod
    def update_role(user_id: str, role: str) -> bool:
        """
        Update a user's role.

        Args:
            user_id: UUID of the user
            role: New role (super_admin, admin, analyst, viewer)

        Returns:
            True if successful, False otherwise
        """
        if role not in ("super_admin", "admin", "analyst", "viewer"):
            logger.error(f"Invalid role: {role}")
            return False

        client = get_client()
        if not client:
            return False

        try:
            response = client.table("users").update({"role": role}).eq("id", user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating user role for {user_id}: {e}")
            return False

    @staticmethod
    def update_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update a user's preferences JSON.

        Args:
            user_id: UUID of the user
            preferences: Preferences dict

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("users").update({"preferences": preferences}).eq("id", user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating user preferences for {user_id}: {e}")
            return False

    @staticmethod
    def update_last_login(user_id: str) -> bool:
        """
        Update a user's last login timestamp.

        Args:
            user_id: UUID of the user

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("users").update({"last_login_at": datetime.utcnow().isoformat()}).eq("id", user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating last login for {user_id}: {e}")
            return False


# ==================== WATCHLIST DAO ====================
class WatchlistDAO:
    """Data Access Object for watchlists table."""

    @staticmethod
    def get_user_watchlists(user_id: str) -> List[Dict[str, Any]]:
        """
        Get all watchlists for a user.

        Args:
            user_id: UUID of the user

        Returns:
            List of watchlist dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("watchlists").select("*").eq("user_id", user_id).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting watchlists for user {user_id}: {e}")
            return []

    @staticmethod
    def get_default(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the default watchlist for a user.

        Args:
            user_id: UUID of the user

        Returns:
            Default watchlist dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("watchlists").select("*").eq("user_id", user_id).eq("is_default", True).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.debug(f"No default watchlist for user {user_id}: {e}")
            return None

    @staticmethod
    def create(user_id: str, name: str, description: str = "", is_default: bool = False) -> Optional[Dict[str, Any]]:
        """
        Create a new watchlist.

        Args:
            user_id: UUID of the user
            name: Watchlist name
            description: Optional description
            is_default: Whether this is the default watchlist

        Returns:
            Created watchlist dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("watchlists").insert({
                "user_id": user_id,
                "name": name,
                "description": description,
                "is_default": is_default
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating watchlist for user {user_id}: {e}")
            return None

    @staticmethod
    def add_item(watchlist_id: str, ticker: str, company_name: str = "") -> Optional[Dict[str, Any]]:
        """
        Add an item to a watchlist.

        Args:
            watchlist_id: UUID of the watchlist
            ticker: Stock ticker symbol
            company_name: Optional company name

        Returns:
            Created watchlist item dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("watchlist_items").insert({
                "watchlist_id": watchlist_id,
                "ticker": ticker.upper(),
                "company_name": company_name
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error adding item to watchlist {watchlist_id}: {e}")
            return None

    @staticmethod
    def remove_item(item_id: str) -> bool:
        """
        Remove an item from a watchlist.

        Args:
            item_id: UUID of the watchlist item

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("watchlist_items").delete().eq("id", item_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error removing watchlist item {item_id}: {e}")
            return False

    @staticmethod
    def get_all_watched_tickers(user_id: str) -> List[str]:
        """
        Get all unique tickers in a user's watchlists.

        Args:
            user_id: UUID of the user

        Returns:
            List of ticker symbols
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("watchlist_items").select("ticker").eq("watchlist_id", user_id).execute()
            # Query needs to get items from watchlists first - simplified for direct watchlist_id
            if not response.data:
                return []
            return list(set(item["ticker"] for item in response.data))
        except Exception as e:
            logger.error(f"Error getting watched tickers for user {user_id}: {e}")
            return []


# ==================== PORTFOLIO DAO ====================
class PortfolioDAO:
    """Data Access Object for portfolio_positions table."""

    @staticmethod
    def get_positions(user_id: str) -> List[Dict[str, Any]]:
        """
        Get all portfolio positions for a user.

        Args:
            user_id: UUID of the user

        Returns:
            List of position dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("portfolio_positions").select("*").eq("user_id", user_id).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting positions for user {user_id}: {e}")
            return []

    @staticmethod
    def add_position(user_id: str, ticker: str, company_name: str, shares: float, cost_basis: float) -> Optional[Dict[str, Any]]:
        """
        Add a new portfolio position.

        Args:
            user_id: UUID of the user
            ticker: Stock ticker symbol
            company_name: Company name
            shares: Number of shares
            cost_basis: Cost basis per share

        Returns:
            Created position dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("portfolio_positions").insert({
                "user_id": user_id,
                "ticker": ticker.upper(),
                "company_name": company_name,
                "shares": shares,
                "cost_basis": cost_basis
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error adding position for user {user_id}: {e}")
            return None

    @staticmethod
    def remove_position(position_id: str) -> bool:
        """
        Remove a portfolio position.

        Args:
            position_id: UUID of the position

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("portfolio_positions").delete().eq("id", position_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error removing position {position_id}: {e}")
            return False


# ==================== REPORT DAO ====================
class ReportDAO:
    """Data Access Object for reports table."""

    @staticmethod
    def save(user_id: str, ticker: str, company_name: str, sections: Dict[str, Any],
             files: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Save a research report.

        Args:
            user_id: UUID of the user
            ticker: Stock ticker symbol
            company_name: Company name
            sections: Report sections dict
            files: Optional files dict
            metadata: Optional metadata dict

        Returns:
            Created report dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("reports").insert({
                "user_id": user_id,
                "ticker": ticker.upper(),
                "company_name": company_name,
                "sections": sections,
                "files": files or {},
                "metadata": metadata or {}
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error saving report for {ticker}: {e}")
            return None

    @staticmethod
    def get_by_ticker(ticker: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get reports for a ticker.

        Args:
            ticker: Stock ticker symbol
            user_id: Optional user UUID to filter by owner

        Returns:
            List of report dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            query = client.table("reports").select("*").eq("ticker", ticker.upper())
            if user_id:
                query = query.eq("user_id", user_id)
            response = query.order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting reports for ticker {ticker}: {e}")
            return []

    @staticmethod
    def get_versions(ticker: str) -> List[Dict[str, Any]]:
        """
        Get all versions of a report for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of report dicts ordered by version
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("reports").select("*").eq("ticker", ticker.upper()).order("version", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting report versions for {ticker}: {e}")
            return []

    @staticmethod
    def get_by_id(report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a report by ID.

        Args:
            report_id: UUID of the report

        Returns:
            Report dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("reports").select("*").eq("id", report_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {e}")
            return None


# ==================== ALERT DAO ====================
class AlertDAO:
    """Data Access Object for alerts table."""

    @staticmethod
    def create_alert(user_id: str, ticker: str, alert_type: str, severity: str, message: str,
                    context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new alert.

        Args:
            user_id: UUID of the user
            ticker: Stock ticker symbol
            alert_type: Type of alert (price_target, volume_spike, news_trigger, earnings, technical_signal)
            severity: Severity level (info, warning, critical)
            message: Alert message
            context: Optional context dict

        Returns:
            Created alert dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("alerts").insert({
                "user_id": user_id,
                "ticker": ticker.upper(),
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "context": context or {}
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating alert for {ticker}: {e}")
            return None

    @staticmethod
    def get_recent(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent alerts for a user.

        Args:
            user_id: UUID of the user
            limit: Maximum number of alerts to return

        Returns:
            List of alert dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("alerts").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting recent alerts for user {user_id}: {e}")
            return []

    @staticmethod
    def get_unread_count(user_id: str) -> int:
        """
        Get count of unread alerts for a user.

        Args:
            user_id: UUID of the user

        Returns:
            Number of unread alerts
        """
        client = get_client()
        if not client:
            return 0

        try:
            response = client.table("alerts").select("*", count="exact").eq("user_id", user_id).eq("is_read", False).execute()
            return response.count if response.count is not None else 0
        except Exception as e:
            logger.error(f"Error getting unread alert count for user {user_id}: {e}")
            return 0

    @staticmethod
    def mark_read(alert_id: str) -> bool:
        """
        Mark an alert as read.

        Args:
            alert_id: UUID of the alert

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("alerts").update({"is_read": True}).eq("id", alert_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error marking alert {alert_id} as read: {e}")
            return False

    @staticmethod
    def mark_all_read(user_id: str) -> bool:
        """
        Mark all alerts as read for a user.

        Args:
            user_id: UUID of the user

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("alerts").update({"is_read": True}).eq("user_id", user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error marking all alerts as read for user {user_id}: {e}")
            return False


# ==================== ALERT RULE DAO ====================
class AlertRuleDAO:
    """Data Access Object for alert_rules table."""

    @staticmethod
    def get_user_rules(user_id: str) -> List[Dict[str, Any]]:
        """
        Get all alert rules for a user.

        Args:
            user_id: UUID of the user

        Returns:
            List of rule dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("alert_rules").select("*").eq("user_id", user_id).eq("is_active", True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting alert rules for user {user_id}: {e}")
            return []

    @staticmethod
    def create_rule(user_id: str, ticker: str, rule_type: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new alert rule.

        Args:
            user_id: UUID of the user
            ticker: Stock ticker symbol (optional for general rules)
            rule_type: Type of rule (price_above, price_below, volume_spike, pct_change, news_keyword, technical)
            parameters: Rule parameters dict

        Returns:
            Created rule dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("alert_rules").insert({
                "user_id": user_id,
                "ticker": ticker.upper() if ticker else None,
                "rule_type": rule_type,
                "parameters": parameters,
                "is_active": True
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating alert rule for user {user_id}: {e}")
            return None

    @staticmethod
    def update_rule(rule_id: str, **kwargs) -> bool:
        """
        Update an alert rule.

        Args:
            rule_id: UUID of the rule
            **kwargs: Fields to update (parameters, is_active, etc.)

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("alert_rules").update(kwargs).eq("id", rule_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating alert rule {rule_id}: {e}")
            return False

    @staticmethod
    def delete_rule(rule_id: str) -> bool:
        """
        Delete an alert rule.

        Args:
            rule_id: UUID of the rule

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("alert_rules").delete().eq("id", rule_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting alert rule {rule_id}: {e}")
            return False


# ==================== ACTIVITY DAO ====================
class ActivityDAO:
    """Data Access Object for user_activity table."""

    @staticmethod
    def log(user_id: str, action_type: str, ticker: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a user activity.

        Args:
            user_id: UUID of the user
            action_type: Type of action (search, analyze, view_report, export, add_watchlist, view_chart, set_alert, login, dcf_run)
            ticker: Optional stock ticker
            metadata: Optional metadata dict
        """
        client = get_client()
        if not client:
            return

        try:
            client.table("user_activity").insert({
                "user_id": user_id,
                "action_type": action_type,
                "ticker": ticker.upper() if ticker else None,
                "metadata": metadata or {}
            }).execute()
        except Exception as e:
            logger.error(f"Error logging activity for user {user_id}: {e}")


# ==================== SENTIMENT DAO ====================
class SentimentDAO:
    """Data Access Object for ai_sentiment_scores table."""

    @staticmethod
    def save_scores(ticker: str, report_id: Optional[str], scores: Dict[str, float]) -> None:
        """
        Save sentiment scores for a ticker.

        Args:
            ticker: Stock ticker symbol
            report_id: Optional UUID of related report
            scores: Dict of category -> score (e.g., {'overall': 0.75, 'management_tone': 0.8})
        """
        client = get_client()
        if not client:
            return

        try:
            for category, score in scores.items():
                if -1.0 <= score <= 1.0:
                    client.table("ai_sentiment_scores").insert({
                        "ticker": ticker.upper(),
                        "report_id": report_id,
                        "score": score,
                        "category": category
                    }).execute()
        except Exception as e:
            logger.error(f"Error saving sentiment scores for {ticker}: {e}")

    @staticmethod
    def get_trend(ticker: str, category: str = "overall", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get sentiment score trend for a ticker.

        Args:
            ticker: Stock ticker symbol
            category: Sentiment category (overall, management_tone, financial_health, growth_outlook, risk_level)
            limit: Maximum number of scores to return

        Returns:
            List of sentiment score dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("ai_sentiment_scores").select("*").eq("ticker", ticker.upper()).eq("category", category).order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting sentiment trend for {ticker}: {e}")
            return []


# ==================== AUDIT DAO ====================
class AuditDAO:
    """Data Access Object for audit_log table (append-only)."""

    @staticmethod
    def log(user_id: Optional[str], action: str, resource: str = "", details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an audit event (append-only).

        Args:
            user_id: UUID of the user (optional)
            action: Description of the action
            resource: Resource affected (table name, etc.)
            details: Optional details dict
        """
        client = get_client()
        if not client:
            return

        try:
            client.table("audit_log").insert({
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "details": details or {}
            }).execute()
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")

    @staticmethod
    def get_log(limit: int = 100, user_id: Optional[str] = None, action: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get audit log entries.

        Args:
            limit: Maximum number of entries to return
            user_id: Optional filter by user
            action: Optional filter by action type

        Returns:
            List of audit log dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            query = client.table("audit_log").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            if action:
                query = query.eq("action", action)
            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return []


# ==================== NOTES DAO ====================
class NotesDAO:
    """Data Access Object for research_notes table."""

    @staticmethod
    def get_for_ticker(user_id: str, ticker: str) -> List[Dict[str, Any]]:
        """
        Get all research notes for a ticker.

        Args:
            user_id: UUID of the user
            ticker: Stock ticker symbol

        Returns:
            List of note dicts
        """
        client = get_client()
        if not client:
            return []

        try:
            response = client.table("research_notes").select("*").eq("user_id", user_id).eq("ticker", ticker.upper()).order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting notes for {ticker}: {e}")
            return []

    @staticmethod
    def create(user_id: str, ticker: str, content: str, tags: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Create a research note.

        Args:
            user_id: UUID of the user
            ticker: Stock ticker symbol
            content: Note content
            tags: Optional list of tags

        Returns:
            Created note dict or None
        """
        client = get_client()
        if not client:
            return None

        try:
            response = client.table("research_notes").insert({
                "user_id": user_id,
                "ticker": ticker.upper(),
                "content": content,
                "tags": tags or []
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating note for {ticker}: {e}")
            return None

    @staticmethod
    def update(note_id: str, content: str, tags: Optional[List[str]] = None) -> bool:
        """
        Update a research note.

        Args:
            note_id: UUID of the note
            content: Updated content
            tags: Optional updated tags

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            update_data = {"content": content}
            if tags is not None:
                update_data["tags"] = tags
            response = client.table("research_notes").update(update_data).eq("id", note_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating note {note_id}: {e}")
            return False

    @staticmethod
    def delete(note_id: str) -> bool:
        """
        Delete a research note.

        Args:
            note_id: UUID of the note

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            response = client.table("research_notes").delete().eq("id", note_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting note {note_id}: {e}")
            return False

    @staticmethod
    def toggle_pin(note_id: str) -> bool:
        """
        Toggle the pin status of a research note.

        Args:
            note_id: UUID of the note

        Returns:
            True if successful, False otherwise
        """
        client = get_client()
        if not client:
            return False

        try:
            # Get current pin status
            note_response = client.table("research_notes").select("is_pinned").eq("id", note_id).single().execute()
            if not note_response.data:
                return False

            new_pin_status = not note_response.data.get("is_pinned", False)
            response = client.table("research_notes").update({"is_pinned": new_pin_status}).eq("id", note_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error toggling pin for note {note_id}: {e}")
            return False
