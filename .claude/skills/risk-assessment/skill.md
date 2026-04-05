# Risk Assessment Skill

## Purpose
Comprehensive risk framework covering financial, operational, market, and regulatory risks.

## Persona
Risk analyst at a major asset management firm.

## Prerequisites
- Balance sheet data (leverage, liquidity)
- Market data (beta, volatility)
- Sector context

## Steps
1. Collect risk-relevant data from all agents
2. Apply prompt from `prompts/risk_analyst.py` (RISK_ASSESSMENT_PROMPT)
3. Call Claude (Sonnet — nuance matters for risk)
4. Return structured markdown

## Sections Produced
4.1 Financial Risk, 4.2 Operational Risk, 4.3 Market Risk, 4.4 Regulatory Risk, 4.5 Risk Matrix

## Model Selection
- Default: claude-sonnet-4 (never downgrade risk assessment)

## Data Sections Needed
CURRENT PRICE, VALUATION, BALANCE SHEET, RISK METRICS
