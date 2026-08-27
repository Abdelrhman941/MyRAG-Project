import asyncio
import hashlib
import logging
import os
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import DocumentStatus, DocumentType, Settings
from ..core.exceptions import (
    DocumentProcessingConflictError,
    DuplicateDocumentError,
    FileTooLargeError,
    MissingFilenameError,
    NotFoundError,
    UnsupportedDocumentTypeError,
)
from ..infrastructure import FileStoragePort, VectorStorePort
from ..models import Document

logger = logging.getLogger(__name__)


def _remove_temp(path: Path) -> None:
    """Best-effort synchronous removal of a temp file."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove temp file %s", path)


class DocumentService:
    """Orchestrates document upload and persistence."""

    def __init__(
        self,
        db: AsyncSession,
        storage: FileStoragePort,
        settings: Settings,
        vector_store: VectorStorePort | None = None,
    ):
        self.db = db
        self.storage = storage
        self.vector_store = vector_store
        self.settings = settings
        self._db_lock = asyncio.Lock()

    async def _upload_single(self, file: UploadFile) -> Document:
        """Core per-file upload: validate → stream → hash → dedup → persist → move.

        Strategy (avoids orphan DB records):
          1. Stream file → temp file on disk, computing SHA-256 and size in parallel.
          2. Attempt DB insert; roll back and clean up temp file on failure.
          3. Move temp file to final UUID-named location only after a successful commit.
        """
        if not file.filename:
            raise MissingFilenameError()

        # 1. Validate file extension.
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        try:
            doc_type = DocumentType(ext)
        except ValueError as e:
            supported = [t.value for t in DocumentType]
            raise UnsupportedDocumentTypeError(
                message=f"Unsupported file type '{ext}'. Supported: {supported}"
            ) from e

        # 2. Stream to temp file, hashing and size-checking as we go.
        #    os.close() the fd immediately — aiofiles will open the path itself.
        sha256 = hashlib.sha256()
        total_size = 0
        tmp_fd, tmp_path_str = tempfile.mkstemp(
            suffix=doc_type.extension,
            dir=self.settings.UPLOAD_DIR,
        )
        os.close(tmp_fd)
        tmp_path = Path(tmp_path_str)

        try:
            async with aiofiles.open(tmp_path, "wb") as f:
                while chunk := await file.read(8192):
                    total_size += len(chunk)
                    if total_size > self.settings.max_file_size_bytes:
                        max_mb = self.settings.MAX_FILE_SIZE_MB
                        raise FileTooLargeError(
                            message=f"File exceeds maximum allowed size of {max_mb}MB."
                        )
                    sha256.update(chunk)
                    await f.write(chunk)
        except Exception:
            _remove_temp(tmp_path)
            raise

        content_hash = sha256.hexdigest()

        # 3. Persist metadata — temp file still exists; delete it if DB fails.
        doc_id = uuid4()
        document = Document(
            id=doc_id,
            original_file_name=file.filename,
            content_hash=content_hash,
            document_type=doc_type,
            status=DocumentStatus.UPLOADED,
        )

        async with self._db_lock:
            try:
                self.db.add(document)
                await self.db.commit()
                await self.db.refresh(document)
                self.db.expunge(document)
            except IntegrityError as e:
                await self.db.rollback()
                _remove_temp(tmp_path)
                raise DuplicateDocumentError() from e
            except Exception:
                await self.db.rollback()
                _remove_temp(tmp_path)
                raise

        # 4. Move temp file to final storage.
        #    If this fails, delete the DB record so it does not become orphaned.
        final_filename = f"{doc_id}{doc_type.extension}"
        try:
            await self.storage.move_from(tmp_path, final_filename)
        except Exception:
            logger.exception("File move failed after DB commit; rolling back DB record")
            async with self._db_lock:
                from sqlalchemy import delete

                await self.db.execute(delete(Document).where(Document.id == doc_id))
                await self.db.commit()
            raise

        return document

    async def upload_document(self, file: UploadFile) -> Document:
        """Upload a single document. Thin wrapper around ``_upload_single``."""
        return await self._upload_single(file)

    async def upload_batch(
        self, files: list[UploadFile]
    ) -> list[Document | BaseException]:
        """Upload multiple files with bounded concurrency.

        Returns one entry per file: either a ``Document`` on success or the
        raised exception on failure.  A per-file failure never aborts the batch.
        """
        semaphore = asyncio.Semaphore(self.settings.UPLOAD_CONCURRENCY)

        async def _guarded(file: UploadFile) -> Document:
            async with semaphore:
                return await self._upload_single(file)

        results: list[Document | BaseException] = await asyncio.gather(
            *(_guarded(f) for f in files),
            return_exceptions=True,
        )
        return results

    async def list_documents(self, limit: int = 50, offset: int = 0) -> list[Document]:
        """List documents ordered by newest first."""
        stmt = (
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_document(self, document_id: UUID) -> None:
        """
        Delete a document and all its associated data.
        Order: Qdrant Vectors -> Filesystem -> DB.
        """
        if not self.vector_store:
            raise RuntimeError("vector_store is required for deletion")

        # 1. Fetch from DB
        doc = await self.db.get(Document, document_id)
        if not doc:
            raise NotFoundError(message=f"Document {document_id} not found")

        # 2. Check if processing
        if doc.status == DocumentStatus.PROCESSING:
            raise DocumentProcessingConflictError()

        # 3. Delete from Vector Store (Qdrant)
        try:
            await self.vector_store.delete_by_document(document_id)
        except Exception as e:
            logger.exception("Failed to delete vectors for document %s", document_id)
            from ..core.exceptions import VectorStoreDeletionError

            raise VectorStoreDeletionError() from e

        # 4. Delete from Filesystem
        # If this fails, it naturally bubbles up as a 500 (StorageError).
        filename = f"{doc.id}{doc.document_type.extension}"
        await self.storage.delete(filename)

        # 5. Delete from DB
        async with self._db_lock:
            await self.db.delete(doc)
            await self.db.commit()
