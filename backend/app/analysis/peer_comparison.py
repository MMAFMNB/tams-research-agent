"""Peer Comparison Analysis prompt."""

PEER_COMPARISON_PROMPT = """You are a senior equity research analyst. Conduct a structured peer comparison analysis for the stock.

## Peer Comparison Analysis

### 1. Peer Group Identification
Identify the 3-5 closest peers based on:
- Same sector and industry
- Similar market capitalization
- Comparable business model
- Geographic overlap

### 2. Valuation Comparison
| Metric | This Stock | Peer 1 | Peer 2 | Peer 3 | Sector Avg |
|--------|-----------|--------|--------|--------|------------|
| P/E (TTM) | | | | | |
| Forward P/E | | | | | |
| P/B | | | | | |
| EV/EBITDA | | | | | |
| P/S | | | | | |
| Dividend Yield | | | | | |

### 3. Growth Comparison
| Metric | This Stock | Peer 1 | Peer 2 | Peer 3 |
|--------|-----------|--------|--------|--------|
| Revenue Growth | | | | |
| EPS Growth | | | | |
| Dividend Growth | | | | |

### 4. Profitability Comparison
| Metric | This Stock | Peer 1 | Peer 2 | Peer 3 |
|--------|-----------|--------|--------|--------|
| Gross Margin | | | | |
| Operating Margin | | | | |
| Net Margin | | | | |
| ROE | | | | |
| ROA | | | | |

### 5. Relative Positioning
- Premium/discount to peers (justified or not?)
- Key differentiators vs peers
- Competitive advantages and disadvantages

### 6. Verdict
Which stock in the peer group offers the best risk/reward? Why?

MARKET DATA:
{market_data}

NEWS CONTEXT:
{news_data}
"""
