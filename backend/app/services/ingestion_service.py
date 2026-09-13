from __future__ import annotations

import asyncio
import logging
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..chunking import chunk
from ..core import DocumentStatus
from ..core.config import Settings
from ..core.exceptions import (
    ParsingError,
    PermanentIngestionError,
    StorageError,
    TransientIngestionError,
)
from ..embeddings import get_embedding_model
from ..infrastructure.ports import FileStoragePort, VectorStorePort
from ..models import Document
from ..parsers import parse

logger = logging.getLogger(__name__)


async def fail_document(
    db: AsyncSession,
    vector_store: VectorStorePort,
    document: Document,
    reason: str,
) -> None:
    """Mark a document as failed and remove any partially indexed chunks."""
    try:
        await vector_store.delete_by_document(document.id)
    except Exception:
        logger.exception(
            "Failed to clean up vector-store points for failed document %s",
            document.id,
        )

    document.status = DocumentStatus.FAILED
    await db.commit()

    logger.error(
        "Document %s failed ingestion: %s",
        document.id,
        reason,
    )


class IngestionService:
    """Orchestrate document parsing, chunking, embedding, and indexing."""

    def __init__(
        self,
        db: AsyncSession,
        storage: FileStoragePort,
        vector_store: VectorStorePort,
        settings: Settings,
    ):
        self.db = db
        self.storage = storage
        self.vector_store = vector_store
        self.settings = settings

    async def ingest(self, document_id: UUID) -> None:
        """Process one uploaded document into the vector store."""
        started_at = time.perf_counter()

        document = await self.db.get(Document, document_id)

        if document is None:
            logger.warning(
                "Document %s not found for ingestion",
                document_id,
            )
            return

        if document.status != DocumentStatus.UPLOADED:
            logger.warning(
                "Skipping document %s because its status is %s",
                document_id,
                document.status,
            )
            return

        document.status = DocumentStatus.PROCESSING
        await self.db.commit()

        try:
            storage_started = time.perf_counter()

            try:
                content = await self.storage.read(
                    f"{document.id}{document.document_type.extension}"
                )
            except StorageError as exc:
                raise TransientIngestionError(
                    reason="storage_error",
                ) from exc

            storage_ms = (time.perf_counter() - storage_started) * 1000

            parse_started = time.perf_counter()

            try:
                segments = await asyncio.to_thread(
                    parse,
                    content,
                    document.document_type,
                    document.id,
                )
            except ParsingError as exc:
                raise PermanentIngestionError(
                    reason="parsing_error",
                ) from exc
            except Exception as exc:
                raise TransientIngestionError(
                    reason="internal_error",
                ) from exc

            parse_ms = (time.perf_counter() - parse_started) * 1000

            if not segments:
                raise PermanentIngestionError(
                    reason="no_extractable_text",
                )

            chunk_started = time.perf_counter()

            chunks = await asyncio.to_thread(
                chunk,
                segments,
                document.id,
            )

            chunk_ms = (time.perf_counter() - chunk_started) * 1000

            if not chunks:
                raise PermanentIngestionError(
                    reason="no_extractable_text",
                )

            model = get_embedding_model(
                self.settings.EMBEDDING_MODEL,
            )

            payload_metadata = {
                "original_file_name": document.original_file_name,
                "created_at": document.created_at.isoformat(),
                "session_id": str(document.session_id),
            }

            batch_size = self.settings.EMBEDDING_BATCH_SIZE
            embedding_started = time.perf_counter()
            batch_count = 0

            for i in range(0, len(chunks), batch_size):
                document_exists = await self.db.scalar(
                    select(Document.id).where(
                        Document.id == document_id,
                    )
                )

                if not document_exists:
                    logger.info(
                        "Document %s was deleted during ingestion; stopping",
                        document_id,
                    )
                    return

                batch_chunks = chunks[i : i + batch_size]
                texts = [item.text for item in batch_chunks]

                try:
                    # NOTE: always compute sparse vectors during ingestion,
                    # regardless of RETRIEVAL_HYBRID. Skipping them when hybrid
                    # is off produces an empty sparse list that fails the
                    # upsert length check — and it keeps indexed vectors
                    # compatible if hybrid is toggled on later without
                    # re-ingestion. The hybrid flag only gates the *query*
                    # side (see retrieval/service.py).
                    dense, sparse = await asyncio.to_thread(
                        model.encode_batch,
                        texts,
                        batch_size,
                        True,
                    )
                except Exception as exc:
                    raise TransientIngestionError(
                        reason="embedding_error",
                    ) from exc

                try:
                    await self.vector_store.upsert_chunks(
                        batch_chunks,
                        dense,
                        sparse,
                        payload_metadata,
                    )
                except Exception as exc:
                    raise TransientIngestionError(
                        reason="qdrant_unavailable",
                    ) from exc

                batch_count += 1

            embedding_ms = (time.perf_counter() - embedding_started) * 1000

            document.status = DocumentStatus.READY
            await self.db.commit()

            total_ms = (time.perf_counter() - started_at) * 1000

            logger.info(
                "Ingestion completed for document %s "
                "(segments=%d chunks=%d batches=%d "
                "storage=%.2fms parse=%.2fms chunk=%.2fms "
                "embed_and_upsert=%.2fms total=%.2fms)",
                document_id,
                len(segments),
                len(chunks),
                batch_count,
                storage_ms,
                parse_ms,
                chunk_ms,
                embedding_ms,
                total_ms,
            )

        except (
            TransientIngestionError,
            PermanentIngestionError,
        ):
            raise

        except Exception as exc:
            raise TransientIngestionError(
                reason="internal_error",
            ) from exc
