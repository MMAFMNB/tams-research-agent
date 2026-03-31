"""
Research Notes System (Task 28)

Attach timestamped notes to any ticker with full CRUD operations,
pinning, archiving, and full-text search capabilities.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
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
NOTES_FILE = Path(__file__).parent / "research_notes.json"

# Thread-safe lock for JSON operations
_notes_lock = threading.Lock()


def _load_notes() -> Dict[str, Any]:
    """Load notes from JSON file, creating empty structure if needed."""
    if not NOTES_FILE.exists():
        return {"notes": {}, "metadata": {"version": 1, "created_at": datetime.utcnow().isoformat()}}

    with _notes_lock:
        try:
            with open(NOTES_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"notes": {}, "metadata": {"version": 1, "created_at": datetime.utcnow().isoformat()}}


def _save_notes(data: Dict[str, Any]) -> None:
    """Save notes to JSON file in thread-safe manner."""
    with _notes_lock:
        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(NOTES_FILE, "w") as f:
            json.dump(data, f, indent=2)


def _calculate_next_run(last_run: Optional[str], frequency: str) -> str:
    """Calculate next run datetime based on frequency."""
    from dateutil.relativedelta import relativedelta

    if last_run:
        last_dt = datetime.fromisoformat(last_run)
    else:
        last_dt = datetime.utcnow()

    if frequency == "daily":
        next_dt = last_dt + relativedelta(days=1)
    elif frequency == "weekly":
        next_dt = last_dt + relativedelta(weeks=1)
    elif frequency == "monthly":
        next_dt = last_dt + relativedelta(months=1)
    else:
        next_dt = last_dt

    return next_dt.isoformat()


def add_note(
    user_id: str,
    ticker: str,
    content: str,
    tags: Optional[List[str]] = None,
    report_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new research note.

    Args:
        user_id: User identifier
        ticker: Stock ticker symbol
        content: Markdown content of the note
        tags: Optional list of tag strings
        report_id: Optional link to a report

    Returns:
        The created note object
    """
    note_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    note = {
        "id": note_id,
        "user_id": user_id,
        "ticker": ticker.upper(),
        "content": content,
        "tags": tags or [],
        "report_id": report_id,
        "is_pinned": False,
        "is_archived": False,
        "created_at": now,
        "updated_at": now
    }

    data = _load_notes()
    data["notes"][note_id] = note
    _save_notes(data)

    return note


