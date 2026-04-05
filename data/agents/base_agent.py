"""
Base Agent class — foundation for all data collection and analysis agents.

Features:
- Async fetch with sync wrapper
- File-based caching with configurable TTL
- Rate limiting (token bucket)
- Retry with exponential backoff
- Output validation
- Integration with memory and cost systems
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "cache"


class BaseAgent:
    """Base class for all TAM Capital research agents."""

    name: str = "base"
    cache_ttl: int = 3600          # Default cache TTL in seconds (1 hour)
    rate_limit: float = 1.0        # Max requests per second
    max_retries: int = 3           # Number of retries on failure
    required_fields: List[str] = []  # Fields that must be present in output

    def __init__(self):
        self._last_request_time = 0.0
        self._request_count = 0
        self.status = "idle"       # idle, running, complete, failed, cached
        self.last_error: Optional[str] = None

    # ---- Public API ----

    async def fetch(self, ticker: str, **kwargs) -> Optional[Dict]:
        """
        Fetch data for a single ticker. Override in subclasses.

        Returns:
            Normalized data dict, or None on failure.
        """
        raise NotImplementedError(f"{self.name} must implement fetch()")

    async def fetch_batch(self, tickers: List[str], **kwargs) -> List[Optional[Dict]]:
        """Fetch data for multiple tickers sequentially with rate limiting."""
        results = []
        for ticker in tickers:
            result = await self.safe_fetch(ticker, **kwargs)
            results.append(result)
        return results

    async def safe_fetch(self, ticker: str, **kwargs) -> Optional[Dict]:
        """
        Fetch with caching, rate limiting, retries, and error handling.

        This is the primary entry point — wraps fetch() with all protections.
        """
        self.status = "running"
        self.last_error = None

        # Check cache first
        cache_key = self._make_cache_key(ticker, **kwargs)
        cached = self._read_cache(cache_key)
        if cached is not None:
            self.status = "cached"
            logger.info(f"[{self.name}] Cache hit for {ticker}")
            return cached

        # Retry loop
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                # Rate limit
                await self._wait_for_rate_limit()

                # Fetch
                result = await self.fetch(ticker, **kwargs)

                # Validate
                if result and self.validate_output(result):
                    # Cache the result
                    self._write_cache(cache_key, result)
                    self.status = "complete"
                    self._request_count += 1
                    return result
                else:
                    logger.warning(f"[{self.name}] Invalid output for {ticker} (attempt {attempt + 1})")

            except Exception as e:
                last_exception = e
                wait = min(2 ** attempt * 2, 30)
                logger.warning(
                    f"[{self.name}] Error fetching {ticker} (attempt {attempt + 1}/{self.max_retries}): "
                    f"{type(e).__name__}: {e}. Retrying in {wait}s"
                )
                await asyncio.sleep(wait)

        # All retries exhausted
        self.status = "failed"
        self.last_error = str(last_exception) if last_exception else "Unknown error"
        logger.error(f"[{self.name}] Failed to fetch {ticker} after {self.max_retries} retries")
        return None

    def fetch_sync(self, ticker: str, **kwargs) -> Optional[Dict]:
        """Synchronous wrapper for fetch. Uses existing event loop if available."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an async context (e.g., Streamlit) — create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.safe_fetch(ticker, **kwargs))
                return future.result(timeout=60)
        else:
            return asyncio.run(self.safe_fetch(ticker, **kwargs))

    def validate_output(self, data: Dict) -> bool:
        """Validate that output contains all required fields."""
        if not isinstance(data, dict):
            return False
        for field in self.required_fields:
            if field not in data:
                logger.warning(f"[{self.name}] Missing required field: {field}")
                return False
        return True

    def get_status(self) -> Dict:
        """Get agent status for UI display."""
        return {
            "name": self.name,
            "status": self.status,
            "requests": self._request_count,
            "last_error": self.last_error,
        }

    # ---- Rate Limiting ----

    async def _wait_for_rate_limit(self):
        """Token bucket rate limiter."""
        if self.rate_limit <= 0:
            return
        min_interval = 1.0 / self.rate_limit
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            wait = min_interval - elapsed
            logger.debug(f"[{self.name}] Rate limit: waiting {wait:.2f}s")
            await asyncio.sleep(wait)
        self._last_request_time = time.monotonic()

    # ---- Caching ----

    def _make_cache_key(self, ticker: str, **kwargs) -> str:
        """Generate a cache key from ticker and parameters."""
        date = datetime.now().strftime("%Y%m%d")
        extra = hashlib.md5(json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()[:6]
        return f"{self.name}_{ticker}_{date}_{extra}"

    def _read_cache(self, key: str) -> Optional[Dict]:
        """Read from file-based cache."""
        path = CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
            # Check TTL
            cached_at = datetime.fromisoformat(entry.get("_cached_at", "2000-01-01"))
            age_seconds = (datetime.now() - cached_at).total_seconds()
            if age_seconds > self.cache_ttl:
                return None
            return entry.get("data")
        except Exception as e:
            logger.debug(f"[{self.name}] Cache read error: {e}")
            return None

    def _write_cache(self, key: str, data: Dict):
        """Write to file-based cache."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / f"{key}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "data": data,
                    "_cached_at": datetime.now().isoformat(),
                    "_agent": self.name,
                    "_key": key,
                }, f, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"[{self.name}] Cache write error: {e}")

    def clear_cache(self, ticker: Optional[str] = None):
        """Clear cached data. If ticker given, only clear that ticker's cache."""
        if not CACHE_DIR.exists():
            return
        pattern = f"{self.name}_{ticker}_*" if ticker else f"{self.name}_*"
        for path in CACHE_DIR.glob(f"{pattern}.json"):
            path.unlink(missing_ok=True)
            logger.info(f"[{self.name}] Cleared cache: {path.name}")
