"""JSON-based report history store with version tracking per ticker."""

import json
import os
import re
from datetime import datetime
from typing import Optional

from data.report_comparator import compare_metrics, compare_text_sections


REPORT_HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "report_history")
VERSION_INDEX_FILE = "_versions.json"


def _ensure_dir():
    os.makedirs(REPORT_HISTORY_DIR, exist_ok=True)


def _safe_ticker(ticker: str) -> str:
    return re.sub(r'[^\w]', '_', ticker)


def _load_version_index(ticker: str) -> dict:
    """Load (or initialize) the version index for a ticker."""
    _ensure_dir()
    safe = _safe_ticker(ticker)
    path = os.path.join(REPORT_HISTORY_DIR, f"{safe}{VERSION_INDEX_FILE}")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"ticker": ticker, "next_version": 1, "versions": []}


def _save_version_index(ticker: str, index: dict):
    safe = _safe_ticker(ticker)
    path = os.path.join(REPORT_HISTORY_DIR, f"{safe}{VERSION_INDEX_FILE}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _generate_change_summary(old_sections: dict, new_sections: dict) -> str:
    """Auto-generate a short change summary comparing two versions."""
    metrics = compare_metrics(old_sections, new_sections)
    text_diffs = compare_text_sections(old_sections, new_sections)

    parts = []

    improved = [m for m in metrics if m["direction"] == "up"]
    declined = [m for m in metrics if m["direction"] == "down"]
    if improved:
        names = ", ".join(m["metric"] for m in improved[:3])
        parts.append(f"Improved: {names}")
    if declined:
        names = ", ".join(m["metric"] for m in declined[:3])
        parts.append(f"Declined: {names}")

    added_sections = [k for k in new_sections if k not in old_sections]
    removed_sections = [k for k in old_sections if k not in new_sections]
    if added_sections:
        parts.append(f"Added sections: {', '.join(added_sections)}")
    if removed_sections:
        parts.append(f"Removed sections: {', '.join(removed_sections)}")

    if text_diffs:
        changed_count = len(text_diffs) - len(added_sections) - len(removed_sections)
        if changed_count > 0:
            parts.append(f"{changed_count} section(s) updated")

    return "; ".join(parts) if parts else "No significant changes"


def save_report(stock_name: str, ticker: str, sections: dict,
                files: dict = None) -> str:
    """Save a report to the history store with automatic versioning.

    Returns:
        The report ID (filename without extension).
    """
    _ensure_dir()

    # Load version index for this ticker
    index = _load_version_index(ticker)
    version = index["next_version"]

    timestamp = datetime.now()
    safe = _safe_ticker(ticker)
    report_id = f"{safe}_v{version}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

    # Generate change summary if there's a previous version
    change_summary = ""
    if index["versions"]:
        prev_id = index["versions"][-1]["id"]
        prev_report = load_report(prev_id)
        if prev_report and prev_report.get("sections"):
            change_summary = _generate_change_summary(prev_report["sections"], sections)

    record = {
        "id": report_id,
        "stock_name": stock_name,
        "ticker": ticker,
        "version": version,
        "date": timestamp.isoformat(),
        "date_display": timestamp.strftime("%B %d, %Y %H:%M"),
        "change_summary": change_summary,
        "sections": sections,
        "files": files or {},
    }

    filepath = os.path.join(REPORT_HISTORY_DIR, f"{report_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    # Update version index
    index["versions"].append({
        "id": report_id,
        "version": version,
        "date": timestamp.isoformat(),
        "date_display": timestamp.strftime("%B %d, %Y %H:%M"),
        "change_summary": change_summary,
    })
    index["next_version"] = version + 1
    _save_version_index(ticker, index)

    return report_id


def load_report(report_id: str) -> Optional[dict]:
    """Load a report by ID."""
    filepath = os.path.join(REPORT_HISTORY_DIR, f"{report_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_reports(ticker: str = None) -> list:
    """List all saved reports, optionally filtered by ticker.

    Returns list of dicts sorted newest first.
    """
    _ensure_dir()
    reports = []

    for fname in os.listdir(REPORT_HISTORY_DIR):
        if not fname.endswith(".json") or fname.endswith(VERSION_INDEX_FILE):
            continue
        filepath = os.path.join(REPORT_HISTORY_DIR, fname)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            entry = {
                "id": data["id"],
                "stock_name": data["stock_name"],
                "ticker": data["ticker"],
                "version": data.get("version"),
                "date": data["date"],
                "date_display": data.get("date_display", data["date"][:10]),
                "change_summary": data.get("change_summary", ""),
            }
            if ticker and data["ticker"] != ticker:
                continue
            reports.append(entry)
        except (json.JSONDecodeError, KeyError):
            continue

    reports.sort(key=lambda r: r["date"], reverse=True)
    return reports


def get_versions(ticker: str) -> list:
    """Get all versions for a specific ticker, sorted newest first.

    Returns list of version metadata dicts from the index.
    """
    index = _load_version_index(ticker)
    versions = list(index.get("versions", []))
    versions.reverse()
    return versions


def delete_report(report_id: str) -> bool:
    """Delete a report from the store."""
    filepath = os.path.join(REPORT_HISTORY_DIR, f"{report_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False
