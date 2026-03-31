"""
Sentiment Scoring and Trend Database (Task 25)

Extracts and stores sentiment scores from AI-generated reports. Sentiment is categorized
into multiple dimensions and stored with historical tracking for trend analysis.

Usage:
    from data.sentiment_tracker import (
        extract_sentiment, store_sentiment, get_sentiment_history,
        get_sentiment_change, generate_sentiment_chart, get_cross_ticker_sentiment
    )

    # Extract sentiment from report text
    scores = extract_sentiment("Strong growth momentum and outperform expectations...", "2010.SR")

    # Store in database
    store_sentiment("2010.SR", scores, report_id="rpt-123", model_version="v1")

    # Query sentiment trends
    history = get_sentiment_history("2010.SR", category="overall", limit=20)
    change = get_sentiment_change("2010.SR", lookback_days=30)

    # Generate visualization
    chart_html = generate_sentiment_chart("2010.SR")

    # Compare across tickers
    comparison = get_cross_ticker_sentiment(["2010.SR", "2222.SR", "7010.SR"])
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Supabase availability check
from data.supabase_client import SUPABASE_AVAILABLE

if SUPABASE_AVAILABLE:
    from data.supabase_client import SentimentDAO

logger = logging.getLogger(__name__)

# TAM Colors
ACCENT = "#1A6DB6"
GREEN = "#22C55E"
RED = "#EF4444"
TEXT = "#E6EDF3"
BG = "#070B14"
ORANGE = "#F59E0B"
GRAY = "#6B7280"

# Local JSON fallback
SENTIMENT_DATA_PATH = Path(__file__).parent / "sentiment_data.json"

# Sentiment categories
SENTIMENT_CATEGORIES = [
    "overall",
    "management_tone",
    "financial_health",
    "growth_outlook",
    "risk_level",
]

# Keyword/phrase mapping for sentiment extraction
POSITIVE_KEYWORDS = {
    "overall": ["strong growth", "outperform", "bullish", "exceeded expectations", "upgrade",
                "positive momentum", "improving margins", "robust", "accelerating", "momentum"],
    "management_tone": ["confident", "proactive", "strategic", "forward-looking", "decisive",
                        "experienced leadership", "transparent"],
    "financial_health": ["improving margins", "strong cash flow", "debt reduction", "profitable",
                         "revenue growth", "EBITDA improvement", "healthy balance sheet"],
    "growth_outlook": ["strong growth", "market expansion", "new products", "market share gains",
                       "accelerating growth", "upside potential", "catalysts"],
    "risk_level": ["managing risks", "mitigating factors", "diversified", "hedged", "resilient",
                   "contingency plans"],
}

NEGATIVE_KEYWORDS = {
    "overall": ["underperform", "bearish", "missed expectations", "downgrade", "declining",
                "risk", "deteriorating", "weakness", "headwinds", "pressure"],
    "management_tone": ["uncertain", "defensive", "cautious", "reactive", "challenged",
                        "turnover", "inexperienced"],
    "financial_health": ["margin compression", "cash burn", "debt increase", "unprofitable",
                         "revenue decline", "EBITDA pressure", "asset impairment"],
    "growth_outlook": ["slowing growth", "market saturation", "declining demand", "market share loss",
                       "maturing market", "headwinds"],
    "risk_level": ["rising risks", "geopolitical exposure", "regulatory concerns", "operational risks",
                   "concentration risk", "cybersecurity threats"],
}


def _load_sentiment_data() -> Dict[str, Any]:
    """Load sentiment data from JSON file. Returns empty dict if file doesn't exist."""
    try:
        if SENTIMENT_DATA_PATH.exists():
            with open(SENTIMENT_DATA_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading sentiment data: {e}")
    return {}


def _save_sentiment_data(data: Dict[str, Any]) -> None:
    """Save sentiment data to JSON file."""
    try:
        with open(SENTIMENT_DATA_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving sentiment data: {e}")


def extract_sentiment(report_text: str, ticker: str) -> Dict[str, float]:
    """
    Parse report text and extract sentiment scores across categories.

    Uses keyword/phrase matching to score sentiment in range [-1.0, 1.0]:
    - -1.0: very bearish
    - 0.0: neutral
    - 1.0: very bullish

    Args:
        report_text: Full text of the report to analyze
        ticker: Stock ticker for context

    Returns:
        Dict with keys for each sentiment category, each with float score [-1.0, 1.0]
    """
    scores = {}
    text_lower = report_text.lower()

    for category in SENTIMENT_CATEGORIES:
        positive_count = 0
        negative_count = 0

        # Count positive signals
        for keyword in POSITIVE_KEYWORDS.get(category, []):
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
            positive_count += count

        # Count negative signals
        for keyword in NEGATIVE_KEYWORDS.get(category, []):
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
            negative_count += count

        # Calculate net score
        total = positive_count + negative_count
        if total == 0:
            score = 0.0
        else:
            score = (positive_count - negative_count) / max(total, 1)
            # Clamp to [-1.0, 1.0]
            score = max(-1.0, min(1.0, score))

        scores[category] = round(score, 3)

    return scores


def store_sentiment(
    ticker: str,
    scores: Dict[str, float],
    report_id: Optional[str] = None,
    model_version: str = "v1"
) -> bool:
    """
    Save sentiment scores to database.

    Args:
        ticker: Stock ticker
        scores: Dict of category -> score from extract_sentiment()
        report_id: Optional ID linking to the source report
        model_version: Version of sentiment extraction model

    Returns:
        True if successful, False otherwise
    """
    try:
        sentiment_record = {
            "ticker": ticker,
            "scores": scores,
            "report_id": report_id,
            "model_version": model_version,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if SUPABASE_AVAILABLE:
            dao = SentimentDAO()
            return dao.insert(sentiment_record)
        else:
            # JSON fallback
            data = _load_sentiment_data()
            if ticker not in data:
                data[ticker] = []
            data[ticker].append(sentiment_record)
            _save_sentiment_data(data)
            return True

    except Exception as e:
        logger.error(f"Error storing sentiment for {ticker}: {e}")
        return False


def get_sentiment_history(
    ticker: str,
    category: str = "overall",
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Retrieve historical sentiment scores for a ticker.

    Args:
        ticker: Stock ticker
        category: Sentiment category (or 'all' for all categories)
        limit: Maximum number of records to return

    Returns:
        List of sentiment records ordered by timestamp (newest first)
    """
    try:
        if SUPABASE_AVAILABLE:
            dao = SentimentDAO()
            records = dao.get_by_ticker(ticker, limit=limit)
        else:
            # JSON fallback
            data = _load_sentiment_data()
            records = data.get(ticker, [])
            records = sorted(records, key=lambda x: x["timestamp"], reverse=True)[:limit]

        # Filter by category if not 'all'
        if category != "all":
            for record in records:
                # Keep only the requested category score
                if "scores" in record:
                    record["score"] = record["scores"].get(category, 0.0)

        return records

    except Exception as e:
        logger.error(f"Error retrieving sentiment history for {ticker}: {e}")
        return []


def get_sentiment_change(ticker: str, lookback_days: int = 30) -> Dict[str, float]:
    """
    Calculate change in sentiment over a time period.

    Args:
        ticker: Stock ticker
        lookback_days: Number of days to look back

    Returns:
        Dict with keys {category}_change showing delta in sentiment
    """
    history = get_sentiment_history(ticker, category="all", limit=100)
    if not history:
        return {}

    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Find most recent and oldest records within lookback period
    recent = None
    oldest = None

    for record in history:
        ts = datetime.fromisoformat(record["timestamp"])
        if ts >= cutoff_date:
            if recent is None:
                recent = record
        if ts >= cutoff_date:
            oldest = record

    if not recent or not oldest:
        return {}

    changes = {}
    for category in SENTIMENT_CATEGORIES:
        recent_score = recent.get("scores", {}).get(category, 0.0)
        oldest_score = oldest.get("scores", {}).get(category, 0.0)
        changes[f"{category}_change"] = round(recent_score - oldest_score, 3)

    return changes


def generate_sentiment_chart(ticker: str) -> str:
    """
    Generate an interactive Plotly chart of sentiment trends.

    Args:
        ticker: Stock ticker

    Returns:
        HTML string for embedding in web pages
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        logger.warning("Plotly not installed. Cannot generate chart.")
        return ""

    history = get_sentiment_history(ticker, category="all", limit=50)
    if not history:
        return f"<p>No sentiment data available for {ticker}</p>"

    # Prepare data
    timestamps = []
    overall_scores = []
    management_scores = []
    financial_scores = []
    growth_scores = []
    risk_scores = []

    for record in reversed(history):  # Reverse to chronological order
        timestamps.append(record["timestamp"][:10])  # Date only
        scores = record.get("scores", {})
        overall_scores.append(scores.get("overall", 0.0))
        management_scores.append(scores.get("management_tone", 0.0))
        financial_scores.append(scores.get("financial_health", 0.0))
        growth_scores.append(scores.get("growth_outlook", 0.0))
        risk_scores.append(scores.get("risk_level", 0.0))

    # Create figure
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps, y=overall_scores,
        name="Overall Sentiment",
        mode="lines+markers",
        line=dict(color=ACCENT, width=2),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=timestamps, y=management_scores,
        name="Management Tone",
        mode="lines",
        line=dict(color=GREEN, width=1, dash="dash"),
        opacity=0.7
    ))

    fig.add_trace(go.Scatter(
        x=timestamps, y=financial_scores,
        name="Financial Health",
        mode="lines",
        line=dict(color=ORANGE, width=1, dash="dash"),
        opacity=0.7
    ))

    fig.add_trace(go.Scatter(
        x=timestamps, y=growth_scores,
        name="Growth Outlook",
        mode="lines",
        line=dict(color=GREEN, width=1, dash="dash"),
        opacity=0.7
    ))

    fig.add_trace(go.Scatter(
        x=timestamps, y=risk_scores,
        name="Risk Level",
        mode="lines",
        line=dict(color=RED, width=1, dash="dash"),
        opacity=0.7
    ))

    # Add zero reference line
    fig.add_hline(y=0, line_dash="dot", line_color=GRAY, opacity=0.5)

    fig.update_layout(
        title=f"{ticker} - Sentiment Trends",
        xaxis_title="Date",
        yaxis_title="Sentiment Score (-1.0 to 1.0)",
        hovermode="x unified",
        template="plotly_dark",
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(color=TEXT),
        height=400,
    )

    fig.update_yaxes(range=[-1.1, 1.1])

    return fig.to_html(include_plotlyjs="cdn", div_id=f"sentiment-chart-{ticker}")


def get_cross_ticker_sentiment(tickers: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Compare current sentiment across multiple tickers.

    Args:
        tickers: List of stock tickers to compare

    Returns:
        Dict mapping ticker -> dict of sentiment categories and scores
    """
    comparison = {}

    for ticker in tickers:
        history = get_sentiment_history(ticker, category="all", limit=1)
        if history:
            record = history[0]
            comparison[ticker] = record.get("scores", {})
        else:
            comparison[ticker] = {cat: 0.0 for cat in SENTIMENT_CATEGORIES}

    return comparison


def generate_sentiment_badge_html(score: float, category: str = "overall") -> str:
    """
    Generate HTML badge for displaying a sentiment score.

    Args:
        score: Sentiment score between -1.0 and 1.0
        category: Category name for label

    Returns:
        HTML string for glass-styled badge
    """
    if score > 0.3:
        color = GREEN
        label = "Bullish"
    elif score < -0.3:
        color = RED
        label = "Bearish"
    else:
        color = GRAY
        label = "Neutral"

    confidence = abs(score)

    html = f"""
    <div style="
        display: inline-block;
        padding: 8px 12px;
        background: rgba(26, 109, 182, 0.1);
        border: 1px solid {color};
        border-radius: 6px;
        margin: 4px;
        font-size: 12px;
        color: {TEXT};
    ">
        <strong>{category.replace('_', ' ').title()}</strong><br>
        <span style="color: {color}; font-weight: bold;">{label}</span>
        <div style="
            width: 80px;
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            margin-top: 4px;
            overflow: hidden;
        ">
            <div style="
                width: {confidence * 100}%;
                height: 100%;
                background: {color};
            "></div>
        </div>
    </div>
    """
    return html
