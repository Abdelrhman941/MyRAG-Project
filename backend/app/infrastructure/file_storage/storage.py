from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

import aiofiles

from ...core import get_settings
from ...core.exceptions import StorageError

logger = logging.getLogger(__name__)


class DocumentStorage:
    """Manage uploaded documents on the local filesystem."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self.upload_dir = (
            upload_dir if upload_dir is not None else get_settings().UPLOAD_DIR
        )
        self.upload_dir = self.upload_dir.resolve()

    def _get_path(self, filename: str) -> Path:
        """Resolve a filename while preventing path traversal."""
        path = (self.upload_dir / filename).resolve()

        if not path.is_relative_to(self.upload_dir):
            raise StorageError(message="Invalid file path.")

        return path

    async def read(self, filename: str) -> bytes:
        """Read document content from storage."""
        path = self._get_path(filename)

        try:
            async with aiofiles.open(path, "rb") as file:
                return await file.read()
        except OSError as exc:
            logger.exception(
                "Failed to read document %s",
                filename,
            )
            raise StorageError(
                message="Failed to read document.",
            ) from exc

    async def delete(self, filename: str) -> None:
        """Delete a document from storage if it exists."""
        path = self._get_path(filename)

        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.exception(
                "Failed to delete document %s",
                filename,
            )
            raise StorageError(
                message="Failed to delete document.",
            ) from exc

    async def move_from(
        self,
        source_path: Path,
        filename: str,
    ) -> None:
        """Move a temporary file into final document storage."""
        destination = self._get_path(filename)

        try:
            await asyncio.to_thread(
                shutil.move,
                str(source_path),
                str(destination),
            )
        except OSError as exc:
            logger.exception(
                "Failed to move document to %s",
                filename,
            )
            raise StorageError(
                message="Failed to save document.",
            ) from exc
