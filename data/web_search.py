"""Web search for recent news and events about a company."""

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
from data.source_collector import SourceCollector
from typing import Optional


def search_company_news(company_name: str, ticker: str = "",
                        max_results: int = 10,
                        collector: Optional[SourceCollector] = None) -> str:
    """Search for recent news about a company.

    Args:
        company_name: Company name to search
        ticker: Stock ticker symbol
        max_results: Max results per query
        collector: Optional SourceCollector to register found sources

    Returns:
        Formatted string of news results
    """
    queries = [
        f"{company_name} stock news 2026",
        f"{company_name} earnings analysis",
        f"{company_name} {ticker} investor",
    ]

    all_results = []
    seen_urls = set()

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = list(ddgs.text(query, max_results=max_results))
                for r in results:
                    url = r.get("href", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
            except Exception:
                continue

    if not all_results:
        return "No recent news found."

    lines = ["=== RECENT NEWS & ANALYSIS ===", ""]
    for i, r in enumerate(all_results[:15], 1):
        title = r.get("title", "N/A")
        body = r.get("body", "")[:200]
        source = r.get("href", "")

        lines.append(f"{i}. {title}")
        lines.append(f"   {body}")
        lines.append(f"   Source: {source}")
        lines.append("")

        # Register source
        if collector and source:
            collector.add(
                source_type="news_article",
                title=title,
                url=source,
                description=body[:100],
            )

    return "\n".join(lines)


def search_sector_news(sector: str, max_results: int = 5,
                       collector: Optional[SourceCollector] = None) -> str:
    """Search for sector-level news."""
    results = []
    with DDGS() as ddgs:
        try:
            results = list(ddgs.text(f"{sector} sector outlook 2026", max_results=max_results))
        except Exception:
            return "No sector news found."

    if not results:
        return "No sector news found."

    lines = ["=== SECTOR NEWS ===", ""]
    for i, r in enumerate(results, 1):
        title = r.get("title", "N/A")
        url = r.get("href", "")
        lines.append(f"{i}. {title}")
        lines.append(f"   {r.get('body', '')[:200]}")
        lines.append("")

        if collector and url:
            collector.add(
                source_type="sector_news",
                title=title,
                url=url,
            )

    return "\n".join(lines)
