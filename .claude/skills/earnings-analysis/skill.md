# Earnings Analysis Skill

## Purpose
Generate JPMorgan-style earnings analysis covering EPS trends, guidance, and beat/miss history.

## Persona
Senior earnings analyst at JPMorgan.

## Prerequisites
- Earnings history (quarterly EPS, revenue beats/misses)
- Financial statements (income statement)
- Analyst consensus estimates if available

## Steps
1. Collect earnings data from Fundamentals Agent or yfinance
2. Apply prompt from `prompts/earnings_analyst.py` (EARNINGS_ANALYSIS_PROMPT)
3. Call Claude (Sonnet)
4. Return structured markdown

## Sections Produced
3.1 Earnings History, 3.2 Revenue Analysis, 3.3 Guidance Assessment

## Model Selection
- Default: claude-sonnet-4

## Data Sections Needed
CURRENT PRICE, EARNINGS, PROFITABILITY, FINANCIAL STATEMENTS
