"""Idempotency Store — Prevents duplicate submissions.

Uses fingerprint + device_id as natural idempotency key.
Also supports explicit Idempotency-Key header.
"""

from __future__ import annotations

import time
from typing import Optional

from app.domain.ports import IdempotencyStore


class InMemoryIdempotencyStore(IdempotencyStore):
    """In-memory idempotency store — single instance only."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    async def check_and_set(self, key: str, response: str, ttl_seconds: int = 300) -> str | None:
        """Check if key exists. If not, store it. Returns existing response or None."""
        now = time.monotonic()

        # Clean expired entries
        expired = [k for k, (_, t) in self._store.items() if now - t > ttl_seconds]
        for k in expired:
            del self._store[k]

        if key in self._store:
            existing_response, _ = self._store[key]
            return existing_response

        self._store[key] = (response, now)
        return None

    async def exists(self, key: str) -> bool:
        now = time.monotonic()
        if key in self._store:
            _, t = self._store[key]
            if now - t <= 300:
                return True
            del self._store[key]
        return False

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
