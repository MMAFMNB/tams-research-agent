# Tadawul Price Scraping Skill

## Purpose
Scrape stock prices from the official Saudi Exchange (saudiexchange.sa) website.

## Data Source
- Primary: https://www.saudiexchange.sa (official Tadawul)
- Fallback: yfinance with `.SR` suffix (e.g., `2222.SR` for Aramco)

## Scraping Approach
1. Use `httpx` async client with browser-like headers
2. Target the market watch page for real-time quotes
3. Target individual stock pages for historical data
4. Parse HTML with `BeautifulSoup4`
5. Handle Arabic text in stock names (UTF-8)

## Rate Limiting
- Max 1 request per 2 seconds to Tadawul
- Rotate User-Agent strings
- Respect robots.txt

## Caching
- Real-time quotes: cache 5 minutes
- Historical daily data: cache 24 hours
- Use file-based cache in `data/cache/`

## Output Schema
```python
{
    "ticker": "2222",
    "name": "Saudi Aramco",
    "open": 28.50, "high": 28.90, "low": 28.30, "close": 28.75,
    "volume": 12500000,
    "change_pct": 1.2,
    "source": "tadawul_scrape"
}
```

## Error Handling
- Tadawul down: fall back to yfinance
- Rate limited: exponential backoff (2s, 4s, 8s)
- Parse failure: log error, return None, try yfinance
