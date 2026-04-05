Analyze a Tadawul stock: $ARGUMENTS

Steps:

1. Parse the ticker from $ARGUMENTS (e.g., "2222" or "Aramco")
2. Look up the ticker in config.py TADAWUL_TICKERS mapping
3. Run the agent orchestrator: `from data.agents.orchestrator import AgentOrchestrator`
4. If agents aren't ready yet, fall back to `data.market_data.fetch_stock_data(ticker)`
5. Run all 8 analysis sections using the skills in `.claude/skills/`
6. Follow the cost-optimization skill for model routing
7. Compile the report using the report-compilation skill
8. Check memory.md for any user preferences or ticker-specific context
9. Present the executive summary and ask if the user wants a full export (PDF/DOCX/PPTX)
