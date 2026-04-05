"""
Agent Orchestrator — coordinates parallel execution of all agents.

Flow:
1. Data agents run in parallel (Price, News, Fundamentals, Sentiment)
2. Results merged into unified data object
3. Analyst Agent processes combined data (sequential)
4. Advisor Agent generates insights (sequential)

Features:
- Parallel async execution of data agents
- Partial-data fallback (if one agent fails, others continue)
- Status tracking for UI display
- Integration with existing market_data.py as fallback
- Timeout handling per agent
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Agent timeout in seconds
AGENT_TIMEOUT = 45


class AgentOrchestrator:
    """Coordinates all TAM Capital research agents."""

    def __init__(self):
        self._agents = {}
        self._results = {}
        self._timings = {}
        self._initialized = False
        self._init_agents()

    def _init_agents(self):
        """Lazy-initialize available agents."""
        # Data collection agents
        agent_classes = {
            "price": ("data.agents.price_agent", "PriceAgent"),
            "news": ("data.agents.news_agent", "NewsAgent"),
            "fundamentals": ("data.agents.fundamentals_agent", "FundamentalsAgent"),
            "sentiment": ("data.agents.sentiment_agent", "SentimentAgent"),
        }

        for name, (module_path, class_name) in agent_classes.items():
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                self._agents[name] = cls()
                logger.info(f"Initialized {name} agent")
            except (ImportError, AttributeError) as e:
                logger.info(f"Agent {name} not yet implemented: {e}")
                self._agents[name] = None

        self._initialized = True

    async def run_data_agents(self, ticker: str, **kwargs) -> Dict[str, Any]:
        """
        Run all data collection agents in parallel.

        Returns dict with results from each agent:
        {
            "price": { ... } or None,
            "news": [ ... ] or None,
            "fundamentals": { ... } or None,
            "sentiment": { ... } or None,
            "metadata": { timings, statuses, errors }
        }
        """
        start = time.monotonic()
        results = {}
        tasks = {}

        # Launch all available agents in parallel
        for name, agent in self._agents.items():
            if agent is not None:
                tasks[name] = asyncio.create_task(
                    self._run_agent_with_timeout(agent, ticker, **kwargs)
                )

        # Wait for all tasks to complete
        if tasks:
            done, pending = await asyncio.wait(
                tasks.values(),
                timeout=AGENT_TIMEOUT + 5,
                return_when=asyncio.ALL_COMPLETED,
            )

            # Cancel any still-pending tasks
            for task in pending:
                task.cancel()

        # Collect results
        for name, task in tasks.items():
            try:
                if task.done() and not task.cancelled():
                    results[name] = task.result()
                else:
                    results[name] = None
                    logger.warning(f"Agent {name} timed out or was cancelled")
            except Exception as e:
                results[name] = None
                logger.error(f"Agent {name} failed: {e}")

        # Fill in None for agents that weren't available
        for name in self._agents:
            if name not in results:
                results[name] = None

        elapsed = time.monotonic() - start

        # Build metadata
        results["metadata"] = {
            "total_time_seconds": round(elapsed, 2),
            "timings": self._timings,
            "statuses": self.get_all_statuses(),
            "timestamp": datetime.now().isoformat(),
        }

        self._results = results
        return results

    async def _run_agent_with_timeout(self, agent, ticker: str, **kwargs) -> Optional[Dict]:
        """Run a single agent with timeout."""
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                agent.safe_fetch(ticker, **kwargs),
                timeout=AGENT_TIMEOUT,
            )
            self._timings[agent.name] = round(time.monotonic() - start, 2)
            return result
        except asyncio.TimeoutError:
            self._timings[agent.name] = AGENT_TIMEOUT
            agent.status = "failed"
            agent.last_error = f"Timeout after {AGENT_TIMEOUT}s"
            logger.error(f"Agent {agent.name} timed out after {AGENT_TIMEOUT}s")
            return None
        except Exception as e:
            self._timings[agent.name] = round(time.monotonic() - start, 2)
            agent.status = "failed"
            agent.last_error = str(e)
            logger.error(f"Agent {agent.name} error: {e}")
            return None

    def run_data_agents_sync(self, ticker: str, **kwargs) -> Dict[str, Any]:
        """Synchronous wrapper for run_data_agents."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.run_data_agents(ticker, **kwargs))
                return future.result(timeout=AGENT_TIMEOUT + 15)
        else:
            return asyncio.run(self.run_data_agents(ticker, **kwargs))

    def run_all_sync(self, ticker: str, **kwargs) -> Dict[str, Any]:
        """
        Run the complete pipeline: data agents → merge → return unified data.

        This is the main entry point for app.py integration.
        Returns data in a format compatible with the existing fetch_stock_data() schema.
        """
        raw = self.run_data_agents_sync(ticker, **kwargs)
        return self._merge_results(raw, ticker)

    def _merge_results(self, raw: Dict, ticker: str) -> Dict[str, Any]:
        """
        Merge data from all agents into a unified data object.

        The output format is compatible with the existing app.py pipeline:
        - stock_data dict (price, name, metrics)
        - news string
        - sentiment dict
        - metadata
        """
        merged = {
            "ticker": ticker,
            "source": "agent_orchestrator",
            "agents_used": [],
            "agents_failed": [],
        }

        # Price data
        price_data = raw.get("price")
        if price_data:
            merged.update(price_data)
            merged["agents_used"].append("price")
        else:
            merged["agents_failed"].append("price")

        # Fundamentals data
        fundamentals = raw.get("fundamentals")
        if fundamentals:
            # Merge without overwriting price data
            for key, val in fundamentals.items():
                if key not in merged or merged[key] is None:
                    merged[key] = val
            merged["agents_used"].append("fundamentals")
        else:
            merged["agents_failed"].append("fundamentals")

        # News data
        news = raw.get("news")
        if news:
            merged["news_items"] = news if isinstance(news, list) else [news]
            merged["agents_used"].append("news")
        else:
            merged["news_items"] = []
            merged["agents_failed"].append("news")

        # Sentiment data
        sentiment = raw.get("sentiment")
        if sentiment:
            merged["sentiment"] = sentiment
            merged["agents_used"].append("sentiment")
        else:
            merged["sentiment"] = None
            merged["agents_failed"].append("sentiment")

        # Metadata
        merged["metadata"] = raw.get("metadata", {})

        return merged

    # ---- Status & Display ----

    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get status of all agents for UI display."""
        statuses = {}
        for name, agent in self._agents.items():
            if agent is not None:
                statuses[name] = agent.get_status()
            else:
                statuses[name] = {
                    "name": name,
                    "status": "not_implemented",
                    "requests": 0,
                    "last_error": None,
                }
        return statuses

    def get_summary(self) -> str:
        """Get a human-readable summary of the last run."""
        if not self._results:
            return "No agents have been run yet."

        meta = self._results.get("metadata", {})
        statuses = meta.get("statuses", {})
        timings = meta.get("timings", {})

        lines = [f"Agent run completed in {meta.get('total_time_seconds', '?')}s:"]
        for name, status in statuses.items():
            s = status.get("status", "unknown")
            t = timings.get(name, "?")
            icon = {"complete": "OK", "cached": "CACHED", "failed": "FAIL", "not_implemented": "N/A"}.get(s, s)
            err = f" — {status.get('last_error', '')}" if s == "failed" else ""
            lines.append(f"  [{icon}] {name} ({t}s){err}")

        return "\n".join(lines)

    # ---- Fallback Integration ----

    def get_price_or_fallback(self, ticker: str) -> Optional[Dict]:
        """Get price data from agent results, or fall back to market_data.py."""
        if self._results.get("price"):
            return self._results["price"]

        # Fallback to existing market_data
        try:
            from data.market_data import fetch_stock_data
            logger.info(f"Price agent unavailable, falling back to market_data for {ticker}")
            return fetch_stock_data(ticker)
        except Exception as e:
            logger.error(f"Fallback fetch_stock_data also failed: {e}")
            return None

    def get_news_or_fallback(self, ticker: str, company_name: str = "") -> str:
        """Get news from agent results, or fall back to web_search."""
        news_items = self._results.get("news")
        if news_items and isinstance(news_items, list):
            # Format news items as a string for prompt injection
            lines = []
            for item in news_items[:10]:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('title', '')} ({item.get('source', '')}, {item.get('published_at', '')})")
                else:
                    lines.append(f"- {item}")
            return "\n".join(lines) if lines else ""

        # Fallback to existing web_search
        try:
            from data.web_search import search_company_news
            logger.info(f"News agent unavailable, falling back to web_search for {ticker}")
            return search_company_news(company_name or ticker, ticker)
        except Exception as e:
            logger.error(f"Fallback search_company_news also failed: {e}")
            return ""
