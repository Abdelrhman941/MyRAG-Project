import asyncio
import logging
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


class IngestionService:
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
        doc = await self.db.get(Document, document_id)
        if not doc:
            logger.error("Document %s not found for ingestion", document_id)
            return

        if doc.status != DocumentStatus.UPLOADED:
            logger.warning(
                "Document %s is not in uploaded status (status: %s)",
                document_id,
                doc.status,
            )
            return

        doc.status = DocumentStatus.PROCESSING
        await self.db.commit()

        try:
            # 1. Fetch content
            try:
                content = await self.storage.read(
                    f"{doc.id}{doc.document_type.extension}"
                )
            except StorageError as e:
                logger.exception("Storage error during ingestion for %s", document_id)

                raise TransientIngestionError(reason="storage_error") from e

            # 2. Parse
            try:
                segments = await asyncio.to_thread(
                    parse, content, doc.document_type, doc.id
                )
            except ParsingError as e:
                logger.exception("Parsing failed for %s", document_id)

                raise PermanentIngestionError(reason="parsing_error") from e
            except Exception as e:
                logger.exception("Unexpected error during parsing for %s", document_id)

                raise TransientIngestionError(reason="internal_error") from e

            if not segments:
                raise PermanentIngestionError(reason="no_extractable_text")

            # 3. Chunk
            chunks = await asyncio.to_thread(chunk, segments, doc.id)
            if not chunks:
                raise PermanentIngestionError(reason="no_extractable_text")

            # 4. Embed + Upsert in batches
            model = get_embedding_model(self.settings.EMBEDDING_MODEL)

            payload_metadata = {
                "original_file_name": doc.original_file_name,
                "created_at": doc.created_at.isoformat(),
                "session_id": str(doc.session_id),
            }

            batch_size = self.settings.EMBEDDING_BATCH_SIZE

            for i in range(0, len(chunks), batch_size):
                # Delete-while-ingesting guard: bypass identity map cache
                doc_exists = await self.db.scalar(
                    select(Document.id).where(Document.id == document_id)
                )
                if not doc_exists:
                    logger.info(
                        "Document %s deleted during ingestion; aborting silently.",
                        document_id,
                    )
                    return

                batch_chunks = chunks[i : i + batch_size]
                texts = [c.text for c in batch_chunks]

                try:
                    dense, sparse = await asyncio.to_thread(
                        model.encode_batch, texts, self.settings.EMBEDDING_BATCH_SIZE
                    )
                except Exception as e:
                    logger.exception(
                        "Embedding failed for %s",
                        document_id,
                        extra={"event": "ingestion.embedding_error"},
                    )

                    raise TransientIngestionError(reason="embedding_error") from e

                try:
                    await self.vector_store.upsert_chunks(
                        batch_chunks, dense, sparse, payload_metadata
                    )
                except Exception as e:
                    logger.exception(
                        "Vector store upsert failed for %s",
                        document_id,
                        extra={"event": "ingestion.qdrant_unavailable"},
                    )

                    raise TransientIngestionError(reason="qdrant_unavailable") from e

            # 5. Success
            doc.status = DocumentStatus.READY
            await self.db.commit()
            logger.info(
                "Ingestion completed for document %s",
                document_id,
                extra={"event": "ingestion.status", "status": "ready"},
            )

        except (TransientIngestionError, PermanentIngestionError):
            raise
        except Exception as e:
            logger.exception("Unhandled error during ingestion for %s", document_id)

            raise TransientIngestionError(reason="internal_error") from e

    async def fail_document(self, doc: Document, reason: str) -> None:
        try:
            await self.vector_store.delete_by_document(doc.id)
        except Exception:
            logger.exception(
                "Failed to clean up Qdrant points for failed document %s", doc.id
            )

        doc.status = DocumentStatus.FAILED
        await self.db.commit()
        logger.error(
            "Document %s failed ingestion: %s",
            doc.id,
            reason,
            extra={"event": "ingestion.status", "status": "failed", "reason": reason},
        )
