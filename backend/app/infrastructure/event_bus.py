"""Event Bus — Production adapter.

In-memory for dev/test. Redis-backed for production.
Events are persisted to survive restarts.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import AsyncIterator

from app.domain.ports import EventBus


class InMemoryEventBus(EventBus):
    """In-memory event bus — loses events on restart. Use for dev/test only."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []
        self._subscribers: dict[str, list] = defaultdict(list)

    async def publish(self, event_type: str, payload: dict) -> None:
        self.published.append((event_type, payload))
        for callback in self._subscribers.get(event_type, []):
            await callback(payload)

    async def subscribe(self, event_type: str) -> AsyncIterator[dict]:
        queue: list[dict] = []
        self._subscribers[event_type].append(queue.append)
        try:
            while True:
                if queue:
                    yield queue.pop(0)
                else:
                    await self._sleep(0.1)
        except GeneratorExit:
            self._subscribers[event_type].remove(queue.append)

    async def _sleep(self, seconds: float) -> None:
        import asyncio
        await asyncio.sleep(seconds)


class RedisEventBus(EventBus):
    """Redis-backed event bus — persists events across restarts.

    Uses Redis Pub/Sub for real-time delivery and Redis List for persistence.
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

    async def publish(self, event_type: str, payload: dict) -> None:
        r = await self._get_redis()

        event = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        }

        # Persist to list (survives restarts)
        await r.rpush(f"aerogrid:events:{event_type}", json.dumps(event))
        await r.expire(f"aerogrid:events:{event_type}", 86400)  # 24h TTL

        # Publish to channel (real-time delivery)
        await r.publish(f"aerogrid:channel:{event_type}", json.dumps(event))

    async def subscribe(self, event_type: str) -> AsyncIterator[dict]:
        r = await self._get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"aerogrid:channel:{event_type}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(f"aerogrid:channel:{event_type}")

    async def get_history(self, event_type: str, limit: int = 100) -> list[dict]:
        """Get persisted event history for debugging/audit."""
        r = await self._get_redis()
        events = await r.lrange(f"aerogrid:events:{event_type}", 0, limit - 1)
        return [json.loads(e) for e in events]
