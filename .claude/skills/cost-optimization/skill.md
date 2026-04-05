# Cost Optimization Skill

## Purpose
Minimize API spend while maintaining analysis quality through intelligent model routing, prompt truncation, and response caching.

## Model Routing Rules

| Task Type | Default Model | Rationale |
|-----------|--------------|-----------|
| Morning brief | Haiku | Formulaic, extractive |
| News summary | Haiku | Extractive summarization |
| Sentiment classification | Haiku | Simple classification |
| News impact | Haiku | Event-driven, lighter analysis |
| Fundamental analysis | Sonnet | Deep reasoning required |
| Technical analysis | Sonnet | Pattern recognition |
| Earnings analysis | Sonnet | Nuanced interpretation |
| Dividend analysis | Sonnet | Payout sustainability reasoning |
| Risk assessment | Sonnet | Never downgrade risk analysis |
| War/geopolitical impact | Sonnet | Geopolitical nuance |
| Sector rotation | Sonnet | Macro reasoning |
| Executive summary | Sonnet | CIO-level synthesis |

## Budget Override Rules
- If < $5 remaining this month: downgrade ALL tasks to Haiku
- If < $10 remaining: downgrade morning briefs and news to Haiku (keep analysis on Sonnet)
- If prompt > 50k characters and task is Sonnet-tier: consider Haiku

## Prompt Truncation Rules
Each analysis type only needs specific data sections. Trim irrelevant sections before sending to Claude:
- Fundamental: keep financials, valuation, business summary — trim technical indicators
- Technical: keep price history, indicators — trim financial statements
- Dividend: keep dividend data, cash flow — trim everything else
- This reduces prompt tokens by 30-50%

## Caching Strategy
- Same ticker + same analysis type + same day = return cached response
- Cache key format: `{ticker}_{action}_{YYYYMMDD}`
- Cache TTL: 12 hours for analysis, 5 minutes for real-time data
- Store in `data/cache/` as JSON files

## Cost Tracking
- All API calls tracked via `data/token_tracker.py`
- Extended with `agent_name` field to track per-agent costs
- Extended with `cached` boolean to measure cache hit rate
- Monthly dashboard in sidebar shows remaining budget
