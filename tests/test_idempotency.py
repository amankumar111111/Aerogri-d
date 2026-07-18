"""Tests for IdempotencyStore."""

from __future__ import annotations

import pytest
from app.infrastructure.idempotency import InMemoryIdempotencyStore


class TestInMemoryIdempotencyStore:
    @pytest.mark.asyncio
    async def test_first_call_stores_and_returns_none(self):
        store = InMemoryIdempotencyStore()
        result = await store.check_and_set("key-1", '{"id": "obs-1"}')
        assert result is None

    @pytest.mark.asyncio
    async def test_second_call_returns_existing(self):
        store = InMemoryIdempotencyStore()
        await store.check_and_set("key-1", '{"id": "obs-1"}')
        result = await store.check_and_set("key-1", '{"id": "obs-1-dup"}')
        assert result == '{"id": "obs-1"}'

    @pytest.mark.asyncio
    async def test_different_keys_independent(self):
        store = InMemoryIdempotencyStore()
        await store.check_and_set("key-1", '{"id": "obs-1"}')
        result = await store.check_and_set("key-2", '{"id": "obs-2"}')
        assert result is None

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_recent_key(self):
        store = InMemoryIdempotencyStore()
        await store.check_and_set("key-1", "response")
        assert await store.exists("key-1") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_unknown_key(self):
        store = InMemoryIdempotencyStore()
        assert await store.exists("unknown") is False

    @pytest.mark.asyncio
    async def test_delete_removes_key(self):
        store = InMemoryIdempotencyStore()
        await store.check_and_set("key-1", "response")
        await store.delete("key-1")
        assert await store.exists("key-1") is False

    @pytest.mark.asyncio
    async def test_fingerprint_based_dedup(self):
        """Same fingerprint + device_id → duplicate detected."""
        store = InMemoryIdempotencyStore()
        key = "fp:abc123:device-1"
        await store.check_and_set(key, '{"id": "obs-1"}')
        result = await store.check_and_set(key, '{"id": "obs-1-dup"}')
        assert result == '{"id": "obs-1"}'

    @pytest.mark.asyncio
    async def test_different_fingerprints_not_duplicate(self):
        store = InMemoryIdempotencyStore()
        await store.check_and_set("fp:aaa:device-1", '{"id": "obs-1"}')
        result = await store.check_and_set("fp:bbb:device-1", '{"id": "obs-2"}')
        assert result is None
