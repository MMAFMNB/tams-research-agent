"""
Morning Brief AI prompt template and generation function.

Generates concise daily market briefings for TAM Capital analysts,
covering watchlist movers, market context, news highlights, and AI insights.
"""

from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)

# TAM Capital Liquid Glass color palette
C_TEXT = "#E6EDF3"
C_TEXT2 = "#8B949E"
C_ACCENT = "#1A6DB6"
C_GREEN = "#22C55E"
C_RED = "#EF4444"
C_ORANGE = "#F59E0B"
C_GLASS = "rgba(34,47,98,0.12)"
C_BORDER = "rgba(108,185,182,0.08)"

MORNING_BRIEF_PROMPT = """You are a senior analyst at TAM Capital, a CMA-regulated Saudi asset manager.
Generate a concise morning briefing for {date}.

## Watchlist Status
{watchlist_data}

## Market Context
{market_context}

## Recent News & Developments
{news_data}

Structure your brief as:

### Market Pulse
One paragraph summarizing TASI/Saudi market sentiment today and major global market moves affecting local equities.

### Watchlist Movers
Top 3-5 movers (up or down) from the analyst's watchlist with brief context on what drove the moves.

### News Highlights
2-3 key headlines affecting watched tickers or the broader Saudi market (from the news data provided).

### Upcoming Events
Any earnings announcements, dividend ex-dates, or regulatory events in the next 7 days for watched stocks.

### AI Insights
One observation connecting dots across the watchlist - patterns, sector rotations, correlation changes, or risks worth monitoring.

Keep the entire brief under 500 words. Be specific with numbers, use the analyst's timezone context, and be actionable.
Use Arabic numerals for prices and percentages. Format percentages with + or - sign (e.g., +2.3%, -1.1%)."""


def _format_watchlist_data(tickers: List[str], stock_data_fn: Callable) -> str:
    """
    Format watchlist data for the prompt.

    Args:
        tickers: List of ticker symbols to include
        stock_data_fn: Function to fetch stock data (signature: (ticker) -> dict)

    Returns:
        Formatted watchlist summary string
    """
    lines = ["Watched Tickers:"]

    for ticker in tickers:
        try:
            data = stock_data_fn(ticker)
            if not data:
                continue

            name = data.get("name", ticker)
            price = data.get("current_price", 0)
            prev_close = data.get("previous_close", 0)
            volume = data.get("volume", 0)
            avg_volume = data.get("avg_volume", 1)

            if prev_close > 0:
                pct_change = ((price - prev_close) / prev_close) * 100
                sign = "+" if pct_change >= 0 else ""
                lines.append(
                    f"- {ticker}: {name} | Price: {price:.2f} | Change: {sign}{pct_change:.1f}% | "
                    f"Volume: {volume:,.0f} ({volume/avg_volume:.1f}x avg)"
                )
            else:
                lines.append(f"- {ticker}: {name} | Price: {price:.2f}")
        except Exception as e:
            logger.warning(f"Error fetching data for {ticker}: {e}")
            lines.append(f"- {ticker}: [Data unavailable]")

    return "\n".join(lines)


def _format_market_context() -> str:
    """
    Format current market context and indices.

    Returns:
        Market context string
    """
    try:
        from data.market_data import fetch_stock_data

        lines = ["Current Market Status:"]

        # TASI (Tadawul All Share Index) - can be fetched as ^TASI or 1010.SR (Riyad Bank as proxy)
        try:
            # Try to get TASI data
            tasi_data = fetch_stock_data("^TASI")
            if tasi_data and tasi_data.get("current_price"):
                tasi_price = tasi_data.get("current_price", 0)
                tasi_prev = tasi_data.get("previous_close", 0)
                if tasi_prev > 0:
                    tasi_change = ((tasi_price - tasi_prev) / tasi_prev) * 100
                    sign = "+" if tasi_change >= 0 else ""
                    lines.append(f"- TASI (Tadawul Index): {tasi_price:.0f} ({sign}{tasi_change:.1f}%)")
        except Exception:
            lines.append("- TASI: [Market data unavailable]")

        # Global context: S&P 500
        try:
            sp500_data = fetch_stock_data("^GSPC")
            if sp500_data and sp500_data.get("current_price"):
                sp_price = sp500_data.get("current_price", 0)
                sp_prev = sp500_data.get("previous_close", 0)
                if sp_prev > 0:
                    sp_change = ((sp_price - sp_prev) / sp_prev) * 100
                    sign = "+" if sp_change >= 0 else ""
                    lines.append(f"- S&P 500: {sp_price:.0f} ({sign}{sp_change:.1f}%)")
        except Exception:
            lines.append("- S&P 500: [Data unavailable]")

        # Oil prices
        try:
            crude_data = fetch_stock_data("CL=F")  # WTI Crude Oil
            if crude_data and crude_data.get("current_price"):
                crude_price = crude_data.get("current_price", 0)
                crude_prev = crude_data.get("previous_close", 0)
                if crude_prev > 0:
                    crude_change = ((crude_price - crude_prev) / crude_prev) * 100
                    sign = "+" if crude_change >= 0 else ""
                    lines.append(f"- WTI Crude Oil: ${crude_price:.2f}/bbl ({sign}{crude_change:.1f}%)")
        except Exception:
            lines.append("- WTI Crude Oil: [Data unavailable]")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Error formatting market context: {e}")
        return "Market Context: [Unable to retrieve real-time data]"


