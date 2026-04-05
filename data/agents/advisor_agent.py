"""
Advisor Agent — generates actionable investment insights from analysis results.

Responsibilities:
- CIO-level executive summaries
- Morning market briefs
- Investment recommendations (Buy/Hold/Sell)
- Alert generation based on combined signals
- Feeds structured data to report generators (DOCX, PDF, PPTX, XLSX)
"""

import importlib
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from data.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AdvisorAgent(BaseAgent):
    """Generates investment insights and recommendations from analysis output."""

    name = "advisor"
    cache_ttl = 43200            # 12 hours
    rate_limit = 0.0
    max_retries = 1
    required_fields = ["ticker"]

    async def fetch(self, ticker: str, **kwargs) -> Optional[Dict]:
        """
        Generate advisory output from analyst results.

        Args:
            ticker: Tadawul ticker
            kwargs:
                analysis: Dict from AnalystAgent (sections + data)
                agent_data: Dict from orchestrator (raw data)
                mode: "full_report" | "morning_brief" | "quick_insight"

        Returns:
            Dict with executive summary, recommendations, and report-ready data.
        """
        analysis = kwargs.get("analysis", {})
        agent_data = kwargs.get("agent_data", {})
        mode = kwargs.get("mode", "full_report")

        if mode == "morning_brief":
            return await self._generate_morning_brief(ticker, agent_data)
        elif mode == "quick_insight":
            return await self._generate_quick_insight(ticker, analysis, agent_data)
        else:
            return await self._generate_full_advisory(ticker, analysis, agent_data)

    async def _generate_full_advisory(
        self, ticker: str, analysis: Dict, agent_data: Dict
    ) -> Optional[Dict]:
        """Generate full advisory with executive summary and recommendations."""
        sections = analysis.get("sections", {})
        if not sections:
            logger.warning(f"[advisor] No analysis sections for {ticker}")
            return None

        # Generate executive summary using existing report_compiler prompt
        exec_summary = self._generate_executive_summary(ticker, sections, agent_data)

        # Extract recommendation signals from analysis
        signals = self._extract_signals(sections, agent_data)

        return {
            "ticker": ticker,
            "mode": "full_report",
            "executive_summary": exec_summary,
            "signals": signals,
            "recommendation": signals.get("recommendation", "HOLD"),
            "confidence": signals.get("confidence", 0.5),
            "price_target": signals.get("price_target"),
            "key_catalysts": signals.get("catalysts", []),
            "key_risks": signals.get("risks", []),
            "sections": sections,  # Pass through for generators
            "timestamp": datetime.now().isoformat(),
        }

    async def _generate_morning_brief(self, ticker: str, agent_data: Dict) -> Optional[Dict]:
        """Generate a concise morning briefing."""
        try:
            from prompts.morning_brief import MORNING_BRIEF_PROMPT

            # Build watchlist data from agent_data
            watchlist_data = (
                f"Ticker: {ticker}\n"
                f"Name: {agent_data.get('name', ticker)}\n"
                f"Price: {agent_data.get('close', 'N/A')} SAR\n"
                f"Change: {agent_data.get('change_pct', 'N/A')}%\n"
            )

            # Format news
            news_items = agent_data.get("news_items", [])
            news_text = "\n".join(
                f"- {n.get('title', '')}" for n in news_items[:5]
            ) if news_items else "No recent news."

            prompt = MORNING_BRIEF_PROMPT.format(
                date=datetime.now().strftime("%Y-%m-%d"),
                watchlist_data=watchlist_data,
                market_context="Saudi Tadawul market data",
                news_highlights=news_text,
            )

            brief = self._call_claude(prompt, model_tier="haiku")

            return {
                "ticker": ticker,
                "mode": "morning_brief",
                "brief": brief,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"[advisor] Morning brief error: {e}")
            return None

    async def _generate_quick_insight(
        self, ticker: str, analysis: Dict, agent_data: Dict
    ) -> Optional[Dict]:
        """Generate a quick 2-3 sentence insight."""
        name = agent_data.get("name", ticker)
        price = agent_data.get("close", "N/A")
        pe = agent_data.get("pe_ratio", "N/A")
        div_yield = agent_data.get("dividend_yield")
        div_str = f"{div_yield * 100:.1f}%" if isinstance(div_yield, (int, float)) and div_yield < 1 else str(div_yield or "N/A")

        sentiment = agent_data.get("sentiment", {})
        sent_score = sentiment.get("overall_sentiment", 0) if isinstance(sentiment, dict) else 0

        prompt = (
            f"Give a 2-3 sentence investment insight for {name} ({ticker}.SR).\n"
            f"Current price: {price} SAR, PE: {pe}, Dividend Yield: {div_str}\n"
            f"Community sentiment score: {sent_score} (-1=bearish, 1=bullish)\n"
            f"Be specific and opinionated. End with BUY/HOLD/SELL."
        )

        insight = self._call_claude(prompt, model_tier="haiku")

        return {
            "ticker": ticker,
            "mode": "quick_insight",
            "insight": insight,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_executive_summary(
        self, ticker: str, sections: Dict, agent_data: Dict
    ) -> Optional[str]:
        """Generate CIO-level executive summary."""
        try:
            from prompts.report_compiler import EXECUTIVE_SUMMARY_PROMPT

            # Build market data string from agent_data
            market_data = (
                f"Ticker: {ticker}\n"
                f"Company: {agent_data.get('name', ticker)}\n"
                f"Price: {agent_data.get('close', 'N/A')} SAR\n"
                f"Market Cap: {agent_data.get('market_cap', 'N/A')}\n"
                f"PE Ratio: {agent_data.get('pe_ratio', 'N/A')}\n"
                f"Dividend Yield: {agent_data.get('dividend_yield', 'N/A')}\n"
                f"EPS: {agent_data.get('eps', 'N/A')}\n"
            )

            # Compile sections text
            sections_text = "\n\n".join(
                f"=== {key} ===\n{value[:1000]}" for key, value in sections.items()
            )

            prompt = EXECUTIVE_SUMMARY_PROMPT.format(
                market_data=market_data,
                sections=sections_text,
            )

            return self._call_claude(prompt, model_tier="sonnet")

        except Exception as e:
            logger.error(f"[advisor] Executive summary error: {e}")
            return None

    def _extract_signals(self, sections: Dict, agent_data: Dict) -> Dict:
        """
        Extract investment signals from analysis sections and data.

        Combines fundamental, technical, sentiment, and news signals.
        """
        signals = {
            "recommendation": "HOLD",
            "confidence": 0.5,
            "price_target": None,
            "catalysts": [],
            "risks": [],
            "bullish_factors": 0,
            "bearish_factors": 0,
        }

        # Score fundamental signals
        pe = agent_data.get("pe_ratio")
        if pe:
            if pe < 12:
                signals["bullish_factors"] += 1
                signals["catalysts"].append("Low PE valuation")
            elif pe > 25:
                signals["bearish_factors"] += 1
                signals["risks"].append("High PE valuation")

        div_yield = agent_data.get("dividend_yield")
        if div_yield and isinstance(div_yield, (int, float)):
            yield_pct = div_yield * 100 if div_yield < 1 else div_yield
            if yield_pct > 4:
                signals["bullish_factors"] += 1
                signals["catalysts"].append(f"Strong dividend yield ({yield_pct:.1f}%)")

        debt_equity = agent_data.get("debt_to_equity")
        if debt_equity and debt_equity > 100:
            signals["bearish_factors"] += 1
            signals["risks"].append("High leverage")

        # Score sentiment signals
        sentiment = agent_data.get("sentiment", {})
        if isinstance(sentiment, dict):
            sent_score = sentiment.get("overall_sentiment", 0)
            if sent_score > 0.3:
                signals["bullish_factors"] += 1
                signals["catalysts"].append("Positive community sentiment")
            elif sent_score < -0.3:
                signals["bearish_factors"] += 1
                signals["risks"].append("Negative community sentiment")

        # Try ML signal model first
        try:
            from data.ml.signal_model import predict_direction, record_signals
            ml_prediction = predict_direction(signals, agent_data)
            if ml_prediction.get("model_available"):
                direction = ml_prediction["direction"]
                ml_conf = ml_prediction["confidence"]
                signals["ml_prediction"] = ml_prediction

                # Blend ML prediction with rule-based signals
                direction_map = {"UP": "BUY", "DOWN": "SELL", "FLAT": "HOLD"}
                if ml_conf > 0.6:
                    signals["recommendation"] = direction_map.get(direction, "HOLD")
                    signals["confidence"] = ml_conf
                    signals["recommendation_source"] = "ml_model"
                    # Record signals for outcome tracking
                    record_signals(sections.get("ticker", ""), signals, agent_data)
                    return signals
        except ImportError:
            pass

        # Fallback: rule-based recommendation
        bull = signals["bullish_factors"]
        bear = signals["bearish_factors"]
        net = bull - bear

        if net >= 3:
            signals["recommendation"] = "STRONG BUY"
            signals["confidence"] = 0.85
        elif net >= 1:
            signals["recommendation"] = "BUY"
            signals["confidence"] = 0.7
        elif net <= -3:
            signals["recommendation"] = "STRONG SELL"
            signals["confidence"] = 0.85
        elif net <= -1:
            signals["recommendation"] = "SELL"
            signals["confidence"] = 0.65
        else:
            signals["recommendation"] = "HOLD"
            signals["confidence"] = 0.5

        signals["recommendation_source"] = "rule_based"

        # Record signals for outcome tracking (even with rule-based)
        try:
            from data.ml.signal_model import record_signals
            record_signals(agent_data.get("ticker", ""), signals, agent_data)
        except ImportError:
            pass

        return signals

    def _call_claude(self, prompt: str, model_tier: str = "sonnet") -> Optional[str]:
        """Call Claude API with cost-aware model selection."""
        try:
            from data.cost.model_router import MODEL_IDS
            model = MODEL_IDS.get(model_tier, "claude-sonnet-4-20250514")
        except ImportError:
            model = "claude-sonnet-4-20250514" if model_tier == "sonnet" else "claude-haiku-3-5-20241022"

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
            logger.error(f"[advisor] Claude call failed: {e}")
            return None
