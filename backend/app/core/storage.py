"""File storage abstraction (local filesystem or OCI Object Storage)."""

import os
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class LocalStorage:
    """Store files on local filesystem."""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, content: bytes, filename: str, folder: str = "") -> str:
        """Save file and return storage path."""
        folder_path = self.base_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = folder_path / unique_name
        file_path.write_bytes(content)
        return str(file_path)

    async def get(self, path: str) -> bytes:
        """Read file contents."""
        return Path(path).read_bytes()

    async def delete(self, path: str):
        """Delete a file."""
        p = Path(path)
        if p.exists():
            p.unlink()

    async def get_url(self, path: str) -> str:
        """Get a URL/path for the file."""
        return path


def get_storage():
    """Get the configured storage backend."""
    return LocalStorage()
