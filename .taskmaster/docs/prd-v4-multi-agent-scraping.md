# PRD v4: Multi-Agent Saudi Market Research Platform

## Overview

Replace the broken RapidAPI dependency with a **web scraping-first architecture** powered by specialized agents. Each agent handles a specific data domain (prices, fundamentals, news, sentiment), feeding into an analysis pipeline that produces autonomous investment insights.

## Problem Statement

- The RapidAPI Saudi Exchange endpoint is down/unreliable (404 errors)
- yfinance has rate limits and incomplete Tadawul coverage
- No community sentiment analysis exists in the current platform
- The current pipeline is single-threaded and fragile — one source failure blocks everything

## Architecture

### Agent Hierarchy

```
[Price Agent] ──┐
[Fundamentals Agent] ──┤
[News Agent] ──────────┼──> [Analyst Agent] ──> [Advisor Agent] ──> Reports/Alerts
[Sentiment Agent] ─────┘
```

### Data Flow

1. **Data Agents** (parallel) scrape and normalize data into a common schema
2. **Analyst Agent** consumes all normalized data, runs technical + fundamental analysis
3. **Advisor Agent** generates investment insights, reports, and alerts

---

## Agent Specifications

### Agent 1: Price Agent (`data/agents/price_agent.py`)

**Responsibility:** Historical OHLCV prices and real-time quotes for Tadawul stocks.

**Data Sources (in priority order):**
1. **saudiexchange.sa** — Official Tadawul market watch page (primary)
   - Scrape the main market watch table for real-time quotes
   - Scrape individual stock pages for historical daily data
2. **yfinance** — Fallback for historical data using `.SR` suffix (e.g., `2222.SR` for Aramco)

**Output Schema:**
```python
{
    "ticker": "2222",
    "name": "Saudi Aramco",
    "timestamp": "2025-04-01T10:30:00",
    "open": 28.50,
    "high": 28.90,
    "low": 28.30,
    "close": 28.75,
    "volume": 12500000,
    "change_pct": 1.2,
    "source": "tadawul_scrape"
}
```

**Technical Requirements:**
- Use `httpx` + `BeautifulSoup4` for scraping (or `playwright` if JS-rendered)
- Implement request throttling: max 1 request per 2 seconds to Tadawul
- Cache responses for 5 minutes (real-time) and 24 hours (historical)
- Handle Arabic text in stock names
- Retry logic with exponential backoff

### Agent 2: Fundamentals Agent (`data/agents/fundamentals_agent.py`)

**Responsibility:** Financial statements, ratios, company profiles.

**Data Sources:**
1. **argaam.com** — Primary source for Saudi company financials
   - Company profile pages: revenue, net income, EPS, P/E, P/B, dividend yield
   - Financial statements: income statement, balance sheet, cash flow
   - Key ratios and metrics
2. **yfinance** — Fallback for basic financials

**Output Schema:**
```python
{
    "ticker": "2222",
    "name": "Saudi Aramco",
    "sector": "Energy",
    "market_cap": 7200000000000,
    "pe_ratio": 15.2,
    "pb_ratio": 2.1,
    "dividend_yield": 4.5,
    "eps": 1.89,
    "revenue": 1300000000000,
    "net_income": 450000000000,
    "financials": { ... },
    "source": "argaam_scrape",
    "fetched_at": "2025-04-01T12:00:00"
}
```

