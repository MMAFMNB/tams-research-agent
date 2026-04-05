"""
Prompt Learner — ML system that learns from analyst interactions to improve prompts.

Tracks:
- Which prompt variations produce better analyst ratings
- What corrections analysts make to AI output
- Patterns in successful vs rejected analyses
- Prompt-response quality metrics over time

Uses this data to:
- Generate "learned additions" that get appended to base prompts
- Recommend prompt adjustments based on historical performance
- Track quality trends per section type
- Auto-tune temperature/model selection per task

This is NOT a fine-tuning system — it works by building a structured knowledge base
of what works and injecting it as context into future prompts.
"""

import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LEARNINGS_FILE = Path(__file__).parent / "prompt_learnings.json"


def _load_learnings() -> Dict:
    """Load the prompt learnings database."""
    if LEARNINGS_FILE.exists():
        try:
            with open(LEARNINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "interactions": [],      # Raw interaction log
        "section_scores": {},    # section_type -> list of scores
        "learned_rules": [],     # Extracted rules from corrections
        "prompt_additions": {},  # section_type -> list of learned additions
        "model_performance": {}, # model -> { section_type -> avg_score }
    }


def _save_learnings(data: Dict):
    """Save the prompt learnings database."""
    LEARNINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARNINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ===== Recording Interactions =====

def record_interaction(
    section_type: str,
    ticker: str,
    prompt_length: int,
    response_length: int,
    model_used: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    user_id: str = "default",
):
    """
    Record a prompt-response interaction for future learning.

    Called automatically after each generate_section() call.
    """
    db = _load_learnings()

    interaction = {
        "section_type": section_type,
        "ticker": ticker,
        "model": model_used,
        "prompt_chars": prompt_length,
        "response_chars": response_length,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "score": None,           # Filled in by record_score()
        "corrections": [],       # Filled in by record_correction()
    }

    db["interactions"].append(interaction)

    # Keep last 1000 interactions
    if len(db["interactions"]) > 1000:
        db["interactions"] = db["interactions"][-1000:]

    _save_learnings(db)


def record_score(
    section_type: str,
    ticker: str,
    score: float,
    user_id: str = "default",
):
    """
    Record an analyst's quality score for a generated section.

    Args:
        score: 1.0-5.0 (1=poor, 3=acceptable, 5=excellent)
    """
    db = _load_learnings()

    # Update the most recent matching interaction
    for interaction in reversed(db["interactions"]):
        if (interaction["section_type"] == section_type
                and interaction["ticker"] == ticker
                and interaction["score"] is None):
            interaction["score"] = score
            break

    # Update section scores
    if section_type not in db["section_scores"]:
        db["section_scores"][section_type] = []
    db["section_scores"][section_type].append({
        "score": score,
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
    })
    # Keep last 100 scores per section
    db["section_scores"][section_type] = db["section_scores"][section_type][-100:]

    # Update model performance
    for interaction in reversed(db["interactions"]):
        if interaction["section_type"] == section_type and interaction.get("score") == score:
            model = interaction["model"]
            if model not in db["model_performance"]:
                db["model_performance"][model] = {}
            if section_type not in db["model_performance"][model]:
                db["model_performance"][model][section_type] = []
            db["model_performance"][model][section_type].append(score)
            db["model_performance"][model][section_type] = db["model_performance"][model][section_type][-50:]
            break

    _save_learnings(db)
    logger.info(f"Recorded score {score}/5 for {section_type} on {ticker}")

    # Trigger rule extraction if we have enough data
    if len(db["section_scores"].get(section_type, [])) % 10 == 0:
        _extract_rules(db, section_type)
        _save_learnings(db)


def record_correction(
    section_type: str,
    ticker: str,
    original_text: str,
    corrected_text: str,
    correction_type: str = "content",
    user_id: str = "default",
):
    """
    Record when an analyst corrects AI output.

    correction_type: "content" (factual), "format" (structure), "tone" (language),
                     "missing" (added info), "excess" (removed info)
    """
    db = _load_learnings()

    correction = {
        "section_type": section_type,
        "ticker": ticker,
        "correction_type": correction_type,
        "original_snippet": original_text[:500],
        "corrected_snippet": corrected_text[:500],
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
    }

    # Attach to most recent matching interaction
    for interaction in reversed(db["interactions"]):
        if interaction["section_type"] == section_type and interaction["ticker"] == ticker:
            interaction["corrections"].append(correction)
            break

    # Extract a rule from this correction
    rule = _correction_to_rule(correction)
    if rule:
        db["learned_rules"].append(rule)
        # Deduplicate rules
        db["learned_rules"] = _deduplicate_rules(db["learned_rules"])
        logger.info(f"Extracted rule from correction: {rule['rule'][:100]}")

    _save_learnings(db)


