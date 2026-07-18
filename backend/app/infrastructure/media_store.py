"""Media Store — Production adapter.

Saves observation media (photos, voice) to local filesystem.
Swap to Cloud Storage adapter for production deployment.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from app.domain.entities import Media
from app.domain.ports import MediaStore


class LocalMediaStore(MediaStore):
    """Filesystem-based media storage.

    Stores files in a configurable directory with content-hash naming.
    Suitable for development and small-scale pilots.
    """

    def __init__(self, base_path: str = "./media") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, media: Media, content: bytes) -> str:
        """Save media file and return the storage path."""
        # Organize by date
        date_dir = datetime.now().strftime("%Y/%m/%d")
        media_dir = self.base_path / media.media_type / date_dir
        media_dir.mkdir(parents=True, exist_ok=True)

        # Use content hash as filename (deduplication at storage level)
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        ext = self._get_extension(media.media_type)
        filename = f"{media.id}_{content_hash}{ext}"
        filepath = media_dir / filename

        filepath.write_bytes(content)

        # Return relative path for DB storage
        relative_path = str(filepath.relative_to(self.base_path))
        media.storage_uri = relative_path
        media.size_bytes = len(content)
        media.content_hash = content_hash

        return relative_path

    async def get(self, media_id: str) -> bytes | None:
        """Retrieve media by ID. Searches all type/date directories."""
        for media_type in ["image", "audio"]:
            for date_dir in (self.base_path / media_type).glob("*/*/*"):
                for filepath in date_dir.glob(f"{media_id}_*"):
                    return filepath.read_bytes()
        return None

    async def get_by_path(self, relative_path: str) -> bytes | None:
        """Retrieve media by stored path."""
        filepath = self.base_path / relative_path
        if filepath.exists():
            return filepath.read_bytes()
        return None

    async def delete(self, media_id: str) -> bool:
        """Delete media by ID."""
        for media_type in ["image", "audio"]:
            for date_dir in (self.base_path / media_type).glob("*/*/*"):
                for filepath in date_dir.glob(f"{media_id}_*"):
                    filepath.unlink()
                    return True
        return False

    async def get_size(self) -> dict:
        """Get storage statistics."""
        total_bytes = 0
        file_count = 0
        for filepath in self.base_path.rglob("*"):
            if filepath.is_file():
                total_bytes += filepath.stat().st_size
                file_count += 1
        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / 1024 / 1024, 2),
            "file_count": file_count,
        }

    def _get_extension(self, media_type: str) -> str:
        return ".jpg" if media_type == "image" else ".webm"


from datetime import datetime
