"""Tests for LocalMediaStore."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from app.infrastructure.media_store import LocalMediaStore
from app.domain.entities import Media


@pytest.fixture
def media_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalMediaStore(base_path=tmpdir)


class TestLocalMediaStore:
    @pytest.mark.asyncio
    async def test_save_image(self, media_store: LocalMediaStore):
        media = Media(id="test-001", media_type="image", observation_id="obs-1")
        content = b"fake image bytes"

        path = await media_store.save(media, content)

        assert path is not None
        assert media.size_bytes == len(content)
        assert media.content_hash != ""

    @pytest.mark.asyncio
    async def test_save_audio(self, media_store: LocalMediaStore):
        media = Media(id="test-002", media_type="audio", observation_id="obs-1")
        content = b"fake audio bytes"

        path = await media_store.save(media, content)

        assert path is not None
        assert media.size_bytes == len(content)

    @pytest.mark.asyncio
    async def test_get_by_path(self, media_store: LocalMediaStore):
        media = Media(id="test-003", media_type="image", observation_id="obs-1")
        content = b"test content for retrieval"
        path = await media_store.save(media, content)

        retrieved = await media_store.get_by_path(path)
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, media_store: LocalMediaStore):
        result = await media_store.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, media_store: LocalMediaStore):
        media = Media(id="test-004", media_type="image", observation_id="obs-1")
        await media_store.save(media, b"content")

        deleted = await media_store.delete("test-004")
        assert deleted is True

        retrieved = await media_store.get("test-004")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_size(self, media_store: LocalMediaStore):
        media = Media(id="test-005", media_type="image", observation_id="obs-1")
        await media_store.save(media, b"x" * 1024)

        stats = await media_store.get_size()
        assert stats["file_count"] == 1
        assert stats["total_bytes"] == 1024

    @pytest.mark.asyncio
    async def test_content_deduplication(self, media_store: LocalMediaStore):
        """Same content → same hash → same filename."""
        media1 = Media(id="dup-1", media_type="image", observation_id="obs-1")
        media2 = Media(id="dup-2", media_type="image", observation_id="obs-2")

        path1 = await media_store.save(media1, b"identical content")
        path2 = await media_store.save(media2, b"identical content")

        # Different IDs but same content hash
        assert media1.content_hash == media2.content_hash
        # Different file paths (different IDs)
        assert path1 != path2

    @pytest.mark.asyncio
    async def test_date_directory_structure(self, media_store: LocalMediaStore):
        media = Media(id="date-test", media_type="image", observation_id="obs-1")
        path = await media_store.save(media, b"content")

        # Path should contain date components (OS-agnostic)
        assert "image" in path
        assert "2026" in path
        assert "date-test" in path
