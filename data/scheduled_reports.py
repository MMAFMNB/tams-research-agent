"""
Scheduled Report Generation (Task 29)

Configuration and storage layer for recurring report generation.
This manages the scheduling config; actual execution would use APScheduler or Supabase cron.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
import threading

try:
    import streamlit as st
    from streamlit_extras.stylable_container import stylable_container
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# TAM Brand Colors
C_CARD = "rgba(26,38,78,0.15)"
C_BORDER = "rgba(108,185,182,0.08)"
C_ACCENT = "#1A6DB6"
C_TEXT = "#E6EDF3"
C_TEXT2 = "#8B949E"
C_MUTED = "#4A5568"
C_GREEN = "#22C55E"

# Data file path
SCHEDULES_FILE = Path(__file__).parent / "scheduled_reports.json"

# Thread-safe lock for JSON operations
_schedules_lock = threading.Lock()

# Type definitions
FrequencyType = Literal["daily", "weekly", "monthly"]
ReportType = Literal["full", "brief", "watchlist_refresh"]


def _load_schedules() -> Dict[str, Any]:
    """Load schedules from JSON file, creating empty structure if needed."""
    if not SCHEDULES_FILE.exists():
        return {"schedules": {}, "metadata": {"version": 1, "created_at": datetime.utcnow().isoformat()}}

    with _schedules_lock:
        try:
            with open(SCHEDULES_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"schedules": {}, "metadata": {"version": 1, "created_at": datetime.utcnow().isoformat()}}


def _save_schedules(data: Dict[str, Any]) -> None:
    """Save schedules to JSON file in thread-safe manner."""
    with _schedules_lock:
        SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULES_FILE, "w") as f:
            json.dump(data, f, indent=2)


def _calculate_next_run(last_run_at: Optional[str], frequency: FrequencyType) -> str:
    """
    Calculate next run datetime based on frequency.

    Args:
        last_run_at: ISO timestamp of last run (or None for first run)
        frequency: "daily", "weekly", or "monthly"

    Returns:
        ISO timestamp of next scheduled run
    """
    if last_run_at:
        last_dt = datetime.fromisoformat(last_run_at)
    else:
        last_dt = datetime.utcnow()

    if frequency == "daily":
        next_dt = last_dt + timedelta(days=1)
    elif frequency == "weekly":
        next_dt = last_dt + timedelta(weeks=1)
    elif frequency == "monthly":
        # Add one month (approximate; using day-of-month)
        year = last_dt.year
        month = last_dt.month + 1
        day = last_dt.day

        if month > 12:
            month = 1
            year += 1

        # Handle day overflow (e.g., Jan 31 -> Feb 28/29)
        try:
            next_dt = last_dt.replace(year=year, month=month, day=day)
        except ValueError:
            # If day doesn't exist in target month, use last day of month
            next_dt = last_dt.replace(year=year, month=month, day=1) - timedelta(days=1)
            next_dt = next_dt.replace(day=1) + timedelta(days=31)
            next_dt = next_dt.replace(day=1) - timedelta(days=1)
    else:
        next_dt = last_dt

    return next_dt.isoformat()


def create_schedule(
    user_id: str,
    ticker: str,
    frequency: FrequencyType,
    report_type: ReportType = "full"
) -> Dict[str, Any]:
    """
    Create a new scheduled report.

    Args:
        user_id: User identifier
        ticker: Stock ticker symbol (or "watchlist" for all tickers)
        frequency: "daily", "weekly", or "monthly"
        report_type: "full", "brief", or "watchlist_refresh"

    Returns:
        The created schedule object
    """
    schedule_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    next_run = _calculate_next_run(None, frequency)

    schedule = {
        "id": schedule_id,
        "user_id": user_id,
        "ticker": ticker.upper() if ticker != "watchlist" else "watchlist",
        "frequency": frequency,
        "report_type": report_type,
        "is_active": True,
        "last_run_at": None,
        "next_run_at": next_run,
        "created_at": now
    }

    data = _load_schedules()
    data["schedules"][schedule_id] = schedule
    _save_schedules(data)

    return schedule


def get_schedules(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all schedules, optionally filtered by user.

    Args:
        user_id: Optional filter by user

    Returns:
        List of schedule objects
    """
    data = _load_schedules()
    schedules = list(data["schedules"].values())

    if user_id:
        schedules = [s for s in schedules if s["user_id"] == user_id]

    # Sort by next_run_at ascending (due soonest first)
    schedules.sort(key=lambda s: s["next_run_at"])

    return schedules