# ===== Learning & Rule Extraction =====

def _correction_to_rule(correction: Dict) -> Optional[Dict]:
    """
    Convert a correction into a learned rule.

    The rule is a natural language instruction that can be injected into future prompts.
    """
    section = correction["section_type"]
    ctype = correction["correction_type"]
    original = correction["original_snippet"]
    corrected = correction["corrected_snippet"]

    if not original or not corrected:
        return None

    # Build the rule based on correction type
    if ctype == "content":
        rule = f"For {section}: the analyst corrected factual content. Prefer: '{corrected[:200]}' over '{original[:200]}'"
    elif ctype == "format":
        rule = f"For {section}: use the formatting style shown in the corrected version"
    elif ctype == "tone":
        rule = f"For {section}: adjust tone — the analyst preferred a different writing style"
    elif ctype == "missing":
        rule = f"For {section}: include this information that was missing: '{corrected[:300]}'"
    elif ctype == "excess":
        rule = f"For {section}: remove unnecessary content. The analyst stripped: '{original[:200]}'"
    else:
        rule = f"For {section}: analyst correction applied"

    return {
        "rule": rule,
        "section_type": section,
        "correction_type": ctype,
        "confidence": 0.7,  # Single correction starts at 0.7
        "occurrences": 1,
        "created_at": datetime.now().isoformat(),
    }


def _extract_rules(db: Dict, section_type: str):
    """
    Analyze scored interactions to extract performance patterns.

    Called periodically (every 10 scores for a section type).
    """
    scores = db["section_scores"].get(section_type, [])
    if len(scores) < 5:
        return

    # Calculate trend
    recent = [s["score"] for s in scores[-10:]]
    older = [s["score"] for s in scores[-20:-10]] if len(scores) >= 20 else []

    avg_recent = sum(recent) / len(recent)
    avg_older = sum(older) / len(older) if older else avg_recent

    # If quality is declining, add a "be more careful" rule
    if avg_recent < avg_older - 0.5:
        rule = {
            "rule": f"For {section_type}: quality has been declining (avg {avg_recent:.1f}/5). "
                    f"Pay extra attention to accuracy and detail.",
            "section_type": section_type,
            "correction_type": "quality_trend",
            "confidence": 0.6,
            "occurrences": 1,
            "created_at": datetime.now().isoformat(),
        }
        db["learned_rules"].append(rule)

    # If certain tickers consistently score lower, note it
    ticker_scores = defaultdict(list)
    for s in scores:
        ticker_scores[s["ticker"]].append(s["score"])

    for ticker, t_scores in ticker_scores.items():
        if len(t_scores) >= 3:
            avg = sum(t_scores) / len(t_scores)
            if avg < 3.0:
                rule = {
                    "rule": f"For {section_type} on {ticker}: this stock's analysis scores below average "
                            f"({avg:.1f}/5). Give extra attention to data accuracy for this ticker.",
                    "section_type": section_type,
                    "correction_type": "ticker_quality",
                    "confidence": 0.8,
                    "occurrences": len(t_scores),
                    "created_at": datetime.now().isoformat(),
                }
                db["learned_rules"].append(rule)

    db["learned_rules"] = _deduplicate_rules(db["learned_rules"])


def _deduplicate_rules(rules: List[Dict]) -> List[Dict]:
    """
    Deduplicate rules by merging similar ones.

    If the same section_type + correction_type appears multiple times,
    keep the most recent and boost confidence.
    """
    seen = {}
    for rule in rules:
        key = f"{rule['section_type']}_{rule['correction_type']}"
        if key in seen:
            # Merge: increase confidence and occurrence count
            existing = seen[key]
            existing["confidence"] = min(1.0, existing["confidence"] + 0.1)
            existing["occurrences"] += 1
            # Keep the more recent rule text
            if rule["created_at"] > existing["created_at"]:
                existing["rule"] = rule["rule"]
                existing["created_at"] = rule["created_at"]
        else:
            seen[key] = rule.copy()

    return list(seen.values())


# ===== Generating Prompt Additions =====

