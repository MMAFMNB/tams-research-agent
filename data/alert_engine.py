"""In-app alert engine with cooldown periods and notification history."""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

ALERT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "watchlist_data")
ALERT_HISTORY_FILE = os.path.join(ALERT_DIR, "alert_history.json")

# Cooldown: don't re-alert for the same ticker+type within this window
COOLDOWN_HOURS = 4
MAX_HISTORY = 100  # keep last N alerts


def _load_history() -> list:
    os.makedirs(ALERT_DIR, exist_ok=True)
    if os.path.exists(ALERT_HISTORY_FILE):
        try:
            with open(ALERT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_history(history: list):
    os.makedirs(ALERT_DIR, exist_ok=True)
    with open(ALERT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)


def _cooldown_key(ticker: str, alert_type: str) -> str:
    return f"{ticker}:{alert_type}"


def is_on_cooldown(ticker: str, alert_type: str) -> bool:
    """Check if an alert for this ticker+type is still in cooldown."""
    history = _load_history()
    key = _cooldown_key(ticker, alert_type)
    cutoff = (datetime.now() - timedelta(hours=COOLDOWN_HOURS)).isoformat()

    for entry in reversed(history):
        if entry.get("cooldown_key") == key and entry["timestamp"] > cutoff:
            return True
    return False


def record_alert(ticker: str, alert_type: str, severity: str,
                 message: str) -> Optional[dict]:
    """Record an alert if not on cooldown.

    Returns the alert dict if recorded, None if suppressed by cooldown.
    """
    if is_on_cooldown(ticker, alert_type):
        return None

    entry = {
        "ticker": ticker,
        "type": alert_type,
        "severity": severity,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "display_time": datetime.now().strftime("%b %d, %H:%M"),
        "is_read": False,
        "cooldown_key": _cooldown_key(ticker, alert_type),
    }

    history = _load_history()
    history.append(entry)
    _save_history(history)
    return entry


def process_monitor_alerts(monitor_alerts: list) -> list:
    """Process raw alerts from the market monitor, applying cooldown.

    Args:
        monitor_alerts: List of alert dicts from market_monitor.get_all_alerts()

    Returns:
        List of newly recorded alerts (cooldown-filtered).
    """
    new_alerts = []
    for alert in monitor_alerts:
        result = record_alert(
            ticker=alert.get("ticker", ""),
            alert_type=alert.get("type", "unknown"),
            severity=alert.get("severity", "moderate"),
            message=alert.get("message", ""),
        )
        if result:
            new_alerts.append(result)
    return new_alerts


def get_recent_alerts(limit: int = 20) -> list:
    """Get recent alerts, newest first."""
    history = _load_history()
    return list(reversed(history[-limit:]))


def get_unread_count() -> int:
    """Get count of unread alerts."""
    return sum(1 for a in _load_history() if not a.get("is_read"))


def mark_all_read():
    """Mark all alerts as read."""
    history = _load_history()
    for entry in history:
        entry["is_read"] = True
    _save_history(history)


def clear_history():
    """Clear all alert history."""
    _save_history([])