def get_notes(
    ticker: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Query notes with optional filters.

    Args:
        ticker: Filter by ticker (case-insensitive)
        user_id: Filter by user
        tags: Filter by tags (returns notes with ANY of these tags)
        limit: Maximum number of notes to return

    Returns:
        List of matching notes, pinned first, most recent first
    """
    data = _load_notes()
    notes = list(data["notes"].values())

    # Filter out archived notes
    notes = [n for n in notes if not n.get("is_archived", False)]

    # Apply filters
    if ticker:
        notes = [n for n in notes if n["ticker"] == ticker.upper()]

    if user_id:
        notes = [n for n in notes if n["user_id"] == user_id]

    if tags:
        notes = [n for n in notes if any(tag in n.get("tags", []) for tag in tags)]

    # Sort: pinned first, then by updated_at descending
    notes.sort(key=lambda n: (-n.get("is_pinned", False), -datetime.fromisoformat(n["updated_at"]).timestamp()))

    return notes[:limit]


def update_note(
    note_id: str,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Edit an existing note.

    Args:
        note_id: UUID of the note
        content: New markdown content (optional)
        tags: New list of tags (optional)

    Returns:
        Updated note object or None if not found
    """
    data = _load_notes()

    if note_id not in data["notes"]:
        return None

    note = data["notes"][note_id]

    if content is not None:
        note["content"] = content

    if tags is not None:
        note["tags"] = tags

    note["updated_at"] = datetime.utcnow().isoformat()

    _save_notes(data)
    return note


def delete_note(note_id: str) -> bool:
    """
    Soft delete a note (mark as archived).

    Args:
        note_id: UUID of the note

    Returns:
        True if deleted, False if not found
    """
    data = _load_notes()

    if note_id not in data["notes"]:
        return False

    data["notes"][note_id]["is_archived"] = True
    data["notes"][note_id]["updated_at"] = datetime.utcnow().isoformat()

    _save_notes(data)
    return True


def search_notes(query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Full-text search across all notes.

    Args:
        query: Search query string
        user_id: Optional filter by user

    Returns:
        List of matching notes, most recent first
    """
    data = _load_notes()
    notes = list(data["notes"].values())

    # Filter out archived
    notes = [n for n in notes if not n.get("is_archived", False)]

    # Filter by user if specified
    if user_id:
        notes = [n for n in notes if n["user_id"] == user_id]

    # Search in content and tags (case-insensitive)
    query_lower = query.lower()
    results = [
        n for n in notes
        if query_lower in n.get("content", "").lower()
        or query_lower in n.get("ticker", "").lower()
        or any(query_lower in tag.lower() for tag in n.get("tags", []))
    ]

    # Sort by updated_at descending
    results.sort(key=lambda n: -datetime.fromisoformat(n["updated_at"]).timestamp())

    return results


def pin_note(note_id: str) -> bool:
    """
    Pin a note (shows first in listings).

    Args:
        note_id: UUID of the note

    Returns:
        True if pinned, False if not found
    """
    data = _load_notes()

    if note_id not in data["notes"]:
        return False

    data["notes"][note_id]["is_pinned"] = True
    data["notes"][note_id]["updated_at"] = datetime.utcnow().isoformat()

    _save_notes(data)
    return True


def unpin_note(note_id: str) -> bool:
    """
    Unpin a note.

    Args:
        note_id: UUID of the note

    Returns:
        True if unpinned, False if not found
    """
    data = _load_notes()

    if note_id not in data["notes"]:
        return False

    data["notes"][note_id]["is_pinned"] = False
    data["notes"][note_id]["updated_at"] = datetime.utcnow().isoformat()

    _save_notes(data)
    return True


def get_pinned_notes(ticker: str) -> List[Dict[str, Any]]:
    """
    Get pinned notes for a specific ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of pinned notes for the ticker
    """
    data = _load_notes()
    notes = list(data["notes"].values())

    pinned = [
        n for n in notes
        if n["ticker"] == ticker.upper()
        and n.get("is_pinned", False)
        and not n.get("is_archived", False)
    ]

    pinned.sort(key=lambda n: -datetime.fromisoformat(n["updated_at"]).timestamp())

    return pinned


def render_notes_panel(ticker: str, user_id: str) -> None:
    """
    Streamlit UI component for research notes management.

    Renders:
    - Form to add new note (text area + tags input)
    - List of existing notes with pin/edit/delete actions
    - Search bar for filtering notes
    - Glass card styling with TAM colors

    Args:
        ticker: Stock ticker to display notes for
        user_id: Current user ID
    """
    if not STREAMLIT_AVAILABLE:
        print(f"Streamlit not available. Use add_note() and get_notes() directly.")
        return

    st.markdown("### Research Notes")

    # Search bar
    search_query = st.text_input("Search notes...", key=f"search_{ticker}")

    # Add note form
    with st.form(key=f"add_note_{ticker}"):
        st.markdown("**Add New Note**")

        note_content = st.text_area(
            "Note content (markdown supported)",
            height=120,
            key=f"note_content_{ticker}"
        )

        tags_input = st.text_input(
            "Tags (comma-separated)",
            key=f"note_tags_{ticker}"
        )

        submitted = st.form_submit_button("Add Note")

        if submitted and note_content:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            note = add_note(
                user_id=user_id,
                ticker=ticker,
                content=note_content,
                tags=tags or None
            )
            st.success(f"Note added!")
            st.rerun()

    st.divider()

    # Display notes
    if search_query:
        notes = search_notes(search_query, user_id=user_id)
        notes = [n for n in notes if n["ticker"] == ticker.upper()]
    else:
        notes = get_notes(ticker=ticker, user_id=user_id)

    if not notes:
        st.info(f"No notes for {ticker}")
        return

    for note in notes:
        # Glass card container
        with stylable_container(
            key=f"note_{note['id']}",
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
            # Header with pin/edit/delete
            col1, col2, col3, col4 = st.columns([0.7, 0.1, 0.1, 0.1])

            with col1:
                created = datetime.fromisoformat(note["created_at"])
                st.markdown(
                    f"<span style='color:{C_TEXT2}; font-size: 0.85em'>"
                    f"{created.strftime('%Y-%m-%d %H:%M')}</span>",
                    unsafe_allow_html=True
                )

            with col2:
                pin_label = "📌 Unpin" if note.get("is_pinned") else "📍 Pin"
                if st.button(pin_label, key=f"pin_{note['id']}", use_container_width=True):
                    if note.get("is_pinned"):
                        unpin_note(note["id"])
                    else:
                        pin_note(note["id"])
                    st.rerun()

            with col3:
                if st.button("✏️ Edit", key=f"edit_{note['id']}", use_container_width=True):
                    st.session_state[f"edit_{note['id']}"] = True

            with col4:
                if st.button("🗑️ Delete", key=f"delete_{note['id']}", use_container_width=True):
                    delete_note(note["id"])
                    st.success("Note deleted")
                    st.rerun()

            # Content
            st.markdown(note["content"])

            # Tags
            if note.get("tags"):
                tag_str = " ".join([f"🏷️ `{tag}`" for tag in note["tags"]])
                st.markdown(tag_str, unsafe_allow_html=True)

            # Edit mode
            if st.session_state.get(f"edit_{note['id']}", False):
                with st.form(key=f"edit_form_{note['id']}"):
                    new_content = st.text_area(
                        "Edit content",
                        value=note["content"],
                        height=100,
                        key=f"edit_content_{note['id']}"
                    )

                    new_tags = st.text_input(
                        "Edit tags",
                        value=", ".join(note.get("tags", [])),
                        key=f"edit_tags_{note['id']}"
                    )

                    if st.form_submit_button("Save Changes"):
                        tags = [t.strip() for t in new_tags.split(",") if t.strip()] if new_tags else []
                        update_note(note["id"], content=new_content, tags=tags or None)
                        st.session_state[f"edit_{note['id']}"] = False
                        st.success("Note updated")
                        st.rerun()


if __name__ == "__main__":
    # Example usage
    print("Research Notes System")

    # Create a note
    note = add_note(
        user_id="user_123",
        ticker="AAPL",
        content="# Apple Analysis\nStrong Q1 earnings expected.",
        tags=["earnings", "bullish"],
        report_id=None
    )
    print(f"Created note: {note['id']}")

    # Get notes
    notes = get_notes(ticker="AAPL")
    print(f"Found {len(notes)} notes for AAPL")

    # Search
    results = search_notes("earnings", user_id="user_123")
    print(f"Search results: {len(results)}")
