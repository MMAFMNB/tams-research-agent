# News Impact Skill

## Purpose
Assess the impact of recent news and events on a stock's price and fundamentals.

## Persona
News impact analyst at a major investment bank.

## Steps
1. Gather news from News Agent (Argaam RSS + articles) or `data.web_search`
2. Apply prompt from `prompts/news_impact.py` (NEWS_IMPACT_PROMPT)
3. Call Claude (Haiku is sufficient — extractive task)

## Sections Produced
Part II: Recent News Impact Assessment

## Model Selection
- Default: claude-haiku-3.5 (extractive summarization)
- Complex geopolitical news: upgrade to Sonnet

## Data Sections Needed
NEWS DATA (full), CURRENT PRICE
