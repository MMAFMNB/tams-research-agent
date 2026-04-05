"""
Analyst Agent — consumes data from all 4 data agents and produces structured analysis.

Runs all 8 specialist analysis types using existing prompts/ templates:
1. Fundamental Analysis (Goldman Sachs style)
2. Dividend Income Analysis
3. Earnings Analysis (JPMorgan style)
4. Risk Assessment Framework
5. Technical Analysis (Morgan Stanley style)
6. Sector Rotation Strategy
7. News Impact Assessment
8. Geopolitical/War Impact Assessment

Integrates with existing generate_section() and SECTION_CONFIG from app.py.
"""

import importlib
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from data.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Section types in analysis order
ANALYSIS_SECTIONS = [
    "fundamental", "dividend", "earnings", "risk",
    "technical", "sector", "news_impact", "war_impact",
]


class AnalystAgent(BaseAgent):
    """Runs multi-section analysis using existing prompt templates."""

    name = "analyst"
    cache_ttl = 43200            # 12 hours for analysis
    rate_limit = 0.0             # No external rate limit (uses Claude API)
    max_retries = 1              # Analysis is expensive — don't retry
    required_fields = ["ticker", "sections"]

    def __init__(self):
        super().__init__()
        self._generate_fn: Optional[Callable] = None
        self._format_fn: Optional[Callable] = None

    async def fetch(self, ticker: str, **kwargs) -> Optional[Dict]:
        """
        Run full analysis pipeline on a stock.

        Args:
            ticker: Tadawul ticker
            kwargs:
                agent_data: Dict from orchestrator.run_data_agents()
                market_data_str: Pre-formatted market data string
                news_str: Pre-formatted news string
                sections: List of section types to run (default: all 8)
                cancel_check: Callable that returns True if analysis should stop

        Returns:
            Dict with analysis sections, or None on failure.
        """
        agent_data = kwargs.get("agent_data", {})
        market_data_str = kwargs.get("market_data_str", "")
        news_str = kwargs.get("news_str", "")
        sections_to_run = kwargs.get("sections", ANALYSIS_SECTIONS)
        cancel_check = kwargs.get("cancel_check")

        # If no pre-formatted strings, try to build from agent data
        if not market_data_str and agent_data:
            market_data_str = self._format_agent_data(agent_data)

        if not news_str and agent_data:
            news_str = self._format_news_data(agent_data)

        if not market_data_str:
            logger.warning(f"[analyst] No market data available for {ticker}")
            return None

        # Run each analysis section
        sections = {}
        for section_type in sections_to_run:
            if cancel_check and cancel_check():
                logger.info(f"[analyst] Analysis cancelled at section {section_type}")
                break

            try:
                result = self._run_section(section_type, market_data_str, news_str, ticker)
                if result:
                    sections[self._get_section_key(section_type)] = result
                    logger.info(f"[analyst] Completed section: {section_type}")
            except Exception as e:
                logger.error(f"[analyst] Section {section_type} failed: {e}")

        if not sections:
            return None

        return {
            "ticker": ticker,
            "sections": sections,
            "sections_completed": list(sections.keys()),
            "sections_requested": sections_to_run,
            "timestamp": datetime.now().isoformat(),
        }

    def _run_section(self, section_type: str, market_data_str: str, news_str: str, ticker: str) -> Optional[str]:
        """
        Run a single analysis section using the existing prompt system.

        Uses generate_section() from app.py if available, otherwise calls Claude directly.
        """
        # Try using the app's generate_section (which includes cost optimization + ML learning)
        if self._generate_fn:
            return self._generate_fn(section_type, market_data_str, news_str, ticker)

        # Fallback: call Claude directly using prompt templates
        try:
            from templates.report_structure import SECTION_CONFIG
        except ImportError:
            logger.error("[analyst] Cannot import SECTION_CONFIG")
            return None

        config = SECTION_CONFIG.get(section_type)
        if not config:
            logger.warning(f"[analyst] No config for section type: {section_type}")
            return None

        try:
            module = importlib.import_module(config["prompt_module"])
            prompt_template = getattr(module, config["prompt_var"])
            prompt = prompt_template.format(market_data=market_data_str, news_data=news_str)
        except Exception as e:
            logger.error(f"[analyst] Prompt template error for {section_type}: {e}")
            return None

        # Apply prompt optimization
        try:
            from data.cost.prompt_optimizer import truncate_market_data, deduplicate_news
            prompt_data = truncate_market_data(market_data_str, section_type)
            prompt_news = deduplicate_news(news_str)
            prompt = prompt_template.format(market_data=prompt_data, news_data=prompt_news)
        except ImportError:
            pass

        # Apply learned additions from ML system
        try:
            from data.memory.prompt_learner import get_learned_additions
            learned = get_learned_additions(section_type, ticker)
            if learned:
                prompt += learned
        except ImportError:
            pass

        # Call Claude
        try:
            from data.cost.model_router import select_model
            from data.cost.budget_manager import BudgetManager
            budget = BudgetManager()
            remaining = budget.get_remaining_budget()
            model = select_model(section_type, len(prompt), remaining)
        except ImportError:
            model = "claude-sonnet-4-20250514"

        try:
            import anthropic
            from config import ANTHROPIC_API_KEY
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"[analyst] Claude call failed for {section_type}: {e}")
            return None

    def set_generate_fn(self, fn: Callable):
        """Set the generate_section function from app.py for full integration."""
        self._generate_fn = fn

    # ---- Data Formatting ----

    def _format_agent_data(self, agent_data: Dict) -> str:
        """Format agent data into the market_data_str format expected by prompts."""
        lines = []

        ticker = agent_data.get("ticker", "")
        lines.append(f"--- CURRENT PRICE ---")
        lines.append(f"Ticker: {ticker}")
        if agent_data.get("name"):
            lines.append(f"Company: {agent_data['name']}")
        if agent_data.get("close"):
            lines.append(f"Current Price: {agent_data['close']} SAR")
        if agent_data.get("change_pct"):
            lines.append(f"Change: {agent_data['change_pct']}%")
        if agent_data.get("open"):
            lines.append(f"Open: {agent_data['open']}")
        if agent_data.get("high"):
            lines.append(f"High: {agent_data['high']}")
        if agent_data.get("low"):
            lines.append(f"Low: {agent_data['low']}")
        if agent_data.get("volume"):
            lines.append(f"Volume: {agent_data['volume']:,}")

        lines.append(f"\n--- VALUATION ---")
        for key in ["market_cap", "pe_ratio", "forward_pe", "pb_ratio", "eps", "beta"]:
            if agent_data.get(key) is not None:
                label = key.replace("_", " ").title()
                lines.append(f"{label}: {agent_data[key]}")

        lines.append(f"\n--- DIVIDENDS ---")
        for key in ["dividend_yield", "payout_ratio"]:
            if agent_data.get(key) is not None:
                label = key.replace("_", " ").title()
                val = agent_data[key]
                if isinstance(val, float) and val < 1:
                    val = f"{val * 100:.2f}%"
                lines.append(f"{label}: {val}")

        lines.append(f"\n--- PROFITABILITY ---")
        for key in ["revenue", "net_income", "gross_margins", "operating_margins", "profit_margins",
                     "roe", "roa", "free_cashflow", "operating_cashflow"]:
            if agent_data.get(key) is not None:
                label = key.replace("_", " ").title()
                lines.append(f"{label}: {agent_data[key]}")

        lines.append(f"\n--- BALANCE SHEET ---")
        for key in ["total_debt", "total_cash", "debt_to_equity", "current_ratio", "book_value"]:
            if agent_data.get(key) is not None:
                label = key.replace("_", " ").title()
                lines.append(f"{label}: {agent_data[key]}")

        if agent_data.get("business_summary"):
            lines.append(f"\n--- BUSINESS SUMMARY ---")
            lines.append(agent_data["business_summary"])

        # Sentiment overlay
        sentiment = agent_data.get("sentiment")
        if sentiment and isinstance(sentiment, dict):
            lines.append(f"\n--- COMMUNITY SENTIMENT ---")
            lines.append(f"Overall: {sentiment.get('overall_sentiment', 'N/A')}")
            lines.append(f"Bullish: {sentiment.get('bullish_pct', 0)}%")
            lines.append(f"Bearish: {sentiment.get('bearish_pct', 0)}%")
            if sentiment.get("top_themes"):
                lines.append(f"Top Themes: {', '.join(sentiment['top_themes'])}")

        return "\n".join(lines)

    def _format_news_data(self, agent_data: Dict) -> str:
        """Format news items into the news_str format expected by prompts."""
        news_items = agent_data.get("news_items", [])
        if not news_items:
            return "No recent news available."

        lines = ["Recent News:"]
        for item in news_items[:10]:
            if isinstance(item, dict):
                title = item.get("title", "")
                source = item.get("source", "")
                date = item.get("published_at", "")
                lines.append(f"- {title} ({source}, {date})")
            else:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def _get_section_key(self, section_type: str) -> str:
        """Map section type to the key used in results dict."""
        KEY_MAP = {
            "fundamental": "fundamental_analysis",
            "dividend": "dividend_analysis",
            "earnings": "earnings_analysis",
            "risk": "risk_assessment",
            "technical": "technical_analysis",
            "sector": "sector_rotation",
            "news_impact": "news_impact",
            "war_impact": "war_impact",
        }
        return KEY_MAP.get(section_type, section_type)
