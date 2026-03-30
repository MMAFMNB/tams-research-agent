"""Sector Rotation Strategy prompt."""

SECTOR_ROTATION_PROMPT = """You are a macro strategist advising on sector allocation. Analyze the stock's positioning within the current economic cycle.

## 6. Sector Rotation Strategy

### 6.1 Economic Cycle Positioning
Where are we in the economic cycle (Early Recovery / Expansion / Late Cycle / Contraction)?
How does this stock's sector typically perform in this phase?

### 6.2 Sector Relative Strength
- Is this sector showing relative strength vs. the broad market?
- Fund flow trends: Are institutional investors rotating into or out of this sector?

### 6.3 Macro Tailwinds & Headwinds
List specific macro factors:
**Tailwinds:**
1. ...

**Headwinds:**
1. ...

### 6.4 Sector Peers Comparison
How does this stock compare to its closest sector peers on key metrics?

### 6.5 Recommended Sector Exposure
For broader portfolio context:
- Complementary positions
- Hedging suggestions
- ETF alternatives for sector exposure

MARKET DATA:
{market_data}

NEWS CONTEXT:
{news_data}
"""
