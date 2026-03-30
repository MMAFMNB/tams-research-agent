"""Compare two reports and produce structured diffs with severity categorization."""

import re
import difflib
from typing import Optional

# Change severity thresholds (absolute percentage change)
SEVERITY_MINOR = 5       # < 5%
SEVERITY_MODERATE = 15   # 5-15%
# > 15% = major; rating/outlook changes = critical

# Rating keywords for critical-change detection
RATING_KEYWORDS = [
    "strong buy", "buy", "overweight", "outperform",
    "hold", "neutral", "equal weight", "market perform",
    "underweight", "underperform", "sell", "strong sell",
    "reduce",
]

OUTLOOK_KEYWORDS = ["positive", "negative", "neutral", "stable", "improving", "deteriorating"]


# Financial metrics we attempt to extract from section text
METRIC_PATTERNS = {
    "Revenue": r'[Rr]evenue[:\s]*(?:SAR\s*)?([0-9,.]+)\s*[BbMm]?',
    "Net Income": r'[Nn]et\s+[Ii]ncome[:\s]*(?:SAR\s*)?([0-9,.]+)\s*[BbMm]?',
    "EPS": r'EPS[:\s]*(?:SAR\s*)?([0-9,.]+)',
    "P/E Ratio": r'P/?E\s*(?:[Rr]atio)?[:\s]*([0-9,.]+)x?',
    "Dividend Yield": r'[Dd]ividend\s+[Yy]ield[:\s]*([0-9,.]+)\s*%?',
    "Debt/Equity": r'[Dd]ebt[/\s]?[Ee]quity[:\s]*([0-9,.]+)',
    "Market Cap": r'[Mm]arket\s+[Cc]ap[:\s]*(?:SAR\s*)?([0-9,.]+)\s*[BTbtrn]*',
    "ROE": r'ROE[:\s]*([0-9,.]+)\s*%?',
    "EV/EBITDA": r'EV/EBITDA[:\s]*([0-9,.]+)x?',
    "Price Target": r'[Pp]rice\s+[Tt]arget[:\s]*(?:SAR\s*)?([0-9,.]+)',
}

from templates.report_structure import SECTION_TITLES


def _parse_number(s: str) -> Optional[float]:
    """Parse a number string, stripping commas."""
    try:
        return float(s.replace(",", ""))
    except (ValueError, TypeError):
        return None


def extract_metrics(sections: dict) -> dict:
    """Extract financial metrics from all section texts."""
    full_text = "\n".join(sections.values())
    metrics = {}
    for name, pattern in METRIC_PATTERNS.items():
        m = re.search(pattern, full_text)
        if m:
            val = _parse_number(m.group(1))
            if val is not None:
                metrics[name] = val
    return metrics


def compare_metrics(old_sections: dict, new_sections: dict) -> list:
    """Compare financial metrics between two reports.

    Returns list of dicts: {metric, old, new, change, change_pct, direction}
    """
    old_metrics = extract_metrics(old_sections)
    new_metrics = extract_metrics(new_sections)

    all_keys = sorted(set(old_metrics) | set(new_metrics))
    results = []

    for key in all_keys:
        old_val = old_metrics.get(key)
        new_val = new_metrics.get(key)

        if old_val is None and new_val is None:
            continue

        change = None
        change_pct = None
        direction = "unchanged"

        if old_val is not None and new_val is not None:
            change = new_val - old_val
            if old_val != 0:
                change_pct = (change / abs(old_val)) * 100
            direction = "up" if change > 0 else ("down" if change < 0 else "unchanged")
        elif old_val is None:
            direction = "new"
        else:
            direction = "removed"

        severity = categorize_change(change_pct)

        results.append({
            "metric": key,
            "old": old_val,
            "new": new_val,
            "change": change,
            "change_pct": change_pct,
            "direction": direction,
            "severity": severity,
        })

    return results


def categorize_change(change_pct: Optional[float]) -> str:
    """Categorize a percentage change into minor/moderate/major."""
    if change_pct is None:
        return "unknown"
    abs_pct = abs(change_pct)
    if abs_pct < SEVERITY_MINOR:
        return "minor"
    if abs_pct < SEVERITY_MODERATE:
        return "moderate"
    return "major"


def compare_text_sections(old_sections: dict, new_sections: dict) -> dict:
    """Compare text of each section, producing a unified diff.

    Returns dict of section_key -> list of diff lines.
    Each line is a tuple (type, text) where type is 'added', 'removed', or 'context'.
    """
    all_keys = sorted(set(old_sections) | set(new_sections))
    diffs = {}

    for key in all_keys:
        old_text = old_sections.get(key, "").strip().split("\n")
        new_text = new_sections.get(key, "").strip().split("\n")

        diff_lines = list(difflib.unified_diff(old_text, new_text, lineterm=""))

        parsed = []
        for line in diff_lines:
            if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
                continue
            if line.startswith("+"):
                parsed.append(("added", line[1:]))
            elif line.startswith("-"):
                parsed.append(("removed", line[1:]))
            else:
                parsed.append(("context", line))

        if parsed:
            diffs[key] = parsed

    return diffs


