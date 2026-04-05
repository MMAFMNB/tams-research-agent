"""
Sentiment Agent — gathers community sentiment from Argaam forums and social media.

Data sources:
1. Argaam community/forum pages (web scraping)
2. X/Twitter Arabic hashtags (web scraping)
3. Existing sentiment_tracker.py (internal data)

Output: Aggregated sentiment scores, mention volumes, top themes.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Arabic sentiment keywords
BULLISH_KEYWORDS = [
    "ارتفاع", "صعود", "شراء", "إيجابي", "نمو", "ربح", "توزيعات",
    "buy", "bullish", "growth", "profit", "strong", "upside", "rally",
]
BEARISH_KEYWORDS = [
    "انخفاض", "هبوط", "بيع", "سلبي", "خسارة", "تراجع",
    "sell", "bearish", "loss", "decline", "weak", "downside", "crash",
]


class SentimentAgent(BaseAgent):
    """Gathers and analyzes community sentiment for Saudi stocks."""

    name = "sentiment"
    cache_ttl = 3600             # 1 hour for sentiment
    rate_limit = 0.2             # 1 request per 5 seconds (conservative)
    max_retries = 2
    required_fields = ["ticker", "overall_sentiment"]

    async def fetch(self, ticker: str, **kwargs) -> Optional[Dict]:
        """
        Fetch sentiment data for a Tadawul stock.

        Returns aggregated sentiment analysis.
        """
        period = kwargs.get("period", "24h")
        comments = []
        source_breakdown = {}

        # Source 1: Argaam forums/community
        argaam_comments = await self._fetch_argaam_sentiment(ticker)
        if argaam_comments:
            comments.extend(argaam_comments)
            source_breakdown["argaam_forums"] = self._analyze_comments(argaam_comments)

        # Source 2: Try X/Twitter (best effort)
        twitter_comments = await self._fetch_twitter_sentiment(ticker)
        if twitter_comments:
            comments.extend(twitter_comments)
            source_breakdown["twitter"] = self._analyze_comments(twitter_comments)

        # Source 3: Internal sentiment tracker
        internal = self._fetch_internal_sentiment(ticker)
        if internal:
            source_breakdown["internal"] = internal

        if not comments and not internal:
            # No sentiment data available — return a neutral baseline
            return {
                "ticker": ticker,
                "period": period,
                "overall_sentiment": 0.0,
                "volume_mentions": 0,
                "bullish_pct": 0,
                "bearish_pct": 0,
                "neutral_pct": 100,
                "top_themes": [],
                "sample_comments": [],
                "source_breakdown": {},
                "data_quality": "no_data",
                "fetched_at": datetime.now().isoformat(),
            }

        # Aggregate across all sources
        all_sentiments = [c.get("sentiment", 0) for c in comments if c.get("sentiment") is not None]
        overall = sum(all_sentiments) / len(all_sentiments) if all_sentiments else 0.0

        bullish = sum(1 for s in all_sentiments if s > 0.2)
        bearish = sum(1 for s in all_sentiments if s < -0.2)
        neutral = len(all_sentiments) - bullish - bearish
        total = max(len(all_sentiments), 1)

        # Extract themes
        themes = self._extract_themes(comments)

        return {
            "ticker": ticker,
            "period": period,
            "overall_sentiment": round(overall, 3),
            "volume_mentions": len(comments),
            "bullish_pct": round(bullish / total * 100),
            "bearish_pct": round(bearish / total * 100),
            "neutral_pct": round(neutral / total * 100),
            "top_themes": themes[:5],
            "sample_comments": [c.get("text", "")[:200] for c in comments[:5]],
            "source_breakdown": source_breakdown,
            "data_quality": "good" if len(comments) >= 10 else "limited",
            "fetched_at": datetime.now().isoformat(),
        }

    async def _fetch_argaam_sentiment(self, ticker: str) -> List[Dict]:
        """Scrape Argaam forum/community discussions about a stock."""
        try:
            from data.agents.scraper_utils import fetch_page, parse_html, clean_arabic_text

            # Argaam company discussion page
            url = f"https://www.argaam.com/en/company/companyforums/marketid/3/companyid/{ticker}"
            html = await fetch_page(url, timeout=20.0)

            if not html:
                return []

            soup = parse_html(html)
            if not soup:
                return []

            comments = []

            # Look for forum posts, comments, discussion threads
            for el in soup.select(
                ".forum-post, .comment, .discussion-item, .post-content, "
                ".comment-body, .message-text, .user-comment, article"
            ):
                text = clean_arabic_text(el.get_text(strip=True))
                if text and len(text) > 10:
                    sentiment = self._score_text(text)
                    comments.append({
                        "text": text[:500],
                        "source": "argaam",
                        "sentiment": sentiment,
                        "timestamp": datetime.now().isoformat(),
                    })

            return comments[:50]  # Limit to 50 comments

        except Exception as e:
            logger.warning(f"[sentiment] Argaam forums scrape error for {ticker}: {e}")
            return []

    async def _fetch_twitter_sentiment(self, ticker: str) -> List[Dict]:
        """
        Fetch sentiment from X/Twitter for Saudi stock hashtags.

        Note: Twitter scraping is fragile and may not work without auth.
        This is a best-effort source.
        """
        try:
            from data.agents.scraper_utils import fetch_page, parse_html, clean_arabic_text

            # Build search query with Arabic hashtags
            names = self._get_ticker_names(ticker)
            if not names:
                return []

            # Try Nitter (open-source Twitter frontend) for scraping
            query = names[0]
            # Multiple Nitter instances to try
            nitter_instances = [
                f"https://nitter.privacydev.net/search?f=tweets&q={query}",
            ]

            for nitter_url in nitter_instances:
                try:
                    html = await fetch_page(nitter_url, timeout=15.0)
                    if not html:
                        continue

                    soup = parse_html(html)
                    if not soup:
                        continue

                    comments = []
                    for tweet in soup.select(".tweet-content, .timeline-item .tweet-body"):
                        text = clean_arabic_text(tweet.get_text(strip=True))
                        if text and len(text) > 10:
                            sentiment = self._score_text(text)
                            comments.append({
                                "text": text[:500],
                                "source": "twitter",
                                "sentiment": sentiment,
                                "timestamp": datetime.now().isoformat(),
                            })

                    if comments:
                        return comments[:30]

                except Exception:
                    continue

            return []

        except Exception as e:
            logger.debug(f"[sentiment] Twitter fetch error (expected): {e}")
            return []

    def _fetch_internal_sentiment(self, ticker: str) -> Optional[Dict]:
        """Get sentiment from internal sentiment_tracker if available."""
        try:
            from data.sentiment_tracker import get_sentiment_history
            history = get_sentiment_history(ticker, days=7)
            if history:
                scores = [h.get("score", 0) for h in history if h.get("score") is not None]
                if scores:
                    return {
                        "count": len(scores),
                        "avg_sentiment": round(sum(scores) / len(scores), 3),
                        "source": "internal",
                    }
        except (ImportError, Exception):
            pass
        return None

    # ---- Sentiment Analysis ----

    def _score_text(self, text: str) -> float:
        """
        Score text sentiment using keyword matching.

        Returns -1.0 (bearish) to 1.0 (bullish).
        For more accurate analysis, Claude Haiku is used in batch mode.
        """
        text_lower = text.lower()

        bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
        bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        # Score from -1 to 1
        score = (bullish_count - bearish_count) / total
        return round(score, 3)

    def _analyze_comments(self, comments: List[Dict]) -> Dict:
        """Analyze a batch of comments and return summary stats."""
        if not comments:
            return {"count": 0, "avg_sentiment": 0.0}

        sentiments = [c.get("sentiment", 0) for c in comments]
        return {
            "count": len(comments),
            "avg_sentiment": round(sum(sentiments) / len(sentiments), 3),
        }

    def _extract_themes(self, comments: List[Dict]) -> List[str]:
        """Extract top discussion themes from comments."""
        theme_keywords = {
            "dividend": ["dividend", "توزيع", "payout", "yield"],
            "oil_prices": ["oil", "نفط", "opec", "crude", "brent"],
            "earnings": ["earnings", "profit", "ربح", "revenue", "إيرادات"],
            "expansion": ["expansion", "توسع", "growth", "new project"],
            "regulation": ["regulation", "cma", "هيئة", "compliance"],
            "vision_2030": ["vision 2030", "رؤية 2030", "neom", "giga"],
            "interest_rates": ["interest", "rate", "فائدة", "sama"],
            "ipo": ["ipo", "listing", "إدراج"],
        }

        theme_counts = {}
        all_text = " ".join(c.get("text", "") for c in comments).lower()

        for theme, keywords in theme_keywords.items():
            count = sum(1 for kw in keywords if kw in all_text)
            if count > 0:
                theme_counts[theme] = count

        return sorted(theme_counts, key=theme_counts.get, reverse=True)

    def _get_ticker_names(self, ticker: str) -> List[str]:
        """Get search-friendly names for a ticker."""
        NAMES = {
            "2222": ["Saudi Aramco", "ارامكو"],
            "2010": ["SABIC", "سابك"],
            "1120": ["Al Rajhi Bank", "الراجحي"],
            "7010": ["STC", "الاتصالات"],
            "2280": ["Almarai", "المراعي"],
        }
        return NAMES.get(str(ticker), [str(ticker)])
