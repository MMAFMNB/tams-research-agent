"""
Unified data layer that transparently switches between JSON (existing) and Supabase (new).

This module routes all data access through either JSON-based or Supabase-based backends
depending on whether Supabase is configured. The rest of the app doesn't need to know
which backend is active.

Usage:
    from data.data_layer import (
        get_watchlists, get_positions, save_report, get_recent_alerts,
        set_current_user, calculate_portfolio_metrics
    )

    set_current_user("user-id-uuid")
    watchlists = get_watchlists()
    positions = get_positions()
"""

import logging
from typing import Dict, List, Optional, Any

# Supabase availability check
from data.supabase_client import SUPABASE_AVAILABLE

# Import JSON-based modules (existing)
from data import watchlist as json_watchlist
from data import portfolio as json_portfolio
from data import report_store as json_reports
from data import alert_engine as json_alerts

# Import Supabase DAOs if available
if SUPABASE_AVAILABLE:
    from data.supabase_client import (
        WatchlistDAO,
        PortfolioDAO,
        ReportDAO,
        AlertDAO,
        AlertRuleDAO,
        ActivityDAO,
        NotesDAO,
        AuditDAO,
        SentimentDAO,
    )

# Re-export calculate_portfolio_metrics from json_portfolio
from data.portfolio import calculate_portfolio_metrics

logger = logging.getLogger(__name__)

# Current user context (set after login, defaults to None for JSON mode)
_current_user_id: Optional[str] = None


def set_current_user(user_id: str) -> None:
    """
    Set the current user ID for Supabase operations.

    Args:
        user_id: UUID of the authenticated user
    """
    global _current_user_id
    _current_user_id = user_id
    logger.debug(f"Current user set to: {user_id}")


def get_current_user_id() -> Optional[str]:
    """Get the current user ID."""
    return _current_user_id


def _use_supabase() -> bool:
    """Check if Supabase should be used (available and user is set)."""
    return SUPABASE_AVAILABLE and _current_user_id is not None


# ============================================================================
# WATCHLIST FUNCTIONS
# ============================================================================


def get_watchlists() -> List[Dict[str, Any]]:
    """
    Get all watchlists for the current user.

    Returns:
        List of watchlist dicts with summary info (id, name, description, item_count)
    """
    if _use_supabase():
        watchlists = WatchlistDAO.get_user_watchlists(_current_user_id)
        # Format to match JSON structure
        return [
            {
                "id": wl.get("id"),
                "name": wl.get("name", ""),
                "description": wl.get("description", ""),
                "is_default": wl.get("is_default", False),
                "item_count": len(wl.get("items", [])) if "items" in wl else 0,
            }
            for wl in watchlists
        ]
    return json_watchlist.get_watchlists()


def get_default_watchlist() -> Optional[Dict[str, Any]]:
    """
    Get the default watchlist for the current user.

    Returns:
        Watchlist dict or None if no default exists
    """
    if _use_supabase():
        return WatchlistDAO.get_default(_current_user_id)
    return json_watchlist.get_default_watchlist()


