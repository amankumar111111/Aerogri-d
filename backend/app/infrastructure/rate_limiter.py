"""Rate Limiter — Production adapter.

Token bucket algorithm with sliding window counter.
Redis-backed for distributed rate limiting across instances.
Falls back to in-memory for local development.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from app.domain.ports import RateLimiter


class InMemoryRateLimiter(RateLimiter):
    """In-memory rate limiter — single instance only. Use for dev/test."""

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        now = time.monotonic()
        cutoff = now - window_seconds

        # Remove expired entries
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]

        if len(self._buckets[key]) >= limit:
            return False

        self._buckets[key].append(now)
        return True

    async def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        now = time.monotonic()
        cutoff = now - window_seconds
        current = len([t for t in self._buckets[key] if t > cutoff])
        return max(0, limit - current)

    async def reset(self, key: str) -> None:
        self._buckets.pop(key, None)


class RedisRateLimiter(RateLimiter):
    """Redis-backed rate limiter — works across multiple instances.

    Uses sliding window counter with Redis sorted sets.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(
                    self.redis_url, decode_responses=True
                )
            except ImportError:
                raise RuntimeError("redis package required: pip install redis")
        return self._redis

    async def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Sliding window rate limit using Redis sorted sets."""
        r = await self._get_redis()
        now = time.time()
        window_key = f"ratelimit:{key}"

        pipe = r.pipeline()
        # Remove expired entries
        pipe.zremrangebyscore(window_key, 0, now - window_seconds)
        # Count current entries
        pipe.zcard(window_key)
        # Add current request
        pipe.zadd(window_key, {str(now): now})
        # Set expiry
        pipe.expire(window_key, window_seconds)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= limit:
            # Remove the entry we just added (request denied)
            await r.zrem(window_key, str(now))
            return False

        return True

    async def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        r = await self._get_redis()
        now = time.time()
        window_key = f"ratelimit:{key}"
        await r.zremrangebyscore(window_key, 0, now - window_seconds)
        current = await r.zcard(window_key)
        return max(0, limit - current)

    async def reset(self, key: str) -> None:
        r = await self._get_redis()
        await r.delete(f"ratelimit:{key}")
