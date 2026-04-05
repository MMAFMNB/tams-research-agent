Generate the TAM Capital morning brief.

Steps:

1. Load the user's watchlist from `data.watchlist.load_watchlist()`
2. For each ticker, fetch current price data (Price Agent or market_data)
3. Gather top news from News Agent or web_search
4. Gather sentiment snapshot from Sentiment Agent if available
5. Follow the morning-brief skill in `.claude/skills/morning-brief/skill.md`
6. Use claude-haiku-3.5 for cost efficiency (per cost-optimization skill)
7. Format with TAM Capital branding (colors from config.py)
8. Present the brief and ask if the user wants it emailed or exported
