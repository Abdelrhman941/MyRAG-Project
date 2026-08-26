import asyncio
import logging
import shutil
from pathlib import Path

import aiofiles

from ...core import get_settings
from ...core.exceptions import StorageError

settings = get_settings()
logger = logging.getLogger(__name__)


class DocumentStorage:
    """Handles local filesystem storage for uploaded documents."""

    def __init__(self, upload_dir: Path = settings.UPLOAD_DIR):
        self.upload_dir = upload_dir

    def _get_path(self, filename: str) -> Path:
        """Get the absolute path for a stored document."""
        path = (self.upload_dir / filename).resolve()
        if not path.is_relative_to(self.upload_dir.resolve()):
            raise StorageError(message="Invalid file path.")
        return path

    async def save(self, filename: str, content: bytes) -> None:
        """Save document content to disk."""
        try:
            path = self._get_path(filename)
            async with aiofiles.open(path, "wb") as f:
                await f.write(content)
        except OSError as e:
            logger.exception("Storage save failed", exc_info=e)
            raise StorageError(message="Failed to save document.") from None

    async def read(self, filename: str) -> bytes:
        """Read document content from disk."""
        try:
            path = self._get_path(filename)
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        except OSError as e:
            logger.exception("Storage read failed", exc_info=e)
            raise StorageError(message="Failed to read document.") from None

    async def delete(self, filename: str) -> None:
        """Delete document from disk."""
        try:
            path = self._get_path(filename)
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.exception("Storage delete failed", exc_info=e)
            raise StorageError(message="Failed to delete document.") from None

    async def move_from(self, source_path: Path, filename: str) -> None:
        """Move a file from a temporary location to the final storage."""
        try:
            dest_path = self._get_path(filename)
            await asyncio.to_thread(shutil.move, str(source_path), str(dest_path))
        except OSError as e:
            logger.exception("Storage move failed", exc_info=e)
            raise StorageError(message="Failed to save document.") from None
