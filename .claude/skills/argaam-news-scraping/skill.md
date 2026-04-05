# Argaam News Scraping Skill

## Purpose
Collect market news from Argaam (argaam.com) via RSS feeds and article scraping.

## Data Sources
1. Argaam RSS feeds (free, no API key) — use `feedparser` library
2. Argaam article pages — scrape for full text when needed
3. Saudi Exchange announcements — company disclosures

## RSS Feed URLs
- Main news: https://www.argaam.com/en/rss/articles
- Saudi market: https://www.argaam.com/en/rss/articles-category/30

## Steps
1. Parse RSS feeds with `feedparser`
2. Extract: title, URL, published date, summary
3. For detailed analysis: scrape full article text with `httpx` + `BeautifulSoup4`
4. Use Claude (Haiku) to: classify sentiment (-1 to 1), extract mentioned tickers, categorize
5. Deduplicate across sources (by URL or title similarity)

## Rate Limiting
- Max 15 requests/minute to Argaam
- Cache articles permanently (news doesn't change)

## Output Schema
```python
{
    "title": "Aramco announces Q3 dividend",
    "source": "argaam",
    "url": "https://argaam.com/...",
    "published_at": "2025-04-01T08:00:00",
    "tickers_mentioned": ["2222"],
    "category": "dividend",
    "sentiment_score": 0.7
}
```
