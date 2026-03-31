"""
Audit Trail and Compliance Logging (Task 30)

CMA-compliant audit logging for all sensitive operations. Append-only audit
trail with no update/delete functions to ensure tamper-proof records.

Works with both Supabase (when available) and a local JSON fallback.

Usage:
    from data.audit_logger import (
        log_audit, get_audit_log, get_audit_summary
    )

    # Log a sensitive operation
    log_audit(
        user_id="user-uuid",
        action_type="report_export",
        resource_type="report",
        resource_id="report-uuid",
        details={"format": "PDF", "recipient": "admin@company.com"}
    )

    # Query audit trail
    entries = get_audit_log(user_id="user-uuid", action_type="login", limit=50)
    summary = get_audit_summary(days=30)
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Supabase availability check
from data.supabase_client import SUPABASE_AVAILABLE

if SUPABASE_AVAILABLE:
    from data.supabase_client import AuditDAO

logger = logging.getLogger(__name__)

# Local JSON fallback
AUDIT_LOG_PATH = Path(__file__).parent / "audit_log.json"

# Thread lock for JSON mode (append-only safety)
_audit_lock = threading.Lock()

# Valid log types
VALID_LOG_TYPES = {
    "login",
    "logout",
    "report_generate",
    "report_export",
    "admin_action",
    "alert_trigger",
    "setting_change",
    "data_access",
}

# CMA Compliance notice
CMA_COMPLIANCE_NOTICE = (
    "This audit trail is maintained in compliance with CMA regulatory requirements"
)


def _load_audit_log() -> List[Dict[str, Any]]:
    """Load audit log from JSON file. Returns empty list if file doesn't exist."""
    try:
        if AUDIT_LOG_PATH.exists():
            with open(AUDIT_LOG_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading audit log: {e}")
    return []


def _save_audit_log(entries: List[Dict[str, Any]]) -> None:
    """
    Append-only save to JSON file. Thread-safe via lock.
    """
    try:
        with _audit_lock:
            with open(AUDIT_LOG_PATH, "w") as f:
                json.dump(entries, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving audit log: {e}")


def log_audit(
    user_id: Optional[str],
    action_type: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Log an audit event (append-only, no update/delete).
    Safe to call - never raises exceptions.

    Args:
        user_id: UUID of the user (optional for system actions)
        action_type: Type of action (must be in VALID_LOG_TYPES)
        resource_type: Type of resource affected (e.g., "report", "alert_rule", "setting")
        resource_id: ID of the resource affected
        details: Optional details dict (JSON-serializable)
        ip_address: Optional IP address of the requester

    Returns:
        None (always succeeds silently)
    """
    try:
        # Validate action type
        if action_type not in VALID_LOG_TYPES:
            logger.warning(f"Unknown audit action type: {action_type}. Skipping audit log.")
            return

        now = datetime.utcnow()
        entry_id = str(uuid.uuid4())

        entry = {
            "id": entry_id,
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "timestamp": now.isoformat(),
            "compliance_notice": CMA_COMPLIANCE_NOTICE,
        }

        # Use Supabase if available
        if SUPABASE_AVAILABLE:
            try:
                AuditDAO.log(
                    user_id=user_id,
                    action=action_type,
                    resource=resource_type or "",
                    details=entry,
                )
                return
            except Exception as e:
                logger.error(f"Error logging audit to Supabase: {e}. Falling back to JSON.")

        # Fallback to JSON (append-only, thread-safe)
        entries = _load_audit_log()
        entries.append(entry)
        _save_audit_log(entries)

    except Exception as e:
        logger.error(f"Error logging audit event: {e}")
        # Never raise - this is a logging function


def get_audit_log(
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Query audit log with optional filters.

    Args:
        user_id: Optional filter by user
        action_type: Optional filter by action type
        start_date: Optional filter by start date (inclusive)
        end_date: Optional filter by end date (inclusive)
        limit: Maximum number of entries to return

    Returns:
        List of audit log entry dicts, newest first
    """
    try:
        if SUPABASE_AVAILABLE:
            try:
                # Query Supabase
                from data.supabase_client import get_client
                client = get_client()
                if client:
                    query = client.table("audit_log").select("*")
                    if user_id:
                        query = query.eq("user_id", user_id)
                    if action_type:
                        query = query.eq("action", action_type)
                    response = query.order("created_at", desc=True).limit(limit).execute()
                    entries = response.data if response.data else []
                    # Apply date filters post-fetch
                    return _filter_by_date(entries, start_date, end_date)
            except Exception as e:
                logger.error(f"Error querying Supabase: {e}. Falling back to JSON.")

        # Fallback to JSON
        entries = _load_audit_log()

        # Apply filters
        if user_id:
            entries = [e for e in entries if e.get("user_id") == user_id]
        if action_type:
            entries = [e for e in entries if e.get("action_type") == action_type]

        # Filter by date
        entries = _filter_by_date(entries, start_date, end_date)

        # Sort by timestamp descending (newest first)
        entries.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )

        return entries[:limit]

    except Exception as e:
        logger.error(f"Error querying audit log: {e}")
        return []


def _filter_by_date(
    entries: List[Dict[str, Any]],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> List[Dict[str, Any]]:
    """Helper to filter entries by date range."""
    if not start_date and not end_date:
        return entries

    filtered = []
    for entry in entries:
        timestamp_str = entry.get("timestamp", "")
        if not timestamp_str:
            continue

        try:
            entry_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if start_date and entry_date < start_date:
            continue
        if end_date and entry_date > end_date:
            continue

        filtered.append(entry)

    return filtered


def get_audit_summary(days: int = 30) -> Dict[str, Any]:
    """
    Get aggregated audit statistics.

    Args:
        days: Number of days to include

    Returns:
        Dict with keys:
            - total_events: Total number of audit events
            - by_action_type: Dict of action_type -> count
            - by_user: Dict of user_id -> count
            - by_resource_type: Dict of resource_type -> count
            - critical_actions: List of critical action entries (logins, exports, admin actions)
            - compliance_notice: CMA compliance notice
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        if SUPABASE_AVAILABLE:
            try:
                from data.supabase_client import get_client
                client = get_client()
                if client:
                    cutoff_str = cutoff_date.isoformat()
                    response = client.table("audit_log").select("*").gte(
                        "created_at", cutoff_str
                    ).execute()
                    entries = response.data if response.data else []
                    return _compute_summary(entries)
            except Exception as e:
                logger.error(f"Error querying Supabase: {e}. Falling back to JSON.")

        # Fallback to JSON
        entries = get_audit_log(start_date=cutoff_date, limit=100000)
        return _compute_summary(entries)

    except Exception as e:
        logger.error(f"Error computing audit summary: {e}")
        return {
            "total_events": 0,
            "by_action_type": {},
            "by_user": {},
            "by_resource_type": {},
            "critical_actions": [],
            "compliance_notice": CMA_COMPLIANCE_NOTICE,
        }


def _compute_summary(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to compute summary from audit entries."""
    action_counts = defaultdict(int)
    user_counts = defaultdict(int)
    resource_counts = defaultdict(int)
    critical_actions = []

    for entry in entries:
        action = entry.get("action_type")
        user_id = entry.get("user_id")
        resource_type = entry.get("resource_type")

        if action:
            action_counts[action] += 1

            # Track critical actions
            if action in ["login", "logout", "report_export", "admin_action"]:
                critical_actions.append({
                    "timestamp": entry.get("timestamp"),
                    "action_type": action,
                    "user_id": user_id,
                    "resource_type": resource_type,
                })

        if user_id:
            user_counts[user_id] += 1

        if resource_type:
            resource_counts[resource_type] += 1

    return {
        "total_events": len(entries),
        "by_action_type": dict(action_counts),
        "by_user": dict(sorted(
            user_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )),
        "by_resource_type": dict(resource_counts),
        "critical_actions": sorted(
            critical_actions,
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )[:50],  # Most recent 50
        "compliance_notice": CMA_COMPLIANCE_NOTICE,
    }
