"""
Structured memory storage for user preferences, corrections, and learnings.

Works with local JSON fallback (data/memory/memories.json) and optionally Supabase.
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MEMORY_FILE = Path(__file__).parent / "memories.json"
_lock = threading.Lock()

# Valid memory categories
CATEGORIES = ("preference", "correction", "learning", "ticker_context")


def _load_memories() -> List[Dict]:
    """Load all memories from JSON file."""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load memories: {e}")
    return []


def _save_memories(memories: List[Dict]):
    """Save memories to JSON file."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2, ensure_ascii=False, default=str)


def add_memory(
    category: str,
    key: str,
    value: Any,
    user_id: str = "default",
    source: str = "explicit",
    confidence: float = 1.0,
) -> Dict:
    """
    Add or update a memory entry.

    Args:
        category: One of "preference", "correction", "learning", "ticker_context"
        key: Lookup key (e.g., "default_formats", "2222_peer_group")
        value: The memory content (string, list, dict, etc.)
        user_id: User who created this memory
        source: "explicit" (user said it) or "inferred" (observed pattern)
        confidence: 0.0-1.0, how confident we are this is correct

    Returns:
        The created/updated memory entry
    """
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category: {category}. Must be one of {CATEGORIES}")

    memories = _load_memories()

    # Check for existing entry with same category + key
    existing = None
    for i, m in enumerate(memories):
        if m.get("category") == category and m.get("key") == key and m.get("user_id") == user_id:
            existing = i
            break

    entry = {
        "category": category,
        "key": key,
        "value": value,
        "user_id": user_id,
        "source": source,
        "confidence": confidence,
        "access_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    if existing is not None:
        # Update existing — preserve created_at and access_count
        entry["created_at"] = memories[existing].get("created_at", entry["created_at"])
        entry["access_count"] = memories[existing].get("access_count", 0)
        memories[existing] = entry
        logger.info(f"Updated memory: {category}/{key}")
    else:
        memories.append(entry)
        logger.info(f"Added memory: {category}/{key}")

    _save_memories(memories)
    return entry


def get_memory(category: str, key: str, user_id: str = "default") -> Optional[Any]:
    """Get a specific memory value by category and key."""
    memories = _load_memories()
    for m in memories:
        if m.get("category") == category and m.get("key") == key and m.get("user_id") == user_id:
            # Increment access count
            m["access_count"] = m.get("access_count", 0) + 1
            _save_memories(memories)
            return m.get("value")
    return None


def get_memories_by_category(category: str, user_id: str = "default") -> List[Dict]:
    """Get all memories in a category."""
    memories = _load_memories()
    return [m for m in memories if m.get("category") == category and m.get("user_id") == user_id]


def get_ticker_memories(ticker: str, user_id: str = "default") -> List[Dict]:
    """Get all memories related to a specific ticker."""
    memories = _load_memories()
    return [
        m for m in memories
        if m.get("user_id") == user_id and (
            m.get("key", "").startswith(f"{ticker}_")
            or ticker in str(m.get("value", ""))
        )
    ]


def get_all_memories(user_id: str = "default") -> List[Dict]:
    """Get all memories for a user."""
    memories = _load_memories()
    return [m for m in memories if m.get("user_id") == user_id]


def delete_memory(category: str, key: str, user_id: str = "default") -> bool:
    """Delete a specific memory. Returns True if found and deleted."""
    memories = _load_memories()
    original_len = len(memories)
    memories = [
        m for m in memories
        if not (m.get("category") == category and m.get("key") == key and m.get("user_id") == user_id)
    ]
    if len(memories) < original_len:
        _save_memories(memories)
        logger.info(f"Deleted memory: {category}/{key}")
        return True
    return False


def decay_confidence(days_threshold: int = 30):
    """
    Reduce confidence of inferred memories that haven't been accessed recently.

    Explicit memories (user directly stated) don't decay.
    """
    memories = _load_memories()
    now = datetime.now()
    changed = False

    for m in memories:
        if m.get("source") != "inferred":
            continue
        updated = datetime.fromisoformat(m.get("updated_at", now.isoformat()))
        age_days = (now - updated).days
        if age_days > days_threshold and m.get("confidence", 1.0) > 0.3:
            m["confidence"] = max(0.3, m["confidence"] - 0.1)
            changed = True

    if changed:
        _save_memories(memories)
        logger.info("Decayed confidence of stale inferred memories")
