# Technical Analysis Skill

## Purpose
Generate Morgan Stanley-style technical analysis with chart patterns, momentum signals, and entry/exit points.

## Persona
Chief technical strategist at Morgan Stanley.

## Prerequisites
- Price history (OHLCV data, minimum 200 days)
- Technical indicators (MAs, RSI, MACD, Bollinger Bands)

## Steps
1. Fetch price history: `data.market_data.fetch_price_history(ticker)` or Price Agent
2. Calculate technicals: `data.market_data.calculate_technical_indicators(hist)`
3. Apply prompt template from `prompts/technical_analyst.py` (TECHNICAL_ANALYSIS_PROMPT)
4. Call Claude with formatted data (use Sonnet)
5. Return structured markdown

## Sections Produced
5.1 Trend Analysis, 5.2 Support & Resistance, 5.3 Moving Averages, 5.4 Momentum Indicators, 5.5 Volume Analysis

## Model Selection
- Default: claude-sonnet-4
- Budget constrained: claude-haiku-3.5

## Data Sections Needed
CURRENT PRICE, TECHNICAL INDICATORS, RECENT PRICE ACTION
