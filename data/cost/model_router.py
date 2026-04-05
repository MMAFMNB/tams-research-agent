"""
Intelligent model selection based on task type, prompt size, and budget.

Routes each analysis action to the cheapest model that can produce acceptable quality.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Task-to-model-tier mapping
# "haiku" = cheap + fast, "sonnet" = expensive + strong reasoning
TASK_ROUTES = {
    # Light tasks — Haiku is sufficient
    "morning_brief": "haiku",
    "news_summarize": "haiku",
    "sentiment_classify": "haiku",
    "news_impact": "haiku",
    # Deep analysis — needs Sonnet
    "fundamental": "sonnet",
    "technical": "sonnet",
    "earnings": "sonnet",
    "dividend": "sonnet",
    "risk": "sonnet",
    "sector": "sonnet",
    "war_impact": "sonnet",
    "executive_summary": "sonnet",
    # Default for unknown actions
    "research": "sonnet",
}

MODEL_IDS = {
    "haiku": "claude-haiku-3-5-20241022",
    "sonnet": "claude-sonnet-4-20250514",
}


def select_model(
    action: str,
    prompt_length: int = 0,
    budget_remaining: float = 999.0,
    force_tier: Optional[str] = None,
) -> str:
    """
    Select the optimal model for a given task.

    Args:
        action: The analysis type (e.g., "fundamental", "morning_brief")
        prompt_length: Length of prompt in characters
        budget_remaining: Remaining monthly budget in USD
        force_tier: Override to force "haiku" or "sonnet"

    Returns:
        Model ID string (e.g., "claude-sonnet-4-20250514")
    """
    if force_tier and force_tier in MODEL_IDS:
        return MODEL_IDS[force_tier]

    tier = TASK_ROUTES.get(action, "sonnet")

    # Budget override: if less than $5 remaining, downgrade everything to Haiku
    if budget_remaining < 5.0:
        logger.info(f"Budget low (${budget_remaining:.2f}), downgrading {action} to haiku")
        tier = "haiku"
    # If less than $10, downgrade haiku-eligible tasks only (already haiku), keep sonnet for deep analysis
    elif budget_remaining < 10.0 and tier == "sonnet":
        logger.info(f"Budget moderate (${budget_remaining:.2f}), keeping {action} on sonnet")

    # Prompt length override: huge prompts on Sonnet get expensive fast
    if prompt_length > 50000 and tier == "sonnet" and budget_remaining < 20.0:
        logger.info(f"Large prompt ({prompt_length} chars) + low budget, downgrading to haiku")
        tier = "haiku"

    model = MODEL_IDS.get(tier, MODEL_IDS["sonnet"])
    logger.debug(f"ModelRouter: {action} -> {tier} -> {model}")
    return model


def get_tier_for_action(action: str) -> str:
    """Get the default tier name for an action (for display purposes)."""
    return TASK_ROUTES.get(action, "sonnet")
