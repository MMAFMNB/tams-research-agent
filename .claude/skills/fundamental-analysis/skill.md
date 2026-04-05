# Fundamental Analysis Skill

## Purpose
Generate Goldman Sachs-style fundamental analysis for a Tadawul stock.

## Persona
Senior fundamental analyst at a top-tier investment bank.

## Prerequisites
- Market data dict (current price, valuation multiples, financials)
- 5-year financial statements
- News context string

## Steps
1. Collect market data: `data.market_data.fetch_stock_data(ticker)` or Price Agent output
2. Collect financials: `data.market_data.fetch_financials(ticker)` or Fundamentals Agent output
3. Format data: `data.market_data.format_market_data_for_prompt(data, technicals, hist, financials)`
4. Apply prompt template from `prompts/fundamental_analyst.py` (FUNDAMENTAL_ANALYSIS_PROMPT)
5. Call Claude with formatted prompt (use Sonnet — deep analysis requires nuance)
6. Return structured markdown with ## headers

## Sections Produced
1.1 Business Model, 1.2 Revenue Sources, 1.3 Profitability Analysis, 1.4 Balance Sheet Strength, 1.5 Free Cash Flow, 1.6 Competitive Advantages

## Model Selection
- Default: claude-sonnet-4 (deep analysis)
- Budget constrained: claude-haiku-3.5 (acceptable quality loss)

## Data Sections Needed (for prompt truncation)
CURRENT PRICE, VALUATION, EARNINGS, PROFITABILITY, BALANCE SHEET, CASH FLOW, BUSINESS SUMMARY, FINANCIAL STATEMENTS

## Error Handling
- Missing financials: proceed with available data, note gaps in output
- Claude rate limited: fall back to FALLBACK_MODEL