def build_comparison_summary(metric_changes: list, text_diffs: dict) -> dict:
    """Build a high-level summary of the comparison.

    Returns dict with total_metric_changes, largest_change, sections_changed, etc.
    """
    metrics_up = sum(1 for m in metric_changes if m["direction"] == "up")
    metrics_down = sum(1 for m in metric_changes if m["direction"] == "down")

    largest = None
    largest_pct = 0
    for m in metric_changes:
        if m["change_pct"] is not None and abs(m["change_pct"]) > abs(largest_pct):
            largest_pct = m["change_pct"]
            largest = m

    sections_changed = len(text_diffs)
    total_added = sum(
        sum(1 for typ, _ in lines if typ == "added")
        for lines in text_diffs.values()
    )
    total_removed = sum(
        sum(1 for typ, _ in lines if typ == "removed")
        for lines in text_diffs.values()
    )

    # Severity breakdown
    severity_counts = {"minor": 0, "moderate": 0, "major": 0}
    for m in metric_changes:
        sev = m.get("severity", "unknown")
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Change score (0-100): weighted sum of changes
    change_score = _calculate_change_score(metric_changes, text_diffs)

    return {
        "metrics_improved": metrics_up,
        "metrics_deteriorated": metrics_down,
        "largest_change": largest,
        "sections_changed": sections_changed,
        "lines_added": total_added,
        "lines_removed": total_removed,
        "severity_counts": severity_counts,
        "change_score": change_score,
    }


def _calculate_change_score(metric_changes: list, text_diffs: dict) -> int:
    """Calculate overall change score (0-100).

    0 = identical reports, 100 = completely different.
    """
    score = 0.0

    # Metric changes contribute up to 60 points
    for m in metric_changes:
        pct = abs(m.get("change_pct") or 0)
        if pct > 0:
            score += min(pct, 50) * 0.6  # Cap individual metric contribution

    if metric_changes:
        score = min(score, 60)

    # Text changes contribute up to 40 points
    total_diff_lines = sum(
        sum(1 for typ, _ in lines if typ in ("added", "removed"))
        for lines in text_diffs.values()
    )
    score += min(total_diff_lines * 0.5, 40)

    return min(int(score), 100)


def detect_rating_change(old_sections: dict, new_sections: dict) -> Optional[dict]:
    """Detect if the investment rating/recommendation changed between versions.

    Returns dict with old_rating, new_rating, is_upgrade, or None if no change detected.
    """
    old_rating = _find_rating(old_sections)
    new_rating = _find_rating(new_sections)

    if old_rating is None or new_rating is None:
        return None
    if old_rating == new_rating:
        return None

    old_idx = _rating_rank(old_rating)
    new_idx = _rating_rank(new_rating)

    return {
        "old_rating": old_rating,
        "new_rating": new_rating,
        "is_upgrade": new_idx < old_idx,  # Lower index = more bullish
        "severity": "critical",
    }


def _find_rating(sections: dict) -> Optional[str]:
    """Search sections for a recognizable rating keyword."""
    # Prioritize executive_summary and key_takeaways
    priority_keys = ["executive_summary", "key_takeaways"]
    search_order = priority_keys + [k for k in sections if k not in priority_keys]

    for key in search_order:
        text = sections.get(key, "").lower()
        for kw in RATING_KEYWORDS:
            if kw in text:
                return kw
    return None


def _rating_rank(rating: str) -> int:
    """Return rank of a rating (lower = more bullish)."""
    try:
        return RATING_KEYWORDS.index(rating)
    except ValueError:
        return len(RATING_KEYWORDS)


def detect_outlook_change(old_sections: dict, new_sections: dict) -> Optional[dict]:
    """Detect if the outlook sentiment changed."""
    old_outlook = _find_outlook(old_sections)
    new_outlook = _find_outlook(new_sections)

    if old_outlook is None or new_outlook is None:
        return None
    if old_outlook == new_outlook:
        return None

    return {
        "old_outlook": old_outlook,
        "new_outlook": new_outlook,
        "severity": "critical",
    }


def _find_outlook(sections: dict) -> Optional[str]:
    """Search for outlook keywords."""
    for key in ["executive_summary", "key_takeaways", "risk_assessment"]:
        text = sections.get(key, "").lower()
        for kw in OUTLOOK_KEYWORDS:
            pattern = rf'outlook[:\s].*?\b{kw}\b'
            if re.search(pattern, text):
                return kw
    return None
