"""
Preference Tracker — observes user interactions and infers preferences.

Learns from:
- Which tickers the user analyzes repeatedly
- Which sections they request most
- Which export formats they choose
- Corrections they make to outputs
- Positive/negative feedback on reports

Generates a context string that gets injected into Claude prompts.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional

from data.memory.memory_store import (
    add_memory, get_memory, get_memories_by_category,
    get_ticker_memories, get_all_memories,
)

logger = logging.getLogger(__name__)

# Minimum observations before creating an inferred preference
INFERENCE_THRESHOLD = 3


def observe_analysis_request(
    user_id: str,
    ticker: str,
    sections: List[str],
    formats: List[str],
):
    """
    Called after each analysis request to track patterns.

    Tracks: which tickers are analyzed, which sections requested, which formats chosen.
    """
    # Track ticker frequency
    ticker_counts = get_memory("preference", "ticker_frequency", user_id) or {}
    ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
    add_memory("preference", "ticker_frequency", ticker_counts, user_id, source="inferred")

    # Track format frequency
    if formats:
        format_counts = get_memory("preference", "format_frequency", user_id) or {}
        for fmt in formats:
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        add_memory("preference", "format_frequency", format_counts, user_id, source="inferred")

    # Track section frequency
    if sections:
        section_counts = get_memory("preference", "section_frequency", user_id) or {}
        for sec in sections:
            section_counts[sec] = section_counts.get(sec, 0) + 1
        add_memory("preference", "section_frequency", section_counts, user_id, source="inferred")

    # Infer: if a ticker has been analyzed 3+ times, it's a favorite
    if ticker_counts.get(ticker, 0) >= INFERENCE_THRESHOLD:
        favorites = get_memory("preference", "favorite_tickers", user_id) or []
        if ticker not in favorites:
            favorites.append(ticker)
            add_memory("preference", "favorite_tickers", favorites, user_id, source="inferred", confidence=0.8)
            logger.info(f"Inferred favorite ticker: {ticker}")


def observe_correction(
    user_id: str,
    original: str,
    corrected: str,
    context: str = "",
):
    """
    Called when user corrects an output.

    Corrections are always explicit and high-priority.
    """
    key = f"correction_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    add_memory(
        category="correction",
        key=key,
        value={
            "original": original,
            "corrected": corrected,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        },
        user_id=user_id,
        source="explicit",
        confidence=1.0,
    )
    logger.info(f"Recorded correction for user {user_id}")


def observe_feedback(
    user_id: str,
    ticker: str,
    action: str,
    feedback_type: str,  # "positive" or "negative"
    details: str = "",
):
    """
    Called when user gives thumbs up/down or edits a section.

    Positive: reinforces the approach.
    Negative: records what went wrong.
    """
    key = f"feedback_{ticker}_{action}"
    existing = get_memory("learning", key, user_id) or {"positive": 0, "negative": 0, "notes": []}

    if feedback_type == "positive":
        existing["positive"] = existing.get("positive", 0) + 1
    else:
        existing["negative"] = existing.get("negative", 0) + 1

    if details:
        notes = existing.get("notes", [])
        notes.append({"type": feedback_type, "detail": details, "date": datetime.now().isoformat()})
        existing["notes"] = notes[-10:]  # Keep last 10 notes

    add_memory("learning", key, existing, user_id, source="explicit")


def get_user_context(user_id: str) -> str:
    """
    Generate a context string for Claude prompts based on user's memories.

    This string is injected as a preamble to help Claude personalize responses.
    Returns empty string if no meaningful preferences exist.
    """
    parts = []

    # Favorite tickers
    favorites = get_memory("preference", "favorite_tickers", user_id)
    if favorites:
        parts.append(f"User's frequently analyzed tickers: {', '.join(favorites)}")

    # Preferred formats
    format_freq = get_memory("preference", "format_frequency", user_id)
    if format_freq:
        top_formats = sorted(format_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        parts.append(f"Preferred export formats: {', '.join(f[0] for f in top_formats)}")

    # Recent corrections (high priority)
    corrections = get_memories_by_category("correction", user_id)
    if corrections:
        recent = sorted(corrections, key=lambda x: x.get("updated_at", ""), reverse=True)[:5]
        correction_lines = []
        for c in recent:
            val = c.get("value", {})
            if isinstance(val, dict) and val.get("corrected"):
                correction_lines.append(f"- {val['corrected']}")
        if correction_lines:
            parts.append("User corrections to apply:\n" + "\n".join(correction_lines))

    # Learnings from feedback
    learnings = get_memories_by_category("learning", user_id)
    negative_learnings = []
    for l in learnings:
        val = l.get("value", {})
        if isinstance(val, dict) and val.get("negative", 0) > val.get("positive", 0):
            notes = val.get("notes", [])
            neg_notes = [n["detail"] for n in notes if n.get("type") == "negative" and n.get("detail")]
            if neg_notes:
                negative_learnings.append(f"- {l['key']}: {neg_notes[-1]}")
    if negative_learnings:
        parts.append("Areas to improve (user feedback):\n" + "\n".join(negative_learnings[:5]))

    if not parts:
        return ""

    return "USER PREFERENCES (from memory):\n" + "\n".join(parts)


def get_ticker_context(ticker: str, user_id: str = "default") -> str:
    """
    Get ticker-specific context for injection into analysis prompts.

    Returns context like peer group corrections, name preferences, etc.
    """
    memories = get_ticker_memories(ticker, user_id)
    if not memories:
        return ""

    parts = []
    for m in memories:
        if m.get("category") == "ticker_context":
            parts.append(f"- {m['key']}: {m['value']}")
        elif m.get("category") == "correction":
            val = m.get("value", {})
            if isinstance(val, dict) and val.get("corrected"):
                parts.append(f"- Correction: {val['corrected']}")

    if not parts:
        return ""

    return f"TICKER CONTEXT for {ticker}:\n" + "\n".join(parts)
