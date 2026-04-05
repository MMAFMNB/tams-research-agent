# Argaam Fundamentals Scraping Skill

## Purpose
Scrape company financial data from Argaam (argaam.com) — financials, ratios, company profiles.

## Data Source
- Primary: https://www.argaam.com/en/company/ pages
- Fallback: yfinance financials

## What to Scrape
- Company profile: sector, market cap, description
- Key ratios: P/E, P/B, EPS, dividend yield
- Income statement: revenue, net income, margins
- Balance sheet: assets, liabilities, equity
- Cash flow statement: operating CF, FCF

## Steps
1. Construct URL: `https://www.argaam.com/en/company/companyoverview/marketid/3/companyid/{company_id}`
2. Fetch page with `httpx` (use English version — better structured tables)
3. Parse financial tables with `BeautifulSoup4`
4. Normalize all values to SAR
5. Cache for 24 hours (fundamentals don't change intraday)

## Rate Limiting
- Max 15 requests/minute to Argaam
- Use 2-second delay between requests

## Output Schema
```python
{
    "ticker": "2222",
    "sector": "Energy",
    "market_cap": 7200000000000,
    "pe_ratio": 15.2, "pb_ratio": 2.1,
    "dividend_yield": 4.5, "eps": 1.89,
    "revenue": 1300000000000,
    "net_income": 450000000000,
    "source": "argaam_scrape"
}
```
