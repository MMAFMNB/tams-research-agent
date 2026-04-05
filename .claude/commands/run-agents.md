Run the multi-agent data collection pipeline: $ARGUMENTS

Steps:

1. Parse ticker from $ARGUMENTS (e.g., "2222")
2. Import and initialize the AgentOrchestrator: `from data.agents.orchestrator import AgentOrchestrator`
3. Run all data agents in parallel (Price, News, Fundamentals, Sentiment)
4. Display status of each agent (running/complete/failed/cached)
5. Show collected data summary for each agent
6. If any agent failed, note the fallback used
7. Ask if the user wants to proceed with analysis (runs Analyst + Advisor agents)
