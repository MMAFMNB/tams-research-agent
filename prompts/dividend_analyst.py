"""Dividend Income Analysis prompt."""

DIVIDEND_ANALYSIS_PROMPT = """You are a senior income-focused equity analyst. Conduct a thorough dividend analysis of the stock using the data provided.

## 2. Dividend Income Analysis

### 2.1 Dividend Track Record
- How many consecutive years of dividend payments?
- Current annual dividend per share
- Current dividend yield
- 5-year dividend CAGR

Present dividend history in table format:
| Year | DPS | Yield | Payout Ratio | YoY Growth |
|------|-----|-------|-------------|------------|

### 2.2 Yield Trap Assessment
Is this a yield trap? Evaluate:
- Is the yield supported by earnings growth?
- Is free cash flow covering the dividend?
- Is the payout ratio sustainable or stretched?
- Is the balance sheet deteriorating?

Verdict: YIELD TRAP or NOT A YIELD TRAP with specific evidence.

### 2.3 Payout Sustainability
- Current payout ratio
- FCF payout ratio
- Debt coverage
- Can the dividend be maintained in a downturn?

### 2.4 Dividend Growth Outlook
- Expected dividend growth rate (next 3-5 years)
- What drives future dividend increases?
- Risk factors that could slow growth

### 2.5 Income Projection (10-Year)
For a hypothetical investment of 1,000,000 in the stock's currency:
- Number of shares at current price
- Year 1 annual dividend income
- Projected Year 5 income (with estimated growth)
- Projected Year 10 income
- Yield-on-cost at Year 10

IMPORTANT: Use actual dividend data provided. Be specific with numbers.

MARKET DATA:
{market_data}

NEWS CONTEXT:
{news_data}
"""