def get_learned_additions(section_type: str, ticker: str = "") -> str:
    """
    Get learned prompt additions for a given section type.

    Returns a string to be appended to the base prompt, containing
    rules and insights learned from analyst interactions.
    """
    db = _load_learnings()

    additions = []

    # Get relevant rules
    for rule in db.get("learned_rules", []):
        if rule["section_type"] == section_type and rule["confidence"] >= 0.5:
            additions.append(f"- {rule['rule']}")
        # Also include rules mentioning this specific ticker
        elif ticker and ticker in rule.get("rule", ""):
            additions.append(f"- {rule['rule']}")

    if not additions:
        return ""

    header = "\n\nIMPORTANT - LEARNED FROM ANALYST FEEDBACK:"
    return header + "\n" + "\n".join(additions[:10])  # Max 10 rules per prompt


def get_recommended_model(section_type: str) -> Optional[str]:
    """
    Recommend the best-performing model for a section type based on historical scores.

    Returns model ID string, or None if insufficient data.
    """
    db = _load_learnings()
    model_perf = db.get("model_performance", {})

    best_model = None
    best_avg = 0.0

    for model, sections in model_perf.items():
        scores = sections.get(section_type, [])
        if len(scores) >= 5:  # Need at least 5 data points
            avg = sum(scores) / len(scores)
            if avg > best_avg:
                best_avg = avg
                best_model = model

    if best_model and best_avg > 3.5:
        logger.info(f"Recommending {best_model} for {section_type} (avg score: {best_avg:.1f})")
        return best_model

    return None


# ===== Analytics =====

def get_quality_report() -> Dict:
    """
    Generate a quality report across all section types.

    Returns metrics for display in the admin dashboard.
    """
    db = _load_learnings()

    report = {
        "total_interactions": len(db.get("interactions", [])),
        "total_scored": sum(1 for i in db.get("interactions", []) if i.get("score") is not None),
        "total_corrections": sum(len(i.get("corrections", [])) for i in db.get("interactions", [])),
        "total_rules": len(db.get("learned_rules", [])),
        "sections": {},
    }

    for section_type, scores in db.get("section_scores", {}).items():
        if not scores:
            continue

        score_vals = [s["score"] for s in scores]
        recent_vals = [s["score"] for s in scores[-10:]]

        report["sections"][section_type] = {
            "total_scores": len(score_vals),
            "avg_score": round(sum(score_vals) / len(score_vals), 2),
            "recent_avg": round(sum(recent_vals) / len(recent_vals), 2),
            "trend": "improving" if len(scores) >= 20 and sum(recent_vals) / len(recent_vals) > sum(score_vals[:10]) / max(len(score_vals[:10]), 1) else "stable",
            "min_score": min(score_vals),
            "max_score": max(score_vals),
        }

    # Model comparison
    report["model_comparison"] = {}
    for model, sections in db.get("model_performance", {}).items():
        all_scores = []
        for s_scores in sections.values():
            all_scores.extend(s_scores)
        if all_scores:
            report["model_comparison"][model] = {
                "avg_score": round(sum(all_scores) / len(all_scores), 2),
                "total_scored": len(all_scores),
            }

    return report


def get_improvement_suggestions() -> List[str]:
    """
    Generate actionable suggestions for improving prompt quality.

    Based on patterns in the data.
    """
    db = _load_learnings()
    suggestions = []

    # Check for sections with low scores
    for section_type, scores in db.get("section_scores", {}).items():
        if not scores:
            continue
        recent = [s["score"] for s in scores[-10:]]
        avg = sum(recent) / len(recent)
        if avg < 3.0:
            suggestions.append(
                f"{section_type}: Average score {avg:.1f}/5 — review prompt template and recent corrections"
            )

    # Check for sections with many corrections
    correction_counts = defaultdict(int)
    for interaction in db.get("interactions", []):
        if interaction.get("corrections"):
            correction_counts[interaction["section_type"]] += len(interaction["corrections"])

    for section, count in sorted(correction_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
        if count >= 5:
            suggestions.append(
                f"{section}: {count} corrections recorded — consider updating the base prompt template"
            )

    # Check model performance differences
    model_perf = db.get("model_performance", {})
    for section_type in db.get("section_scores", {}):
        model_avgs = {}
        for model, sections in model_perf.items():
            scores = sections.get(section_type, [])
            if len(scores) >= 3:
                model_avgs[model] = sum(scores) / len(scores)

        if len(model_avgs) >= 2:
            best = max(model_avgs.items(), key=lambda x: x[1])
            worst = min(model_avgs.items(), key=lambda x: x[1])
            if best[1] - worst[1] > 0.5:
                suggestions.append(
                    f"{section_type}: {best[0]} scores {best[1]:.1f} vs {worst[0]} at {worst[1]:.1f} — "
                    f"consider routing to {best[0]}"
                )

    return suggestions if suggestions else ["No improvement suggestions yet — need more scored interactions"]
