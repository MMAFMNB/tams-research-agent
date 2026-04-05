# Morning Brief Skill

## Purpose
Generate a concise daily market briefing for TAM Capital analysts covering watchlist movers, market context, news highlights, and AI insights.

## Persona
Senior analyst at TAM Capital.

## Full Workflow
1. Fetch watchlist from `data.watchlist.load_watchlist()`
2. For each ticker: get current price from Price Agent or market_data
3. Gather top news from News Agent or `data.web_search`
4. Gather sentiment snapshot from Sentiment Agent
5. Format using `prompts/morning_brief.py` (MORNING_BRIEF_PROMPT)
6. Call Claude with Haiku (morning brief is formulaic)
7. Render with TAM Capital styling (colors from `config.py`)

## Model Selection
- Default: claude-haiku-3.5 (cost efficient for daily runs)
- Weekend deep dive: claude-sonnet-4

## Scheduling
- Run daily at 7:00 AM Riyadh time (AST, UTC+3)
- Skip weekends (Tadawul closed Fri-Sat)
- Trading hours: Sun-Thu 10:00-15:00 AST

## Data Sections Needed
WATCHLIST DATA, NEWS DATA, CURRENT PRICES