def update_schedule(schedule_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Modify an existing schedule.

    Supported kwargs:
    - frequency: new frequency ("daily", "weekly", "monthly")
    - report_type: new report type ("full", "brief", "watchlist_refresh")
    - is_active: activate/deactivate schedule
    - ticker: change target ticker

    Args:
        schedule_id: UUID of the schedule
        **kwargs: Fields to update

    Returns:
        Updated schedule object or None if not found
    """
    data = _load_schedules()

    if schedule_id not in data["schedules"]:
        return None

    schedule = data["schedules"][schedule_id]

    # Update allowed fields
    for key in ["frequency", "report_type", "is_active", "ticker"]:
        if key in kwargs:
            schedule[key] = kwargs[key]

    # If frequency changed, recalculate next_run_at
    if "frequency" in kwargs:
        schedule["next_run_at"] = _calculate_next_run(
            schedule.get("last_run_at"),
            kwargs["frequency"]
        )

    _save_schedules(data)
    return schedule


def delete_schedule(schedule_id: str) -> bool:
    """
    Remove a schedule permanently.

    Args:
        schedule_id: UUID of the schedule

    Returns:
        True if deleted, False if not found
    """
    data = _load_schedules()

    if schedule_id not in data["schedules"]:
        return False

    del data["schedules"][schedule_id]
    _save_schedules(data)
    return True


def get_due_schedules() -> List[Dict[str, Any]]:
    """
    Get all active schedules that are due for execution.

    Compares next_run_at to current time.

    Returns:
        List of due schedules
    """
    data = _load_schedules()
    schedules = list(data["schedules"].values())

    now = datetime.utcnow()
    due = []

    for schedule in schedules:
        if not schedule.get("is_active", True):
            continue

        next_run = datetime.fromisoformat(schedule["next_run_at"])

        if next_run <= now:
            due.append(schedule)

    # Sort by next_run_at ascending
    due.sort(key=lambda s: s["next_run_at"])

    return due


def mark_schedule_run(schedule_id: str) -> Optional[Dict[str, Any]]:
    """
    Update a schedule after it has run (sets last_run_at and next_run_at).

    Args:
        schedule_id: UUID of the schedule

    Returns:
        Updated schedule object or None if not found
    """
    data = _load_schedules()

    if schedule_id not in data["schedules"]:
        return None

    schedule = data["schedules"][schedule_id]
    now = datetime.utcnow().isoformat()

    schedule["last_run_at"] = now
    schedule["next_run_at"] = _calculate_next_run(now, schedule["frequency"])

    _save_schedules(data)
    return schedule


def render_schedule_panel(user_id: str) -> None:
    """
    Streamlit UI component for scheduled report management.

    Renders:
    - Form to create new schedule (ticker selector, frequency dropdown, report type)
    - Table of existing schedules with active/pause toggle
    - Delete button per schedule
    - Glass card styling with TAM colors

    Args:
        user_id: Current user ID
    """
    if not STREAMLIT_AVAILABLE:
        print(f"Streamlit not available. Use create_schedule() and get_schedules() directly.")
        return

    st.markdown("### Scheduled Reports")

    # Create schedule form
    with st.form(key="create_schedule"):
        st.markdown("**Create New Schedule**")

        col1, col2, col3 = st.columns(3)

        with col1:
            ticker_input = st.text_input(
                "Ticker (or 'watchlist' for all)",
                value="AAPL",
                key="schedule_ticker"
            )

        with col2:
            frequency = st.selectbox(
                "Frequency",
                options=["daily", "weekly", "monthly"],
                key="schedule_frequency"
            )

        with col3:
            report_type = st.selectbox(
                "Report Type",
                options=["full", "brief", "watchlist_refresh"],
                key="schedule_report_type"
            )

        submitted = st.form_submit_button("Create Schedule")

        if submitted and ticker_input:
            schedule = create_schedule(
                user_id=user_id,
                ticker=ticker_input.lower(),
                frequency=frequency,
                report_type=report_type
            )
            st.success(f"Schedule created for {ticker_input}")
            st.rerun()

    st.divider()

    # List existing schedules
    schedules = get_schedules(user_id=user_id)

    if not schedules:
        st.info("No schedules configured")
        return

    # Table header
    st.markdown("**Your Schedules**")

    for schedule in schedules:
        with stylable_container(
            key=f"schedule_{schedule['id']}",
            css_styles=f"""
            {{
                border: 1px solid {C_BORDER};
                border-radius: 8px;
                padding: 12px;
                background-color: {C_CARD};
                margin-bottom: 12px;
            }}
            """
        ):
            col1, col2, col3, col4 = st.columns([0.4, 0.3, 0.2, 0.1])

            with col1:
                ticker_display = schedule["ticker"].upper() if schedule["ticker"] != "watchlist" else "📊 Watchlist"
                st.markdown(
                    f"<span style='color:{C_TEXT}; font-weight: bold'>{ticker_display}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<span style='color:{C_TEXT2}; font-size: 0.85em'>{schedule['report_type']} ({schedule['frequency']})</span>",
                    unsafe_allow_html=True
                )

            with col2:
                if schedule.get("last_run_at"):
                    last_run = datetime.fromisoformat(schedule["last_run_at"])
                    st.markdown(
                        f"<span style='color:{C_TEXT2}; font-size: 0.85em'>Last: {last_run.strftime('%m/%d %H:%M')}</span>",
                        unsafe_allow_html=True
                    )

                next_run = datetime.fromisoformat(schedule["next_run_at"])
                color = C_GREEN if next_run <= datetime.utcnow() else C_TEXT2
                st.markdown(
                    f"<span style='color:{color}; font-size: 0.85em'>Next: {next_run.strftime('%m/%d %H:%M')}</span>",
                    unsafe_allow_html=True
                )

            with col3:
                is_active = schedule.get("is_active", True)
                toggle_label = "⏸️ Pause" if is_active else "▶️ Resume"

                if st.button(toggle_label, key=f"toggle_{schedule['id']}", use_container_width=True):
                    update_schedule(schedule["id"], is_active=not is_active)
                    st.rerun()

            with col4:
                if st.button("🗑️", key=f"delete_{schedule['id']}", use_container_width=True):
                    delete_schedule(schedule["id"])
                    st.success("Schedule deleted")
                    st.rerun()

    st.divider()

    # Show due schedules
    due_schedules = get_due_schedules()

    if due_schedules:
        st.warning(f"⚠️ {len(due_schedules)} report(s) ready to run")

        for schedule in due_schedules:
            st.markdown(
                f"• {schedule['ticker'].upper()} - {schedule['report_type']} report"
            )


if __name__ == "__main__":
    # Example usage
    print("Scheduled Reports System")

    # Create a schedule
    schedule = create_schedule(
        user_id="user_123",
        ticker="AAPL",
        frequency="daily",
        report_type="full"
    )
    print(f"Created schedule: {schedule['id']}")

    # Get schedules
    all_schedules = get_schedules(user_id="user_123")
    print(f"Found {len(all_schedules)} schedules")

    # Get due schedules
    due = get_due_schedules()
    print(f"Due schedules: {len(due)}")

    # Mark as run
    updated = mark_schedule_run(schedule["id"])
    print(f"Marked as run: {updated['last_run_at']}")