def create_watchlist(
    name: str, description: str = "", is_default: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Create a new watchlist.

    Args:
        name: Watchlist name
        description: Optional description
        is_default: Whether this is the default watchlist

    Returns:
        Created watchlist dict or None
    """
    if _use_supabase():
        return WatchlistDAO.create(_current_user_id, name, description, is_default)
    return json_watchlist.create_watchlist(name, description)


def add_ticker_to_watchlist(
    watchlist_id: int | str, ticker: str, name: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Add a ticker to a watchlist.

    Args:
        watchlist_id: ID of the watchlist
        ticker: Stock ticker symbol
        name: Optional company name

    Returns:
        Created watchlist item dict or None
    """
    if _use_supabase():
        return WatchlistDAO.add_item(str(watchlist_id), ticker.upper(), name)
    return json_watchlist.add_ticker(int(watchlist_id), ticker, name)


def remove_ticker_from_watchlist(watchlist_id: int | str, ticker: str) -> bool:
    """
    Remove a ticker from a watchlist.

    Args:
        watchlist_id: ID of the watchlist
        ticker: Stock ticker symbol

    Returns:
        True if successful, False otherwise
    """
    if _use_supabase():
        # For Supabase, we need to find the item ID first
        watchlists = WatchlistDAO.get_user_watchlists(_current_user_id)
        for wl in watchlists:
            if str(wl.get("id")) == str(watchlist_id):
                # Find the item with matching ticker
                items = wl.get("items", [])
                for item in items:
                    if item.get("ticker", "").upper() == ticker.upper():
                        item_id = item.get("id")
                        if item_id:
                            return WatchlistDAO.remove_item(str(item_id))
        logger.warning(
            f"Watchlist item not found: watchlist_id={watchlist_id}, ticker={ticker}"
        )
        return False

    return json_watchlist.remove_ticker(int(watchlist_id), ticker)


def get_all_watched_tickers() -> List[str]:
    """
    Get all unique tickers across all watchlists.

    Returns:
        Sorted list of ticker symbols
    """
    if _use_supabase():
        tickers = WatchlistDAO.get_all_watched_tickers(_current_user_id)
        return sorted(tickers) if tickers else []
    return json_watchlist.get_all_watched_tickers()


# ============================================================================
# PORTFOLIO FUNCTIONS
# ============================================================================


def get_positions() -> List[Dict[str, Any]]:
    """
    Get all portfolio positions for the current user.

    Returns:
        List of position dicts
    """
    if _use_supabase():
        return PortfolioDAO.get_positions(_current_user_id)
    return json_portfolio.get_positions()


def add_position(
    ticker: str, name: str, shares: float, cost_basis: float
) -> Optional[Dict[str, Any]]:
    """
    Add a portfolio position.

    Args:
        ticker: Stock ticker symbol
        name: Company name
        shares: Number of shares
        cost_basis: Cost per share

    Returns:
        Created position dict or None
    """
    if _use_supabase():
        return PortfolioDAO.add_position(
            _current_user_id, ticker, name, shares, cost_basis
        )
    return json_portfolio.add_position(ticker, name, shares, cost_basis)


def remove_position(position_id: str | int) -> bool:
    """
    Remove a portfolio position.

    Args:
        position_id: ID of the position

    Returns:
        True if successful, False otherwise
    """
    if _use_supabase():
        result = PortfolioDAO.remove_position(str(position_id))
        return result is not None
    json_portfolio.remove_position(str(position_id))
    return True


# ============================================================================
# REPORT FUNCTIONS
# ============================================================================


def save_report(
    company_name: str,
    ticker: str,
    sections: Dict[str, Any],
    files: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Save a research report.

    Args:
        company_name: Name of the company
        ticker: Stock ticker symbol
        sections: Dict of report sections
        files: Optional files dict

    Returns:
        Report ID or None
    """
    if _use_supabase():
        report = ReportDAO.save(_current_user_id, ticker, company_name, sections, files)
        return report.get("id") if report else None
    return json_reports.save_report(company_name, ticker, sections, files=files)


def list_reports() -> List[Dict[str, Any]]:
    """
    Get all reports (not filtered by ticker).

    Returns:
        List of report summary dicts
    """
    if _use_supabase():
        # Get all reports for current user by passing empty ticker
        reports = ReportDAO.get_by_ticker("", _current_user_id)
        # Format to match JSON structure
        return [
            {
                "id": r.get("id"),
                "stock_name": r.get("company_name", ""),
                "ticker": r.get("ticker", ""),
                "version": r.get("version"),
                "date": r.get("created_at", ""),
                "date_display": r.get("created_at", "")[:10],
                "change_summary": r.get("change_summary", ""),
            }
            for r in reports
        ]
    return json_reports.list_reports()


def load_report(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a report by ID.

    Args:
        report_id: ID of the report

    Returns:
        Report dict or None
    """
    if _use_supabase():
        return ReportDAO.get_by_id(str(report_id))
    return json_reports.load_report(report_id)


def get_versions(ticker: str) -> List[Dict[str, Any]]:
    """
    Get all versions of a report for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of version dicts, newest first
    """
    if _use_supabase():
        return ReportDAO.get_versions(ticker)
    return json_reports.get_versions(ticker)


def get_reports_by_ticker(ticker: str) -> List[Dict[str, Any]]:
    """
    Get all reports for a specific ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of report dicts
    """
    if _use_supabase():
        reports = ReportDAO.get_by_ticker(ticker, _current_user_id)
        return [
            {
                "id": r.get("id"),
                "stock_name": r.get("company_name", ""),
                "ticker": r.get("ticker", ""),
                "version": r.get("version"),
                "date": r.get("created_at", ""),
                "date_display": r.get("created_at", "")[:10],
                "change_summary": r.get("change_summary", ""),
            }
            for r in reports
        ]
    return json_reports.list_reports(ticker)


# ============================================================================
# ALERT FUNCTIONS
# ============================================================================


def get_recent_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent alerts for the current user.

    Args:
        limit: Maximum number of alerts to return

    Returns:
        List of alert dicts
    """
    if _use_supabase():
        return AlertDAO.get_recent(_current_user_id, limit)
    return json_alerts.get_recent_alerts(limit)


def get_unread_count() -> int:
    """
    Get count of unread alerts for the current user.

    Returns:
        Number of unread alerts
    """
    if _use_supabase():
        return AlertDAO.get_unread_count(_current_user_id)
    return json_alerts.get_unread_count()


def mark_all_alerts_read() -> bool:
    """
    Mark all alerts as read for the current user.

    Returns:
        True if successful, False otherwise
    """
    if _use_supabase():
        result = AlertDAO.mark_all_read(_current_user_id)
        return result is not None
    json_alerts.mark_all_read()
    return True


def record_alert(
    ticker: str, alert_type: str, severity: str, message: str
) -> Optional[Dict[str, Any]]:
    """
    Record an alert (JSON only, for backward compatibility).

    Args:
        ticker: Stock ticker symbol
        alert_type: Type of alert
        severity: Alert severity
        message: Alert message

    Returns:
        Alert dict or None
    """
    if _use_supabase():
        return AlertDAO.create_alert(_current_user_id, ticker, alert_type, severity, message)
    return json_alerts.record_alert(ticker, alert_type, severity, message)


# ============================================================================
# SUPABASE-ONLY FEATURES (no JSON fallback)
# ============================================================================


def log_activity(
    action_type: str, ticker: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a user activity (Supabase only).

    Args:
        action_type: Type of action (search, analyze, view_report, etc.)
        ticker: Optional stock ticker
        metadata: Optional metadata dict
    """
    if not _use_supabase():
        logger.debug(f"Activity logging disabled (JSON mode): {action_type}")
        return

    ActivityDAO.log(_current_user_id, action_type, ticker, metadata)


def save_sentiment(
    ticker: str, report_id: Optional[str], scores: Dict[str, float]
) -> None:
    """
    Save sentiment scores for a ticker (Supabase only).

    Args:
        ticker: Stock ticker symbol
        report_id: Optional UUID of related report
        scores: Dict of category -> score (e.g., {'overall': 0.75})
    """
    if not _use_supabase():
        logger.debug(f"Sentiment logging disabled (JSON mode): {ticker}")
        return

    SentimentDAO.save_scores(ticker, report_id, scores)


def log_audit(
    action: str,
    resource: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an audit event (Supabase only).

    Args:
        action: Description of the action
        resource: Resource affected
        details: Optional details dict
    """
    if not _use_supabase():
        logger.debug(f"Audit logging disabled (JSON mode): {action}")
        return

    AuditDAO.log(_current_user_id, action, resource, details)


def get_alert_rules() -> List[Dict[str, Any]]:
    """
    Get alert rules for the current user (Supabase only).

    Returns:
        List of alert rule dicts
    """
    if not _use_supabase():
        logger.debug("Alert rules disabled (JSON mode)")
        return []

    return AlertRuleDAO.get_user_rules(_current_user_id)


def create_alert_rule(
    ticker: str, rule_type: str, parameters: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Create an alert rule (Supabase only).

    Args:
        ticker: Stock ticker symbol
        rule_type: Type of rule
        parameters: Rule parameters dict

    Returns:
        Created rule dict or None
    """
    if not _use_supabase():
        logger.debug(f"Alert rule creation disabled (JSON mode): {ticker}")
        return None

    return AlertRuleDAO.create_rule(_current_user_id, ticker, rule_type, parameters)


def delete_alert_rule(rule_id: str) -> bool:
    """
    Delete an alert rule (Supabase only).

    Args:
        rule_id: UUID of the rule

    Returns:
        True if successful, False otherwise
    """
    if not _use_supabase():
        logger.debug(f"Alert rule deletion disabled (JSON mode): {rule_id}")
        return False

    return AlertRuleDAO.delete_rule(str(rule_id))


def get_notes(ticker: str) -> List[Dict[str, Any]]:
    """
    Get research notes for a ticker (Supabase only).

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of note dicts
    """
    if not _use_supabase():
        logger.debug(f"Notes disabled (JSON mode): {ticker}")
        return []

    return NotesDAO.get_for_ticker(_current_user_id, ticker)


def create_note(
    ticker: str, content: str, tags: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a research note (Supabase only).

    Args:
        ticker: Stock ticker symbol
        content: Note content
        tags: Optional list of tags

    Returns:
        Created note dict or None
    """
    if not _use_supabase():
        logger.debug(f"Note creation disabled (JSON mode): {ticker}")
        return None

    return NotesDAO.create(_current_user_id, ticker, content, tags)


def update_note(
    note_id: str, content: str, tags: Optional[List[str]] = None
) -> bool:
    """
    Update a research note (Supabase only).

    Args:
        note_id: UUID of the note
        content: Updated content
        tags: Optional updated tags

    Returns:
        True if successful, False otherwise
    """
    if not _use_supabase():
        logger.debug(f"Note update disabled (JSON mode): {note_id}")
        return False

    return NotesDAO.update(note_id, content, tags)


def delete_note(note_id: str) -> bool:
    """
    Delete a research note (Supabase only).

    Args:
        note_id: UUID of the note

    Returns:
        True if successful, False otherwise
    """
    if not _use_supabase():
        logger.debug(f"Note deletion disabled (JSON mode): {note_id}")
        return False

    return NotesDAO.delete(note_id)


def toggle_note_pin(note_id: str) -> bool:
    """
    Toggle the pin status of a note (Supabase only).

    Args:
        note_id: UUID of the note

    Returns:
        True if successful, False otherwise
    """
    if not _use_supabase():
        logger.debug(f"Note pin toggle disabled (JSON mode): {note_id}")
        return False

    return NotesDAO.toggle_pin(note_id)
