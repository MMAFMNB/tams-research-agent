"""
Budget management — tracks spend against monthly limits and enforces constraints.

Uses the existing token_tracker.py for actual spend data.
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

DEFAULT_MONTHLY_BUDGET_USD = 50.0

# Approximate costs per analysis action (for pre-flight estimation)
# Based on typical prompt sizes and model routing
ESTIMATED_COSTS = {
    "fundamental": 0.08,
    "technical": 0.06,
    "earnings": 0.06,
    "dividend": 0.05,
    "risk": 0.06,
    "sector": 0.05,
    "news_impact": 0.01,
    "war_impact": 0.05,
    "executive_summary": 0.06,
    "morning_brief": 0.01,
    "sentiment_classify": 0.005,
    "news_summarize": 0.005,
    "research": 0.10,
}


class BudgetManager:
    """Tracks API spend against monthly budget."""

    def __init__(self, monthly_budget_usd: float = DEFAULT_MONTHLY_BUDGET_USD):
        self.monthly_budget = monthly_budget_usd

    def get_remaining_budget(self) -> float:
        """Calculate remaining budget for the current month."""
        try:
            from data.token_tracker import get_token_summary
            summary = get_token_summary(days=30)
            spent = summary.get("total_cost_usd", 0.0)
            return max(0.0, self.monthly_budget - spent)
        except Exception as e:
            logger.warning(f"Could not fetch spend data: {e}")
            return self.monthly_budget  # Assume full budget if tracking fails

    def get_spend_this_month(self) -> float:
        """Get total spend for the current month."""
        return self.monthly_budget - self.get_remaining_budget()

    def can_proceed(self, action: str = "research") -> Tuple[bool, str]:
        """
        Check if an operation should proceed given budget constraints.

        Returns:
            (can_proceed: bool, message: str)
        """
        remaining = self.get_remaining_budget()
        estimated = ESTIMATED_COSTS.get(action, 0.05)

        if remaining <= 0:
            return False, f"Monthly budget exhausted (${self.monthly_budget:.2f} spent)"

        if estimated > remaining:
            return False, (
                f"Estimated cost ${estimated:.3f} exceeds remaining budget "
                f"${remaining:.2f}. Use lighter analysis or increase budget."
            )

        if remaining < 5.0:
            return True, f"Warning: only ${remaining:.2f} remaining this month"

        if remaining < 10.0:
            return True, f"Budget note: ${remaining:.2f} remaining (auto-routing to cheaper models)"

        return True, "OK"

    def estimate_full_analysis_cost(self) -> float:
        """Estimate the cost of a full 8-section analysis + executive summary."""
        sections = [
            "fundamental", "technical", "earnings", "dividend",
            "risk", "sector", "news_impact", "war_impact",
            "executive_summary",
        ]
        return sum(ESTIMATED_COSTS.get(s, 0.05) for s in sections)

    def get_budget_display(self) -> dict:
        """Get budget info formatted for sidebar display."""
        remaining = self.get_remaining_budget()
        spent = self.get_spend_this_month()
        pct_used = (spent / self.monthly_budget * 100) if self.monthly_budget > 0 else 0

        return {
            "monthly_budget": self.monthly_budget,
            "spent": round(spent, 2),
            "remaining": round(remaining, 2),
            "pct_used": round(pct_used, 1),
            "status": (
                "critical" if remaining < 5.0
                else "warning" if remaining < 10.0
                else "ok"
            ),
        }
