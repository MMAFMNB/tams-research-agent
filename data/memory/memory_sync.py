"""
Memory Sync — keeps memory.md in sync with the structured memory store.

Two-way sync:
- sync_to_markdown(): Read structured memories -> regenerate memory.md
- sync_from_markdown(): Parse memory.md -> update structured store (for human edits)
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from data.memory.memory_store import get_all_memories, add_memory, get_memories_by_category

logger = logging.getLogger(__name__)

MEMORY_MD_PATH = Path(__file__).parent.parent.parent / "memory.md"


def sync_to_markdown(user_id: str = "default"):
    """
    Regenerate memory.md from the structured memory store.

    Only includes high-confidence, frequently-accessed memories.
    Groups by category for readability.
    """
    memories = get_all_memories(user_id)
    if not memories:
        logger.info("No memories to sync to markdown")
        return

    sections = {
        "preference": [],
        "correction": [],
        "learning": [],
        "ticker_context": [],
    }

    for m in memories:
        cat = m.get("category", "")
        if cat not in sections:
            continue

        # Only include memories with reasonable confidence
        if m.get("confidence", 1.0) < 0.4:
            continue

        key = m.get("key", "")
        value = m.get("value", "")
        source = m.get("source", "")

        # Format based on category
        if cat == "preference":
            if key == "favorite_tickers" and isinstance(value, list):
                sections[cat].append(f"- Frequently analyzed: {', '.join(value)}")
            elif key == "format_frequency" and isinstance(value, dict):
                top = sorted(value.items(), key=lambda x: x[1], reverse=True)[:3]
                sections[cat].append(f"- Preferred formats: {', '.join(f[0] for f in top)}")
            elif key == "section_frequency" and isinstance(value, dict):
                top = sorted(value.items(), key=lambda x: x[1], reverse=True)[:5]
                sections[cat].append(f"- Most used sections: {', '.join(f[0] for f in top)}")
            elif isinstance(value, str):
                sections[cat].append(f"- {key}: {value}")

        elif cat == "correction":
            if isinstance(value, dict) and value.get("corrected"):
                sections[cat].append(f"- {value['corrected']}")
            elif isinstance(value, str):
                sections[cat].append(f"- {value}")

        elif cat == "learning":
            if isinstance(value, dict):
                pos = value.get("positive", 0)
                neg = value.get("negative", 0)
                notes = value.get("notes", [])
                last_note = notes[-1]["detail"] if notes else ""
                sentiment = "positive" if pos > neg else "needs improvement"
                sections[cat].append(f"- {key}: {sentiment}" + (f" — {last_note}" if last_note else ""))
            elif isinstance(value, str):
                sections[cat].append(f"- {key}: {value}")

        elif cat == "ticker_context":
            sections[cat].append(f"- {key}: {value}")

    # Build markdown
    lines = ["# Memory", ""]
    lines.append(f"_Auto-synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")

    if sections["preference"]:
        lines.append("## User Preferences")
        lines.extend(sections["preference"])
        lines.append("")

    if sections["correction"]:
        lines.append("## Corrections & Learnings")
        lines.extend(sections["correction"])
        lines.append("")

    if sections["ticker_context"]:
        lines.append("## Ticker Preferences")
        lines.extend(sections["ticker_context"])
        lines.append("")

    if sections["learning"]:
        lines.append("## Feedback History")
        lines.extend(sections["learning"])
        lines.append("")

    # Preserve the Cost Preferences section (manually maintained)
    existing_cost = _extract_section(MEMORY_MD_PATH, "Cost Preferences")
    if existing_cost:
        lines.append("## Cost Preferences")
        lines.extend(existing_cost)
        lines.append("")

    content = "\n".join(lines) + "\n"

    try:
        with open(MEMORY_MD_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Synced {sum(len(v) for v in sections.values())} memories to memory.md")
    except Exception as e:
        logger.error(f"Failed to write memory.md: {e}")


def sync_from_markdown(user_id: str = "default"):
    """
    Parse memory.md and update the structured store with any new entries.

    This handles the case where a human edits memory.md directly.
    Only processes simple bullet-point entries.
    """
    if not MEMORY_MD_PATH.exists():
        return

    try:
        with open(MEMORY_MD_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read memory.md: {e}")
        return

    current_section = None
    category_map = {
        "user preferences": "preference",
        "corrections & learnings": "correction",
        "ticker preferences": "ticker_context",
        "cost preferences": "preference",
    }

    for line in content.split("\n"):
        line = line.strip()

        # Detect section headers
        if line.startswith("## "):
            header = line[3:].strip().lower()
            current_section = category_map.get(header)
            continue

        # Parse bullet points
        if current_section and line.startswith("- ") and ":" in line:
            entry = line[2:].strip()
            # Split on first colon for key: value pairs
            parts = entry.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip().lower().replace(" ", "_")
                value = parts[1].strip()
                add_memory(
                    category=current_section,
                    key=f"manual_{key}",
                    value=value,
                    user_id=user_id,
                    source="explicit",
                    confidence=1.0,
                )

    logger.info("Synced memory.md entries to structured store")


def _extract_section(filepath: Path, section_name: str) -> List[str]:
    """Extract lines from a specific ## section of a markdown file."""
    if not filepath.exists():
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    result = []
    in_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if section_name.lower() in stripped.lower():
                in_section = True
                continue
            elif in_section:
                break  # Hit next section
        elif in_section and stripped:
            result.append(stripped)

    return result
