"""Redis-based caching layer for market data."""

import json
import redis
from typing import Optional
from app.config import get_settings

settings = get_settings()


class DataCache:
    """Cache market data in Redis with configurable TTL."""

    def __init__(self):
        try:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis.ping()
            self._available = True
        except Exception:
            self._available = False

    def get(self, key: str) -> Optional[dict]:
        if not self._available:
            return None
        try:
            data = self._redis.get(f"tam:cache:{key}")
            return json.loads(data) if data else None
        except Exception:
            return None

    def set(self, key: str, value: dict, ttl: int = None):
        if not self._available:
            return
        try:
            self._redis.setex(
                f"tam:cache:{key}",
                ttl or settings.REDIS_CACHE_TTL,
                json.dumps(value, default=str),
            )
        except Exception:
            pass

    def delete(self, key: str):
        if not self._available:
            return
        try:
            self._redis.delete(f"tam:cache:{key}")
        except Exception:
            pass


_cache = None

def get_cache() -> DataCache:
    global _cache
    if _cache is None:
        _cache = DataCache()
    return _cache
