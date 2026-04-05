# Dividend Analysis Skill

## Purpose
Generate income-focused dividend analysis covering yield, payout sustainability, and growth trajectory.

## Persona
Senior income-focused equity analyst.

## Prerequisites
- Dividend history and current yield
- Cash flow data (FCF coverage)
- Payout ratio trends

## Steps
1. Collect dividend data from Fundamentals Agent or yfinance
2. Apply prompt from `prompts/dividend_analyst.py` (DIVIDEND_ANALYSIS_PROMPT)
3. Call Claude (Sonnet)
4. Return structured markdown

## Sections Produced
2.1 Yield Analysis, 2.2 Payout Sustainability, 2.3 Dividend Growth, 2.4 Income Strategy

## Model Selection
- Default: claude-sonnet-4

## Data Sections Needed
CURRENT PRICE, DIVIDENDS, CASH FLOW, EARNINGS