**Technical Requirements:**
- Scrape Argaam company pages (both Arabic and English versions)
- Parse financial tables into structured data
- Normalize currency values (SAR)
- Cache for 24 hours (fundamentals don't change intraday)

### Agent 3: News Agent (`data/agents/news_agent.py`)

**Responsibility:** Market news, analyst opinions, sector updates.

**Data Sources:**
1. **argaam.com/en/articles** — News articles and market updates
2. **argaam.com RSS feeds** — Already planned in PRD v3 (use `feedparser`)
3. **saudiexchange.sa announcements** — Company disclosures and regulatory filings

**Output Schema:**
```python
{
    "title": "Aramco announces Q3 dividend",
    "source": "argaam",
    "url": "https://argaam.com/...",
    "published_at": "2025-04-01T08:00:00",
    "tickers_mentioned": ["2222"],
    "category": "dividend",
    "summary": "...",
    "sentiment_score": 0.7  # -1 to 1
}
```

**Technical Requirements:**
- Parse RSS feeds with `feedparser`
- Scrape article pages for full text when needed
- Use Claude to classify news sentiment and extract mentioned tickers
- Deduplicate across sources
- Cache articles permanently (news doesn't change)

### Agent 4: Sentiment Agent (`data/agents/sentiment_agent.py`)

**Responsibility:** Community and social media sentiment around Saudi stocks.

**Data Sources:**
1. **argaam.com community/forums** — User discussions, comments on stocks
2. **X/Twitter** — Arabic hashtags: #تاسي, #تداول, #السوق_السعودي, plus stock-specific tags
3. **StockTwits or similar** — If available for Saudi stocks

**Output Schema:**
```python
{
    "ticker": "2222",
    "period": "24h",
    "overall_sentiment": 0.3,  # -1 (bearish) to 1 (bullish)
    "volume_mentions": 45,
    "top_themes": ["dividend", "oil_prices", "expansion"],
    "bullish_pct": 65,
    "bearish_pct": 25,
    "neutral_pct": 10,
    "sample_comments": [...],
    "source_breakdown": {
        "argaam_forums": {"count": 20, "avg_sentiment": 0.4},
        "twitter": {"count": 25, "avg_sentiment": 0.2}
    }
}
```

**Technical Requirements:**
- Scrape Argaam forum/community pages for stock discussions
- Use `httpx` for X/Twitter scraping (or a library like `snscrape` if available)
- Use Claude to analyze sentiment of Arabic text
- Aggregate sentiment over configurable time windows (1h, 24h, 7d)
- Rate limit aggressively — social platforms are strict

### Agent 5: Analyst Agent (`data/agents/analyst_agent.py`)

**Responsibility:** Consume all data from agents 1-4, run analysis, produce structured insights.

**Capabilities:**
- **Technical Analysis:** Moving averages, RSI, MACD, support/resistance from Price Agent data
- **Fundamental Analysis:** Valuation metrics, peer comparison from Fundamentals Agent
- **News Impact Assessment:** Correlate news events with price movements
- **Sentiment Overlay:** Combine community sentiment with technical/fundamental signals
- **Sector Analysis:** Aggregate metrics across sector peers

**Output:** Structured analysis object consumed by the Advisor Agent and the existing report generators.

**Technical Requirements:**
- Orchestrate parallel data fetching from all 4 data agents
- Use `asyncio` for concurrent agent execution
- Merge and cross-reference data from all sources
- Feed combined context to Claude for AI-powered analysis (reuse existing `prompts/` templates)
- Timeout handling: if one agent fails, proceed with partial data

### Agent 6: Advisor Agent (`data/agents/advisor_agent.py`)

**Responsibility:** Generate actionable investment insights and reports.

**Capabilities:**
- **Stock Recommendations:** Buy/hold/sell signals with confidence scores
- **Morning Brief:** Daily market summary combining all data sources
- **Alert Generation:** Trigger alerts based on combined signals (price + sentiment + news)
- **Report Generation:** Feed structured insights to existing DOCX/PDF/PPTX generators
- **Portfolio Impact:** Assess how new data affects current watchlist/portfolio

**Technical Requirements:**
- Use Claude to generate natural language insights from Analyst Agent output
- Integrate with existing `generators/` for report output
- Integrate with existing `data/alert_engine.py` for alerts
- Support both English and Arabic output

---

## Shared Infrastructure

### Agent Base Class (`data/agents/base_agent.py`)

All agents inherit from a common base:

```python
class BaseAgent:
    name: str
    cache_ttl: int  # seconds
    rate_limit: float  # requests per second
    
    async def fetch(self, ticker: str, **kwargs) -> dict
    async def fetch_batch(self, tickers: list, **kwargs) -> list
    def validate_output(self, data: dict) -> bool
    def get_cached(self, key: str) -> Optional[dict]
    def set_cached(self, key: str, data: dict) -> None
```

### Scraping Utilities (`data/agents/scraper_utils.py`)

Shared scraping helpers:
- Request session management with rotating headers
- User-Agent rotation
- Proxy support (optional)
- HTML parsing helpers for Arabic content
- Rate limiter (token bucket)
- Retry with exponential backoff
- Response caching (file-based or Redis)

### Agent Orchestrator (`data/agents/orchestrator.py`)

Coordinates all agents:
- Parallel execution of data agents
- Sequential execution of Analyst -> Advisor
- Error handling and partial-data fallback
- Logging and performance metrics
- Integration point for the Streamlit app (`app.py`)

---

## Integration with Existing App

### Changes to `app.py`
- Replace direct `market_data.py` calls with orchestrator
- Add "Agent Status" panel showing which agents are active/cached/failed
- Add "Community Sentiment" tab in stock analysis view

### Changes to `data/market_data.py`
- Refactor to use Price Agent as primary source
- Keep as a compatibility layer that delegates to agents

### Changes to `config.py`
- Add scraping configuration (rate limits, cache TTLs, user agents)
- Add agent-specific settings

### New Dependencies
- `httpx` — Async HTTP client for scraping
- `beautifulsoup4` — HTML parsing (likely already installed)
- `playwright` — For JS-rendered pages (optional, only if needed)
- `feedparser` — RSS parsing (already planned in PRD v3)
- `cachetools` — In-memory caching for agents

---

## Implementation Priority

1. **Phase 1 — Foundation:** Base agent class, scraper utils, orchestrator skeleton
2. **Phase 2 — Price Agent:** Tadawul scraping + yfinance fallback (replaces broken RapidAPI)
3. **Phase 3 — News Agent:** Argaam RSS + article scraping (builds on PRD v3 work)
4. **Phase 4 — Fundamentals Agent:** Argaam company page scraping
5. **Phase 5 — Sentiment Agent:** Argaam forums + X/Twitter
6. **Phase 6 — Analyst Agent:** Data fusion and analysis logic
7. **Phase 7 — Advisor Agent:** Insights generation and report integration
8. **Phase 8 — App Integration:** Wire agents into Streamlit UI, add agent status panel

---

## Success Criteria

- All 6 agents operational and producing valid output
- Scraping works without API keys (except Claude for AI analysis)
- Graceful degradation: if one agent fails, others continue
- End-to-end: from scraping to generated report in under 60 seconds
- Community sentiment visible in stock analysis view
- Existing report generators work with new agent data
