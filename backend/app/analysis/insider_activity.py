"""Insider Activity Analysis prompt."""

INSIDER_ACTIVITY_PROMPT = """You are an analyst specializing in insider transaction analysis and ownership patterns. Analyze the ownership structure and insider activity for this stock.

## Insider Activity Analysis

### 1. Ownership Structure
| Owner Type | Percentage | Key Holders |
|-----------|-----------|-------------|
| Government/Sovereign | | |
| Institutional | | |
| Insider/Management | | |
| Public Float | | |

### 2. Major Shareholders
List the top 5 shareholders with their percentage ownership and any recent changes.

### 3. Recent Insider Transactions
| Date | Insider | Position | Transaction | Shares | Value |
|------|---------|----------|-------------|--------|-------|

### 4. Insider Sentiment Analysis
- Net buying vs selling trend (last 6 months)
- Are insiders buying at current valuations?
- Any unusual patterns or cluster buying/selling?

### 5. Institutional Flow
- Are institutional investors increasing or decreasing positions?
- Any notable fund entries or exits?
- ETF inclusion/exclusion impacts

### 6. Ownership Signal
- Bullish, Bearish, or Neutral based on ownership patterns
- Key takeaway for investors

MARKET DATA:
{market_data}

NEWS CONTEXT:
{news_data}
"""