def generate_morning_brief(
    user_tickers: List[str],
    call_claude_fn: Callable,
    fetch_stock_fn: Optional[Callable] = None,
    fetch_news_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Generate a morning briefing for the user's watchlist.

    Args:
        user_tickers: List of ticker symbols to monitor
        call_claude_fn: Function to call Claude API (signature: (prompt) -> str)
        fetch_stock_fn: Optional function to fetch stock data (signature: (ticker) -> dict)
                       Defaults to data.market_data.fetch_stock_data if not provided
        fetch_news_fn: Optional function to fetch news (signature: (company_name, ticker) -> str)
                      Defaults to data.web_search.search_company_news if not provided

    Returns:
        Dict with keys:
        - content: Generated brief markdown string
        - tickers_covered: List of tickers successfully processed
        - generated_at: ISO timestamp
        - market_data: Dict with market indices and watchlist data
    """
    try:
        # Import data functions if not provided
        if fetch_stock_fn is None:
            try:
                from data.market_data import fetch_stock_data
                fetch_stock_fn = fetch_stock_data
            except ImportError:
                logger.warning("data.market_data not available")
                fetch_stock_fn = lambda x: {}

        if fetch_news_fn is None:
            try:
                from data.web_search import search_company_news
                fetch_news_fn = search_company_news
            except ImportError:
                logger.warning("data.web_search not available")
                fetch_news_fn = lambda x, y: ""

        # Validate input
        if not user_tickers:
            return {
                "content": "No tickers provided for morning brief.",
                "tickers_covered": [],
                "generated_at": datetime.now().isoformat(),
                "market_data": {},
            }

        # Fetch watchlist data
        watchlist_data = _format_watchlist_data(user_tickers, fetch_stock_fn)

        # Get market context
        market_context = _format_market_context()

        # Fetch top news
        news_lines = ["Recent Market News:"]
        tickers_covered = []

        for ticker in user_tickers[:5]:  # Limit to top 5 to avoid API rate limits
            try:
                stock_data = fetch_stock_fn(ticker)
                if stock_data:
                    company_name = stock_data.get("name", ticker)
                    news = fetch_news_fn(company_name, ticker)
                    if news and news != "No recent news found.":
                        news_lines.append(f"\n{ticker} News:\n{news[:300]}")  # Truncate to 300 chars
                        tickers_covered.append(ticker)
            except Exception as e:
                logger.warning(f"Error fetching news for {ticker}: {e}")

        news_data = "\n".join(news_lines) if len(news_lines) > 1 else "No recent news available."

        # Format the prompt
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        formatted_prompt = MORNING_BRIEF_PROMPT.format(
            date=current_date,
            watchlist_data=watchlist_data,
            market_context=market_context,
            news_data=news_data,
        )

        # Call Claude to generate the brief
        brief_content = call_claude_fn(formatted_prompt)

        return {
            "content": brief_content,
            "tickers_covered": tickers_covered,
            "generated_at": datetime.now().isoformat(),
            "market_data": {
                "watchlist": watchlist_data,
                "market_context": market_context,
            },
        }

    except Exception as e:
        logger.error(f"Error generating morning brief: {e}")
        return {
            "content": f"Error generating brief: {str(e)}",
            "tickers_covered": [],
            "generated_at": datetime.now().isoformat(),
            "market_data": {},
        }


def format_brief_for_display(brief: Dict[str, Any]) -> str:
    """
    Format a morning brief for Streamlit display with glass styling.

    Args:
        brief: Brief dict from generate_morning_brief

    Returns:
        HTML string with TAM Liquid Glass theme styling
    """
    content = brief.get("content", "No content available")
    generated_at = brief.get("generated_at", "Unknown")
    tickers_covered = brief.get("tickers_covered", [])

    # Parse timestamp for readable format
    try:
        dt = datetime.fromisoformat(generated_at)
        time_str = dt.strftime("%I:%M %p")
    except Exception:
        time_str = "Unknown"

    # Split content into sections for better display
    sections = []
    current_section = None
    current_content = []

    for line in content.split("\n"):
        if line.startswith("###"):
            if current_section:
                sections.append((current_section, "\n".join(current_content).strip()))
            current_section = line.replace("###", "").strip()
            current_content = []
        elif line.strip():
            current_content.append(line)

    if current_section:
        sections.append((current_section, "\n".join(current_content).strip()))

    # Build HTML
    html_parts = [
        f"""
        <div style="
            background: {C_GLASS};
            border: 1px solid {C_BORDER};
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
            margin-bottom: 24px;
        ">
        """
    ]

    # Header
    html_parts.append(
        f"""
        <div style="margin-bottom: 20px;">
            <div style="
                color: {C_TEXT};
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 8px;
            ">Good Morning</div>
            <div style="
                color: {C_TEXT2};
                font-size: 12px;
                letter-spacing: 0.5px;
            ">Generated at {time_str} • {len(tickers_covered)} tickers monitored</div>
        </div>
        """
    )

    # Sections
    for i, (section_title, section_content) in enumerate(sections):
        if i > 0:
            html_parts.append(
                f'<div style="height: 1px; background: {C_BORDER}; margin: 20px 0;"></div>'
            )

        html_parts.append(
            f"""
            <div style="margin-bottom: 16px;">
                <div style="
                    color: {C_ACCENT};
                    font-weight: 600;
                    font-size: 14px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 12px;
                ">{section_title}</div>
                <div style="
                    color: {C_TEXT};
                    font-size: 13px;
                    line-height: 1.6;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                ">{section_content}</div>
            </div>
            """
        )

    html_parts.append("</div>")

    return "".join(html_parts)
