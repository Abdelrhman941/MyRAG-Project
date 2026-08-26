import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..chunking import chunk
from ..core import DocumentStatus
from ..core.config import Settings
from ..core.exceptions import ParsingError, StorageError
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
            except StorageError:
                logger.exception("Storage error during ingestion for %s", document_id)
                await self._fail_document(doc, "storage_error")
                return

            # 2. Parse
            try:
                segments = parse(content, doc.document_type, doc.id)
            except ParsingError:
                logger.exception("Parsing failed for %s", document_id)
                await self._fail_document(doc, "parsing_error")
                return
            except Exception:
                logger.exception("Unexpected error during parsing for %s", document_id)
                await self._fail_document(doc, "internal_error")
                return

            if not segments:
                await self._fail_document(doc, "no_extractable_text")
                return

            # 3. Chunk
            chunks = chunk(segments, doc.id)
            if not chunks:
                await self._fail_document(doc, "no_extractable_text")
                return

            # 4. Embed + Upsert in batches
            # Load singleton; first call downloads/loads BGE-M3 — expected slow
            model = get_embedding_model(self.settings.EMBEDDING_MODEL)
            await self.vector_store.ensure_collection()

            payload_metadata = {
                "original_file_name": doc.original_file_name,
                "created_at": doc.created_at.isoformat(),
            }

            batch_size = self.settings.EMBEDDING_BATCH_SIZE
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i : i + batch_size]
                texts = [c.text for c in batch_chunks]

                try:
                    # encode_batch is CPU-bound; run in thread to not block event loop
                    dense, sparse = await asyncio.to_thread(
                        model.encode_batch, texts, self.settings.EMBEDDING_BATCH_SIZE
                    )
                except Exception:
                    logger.exception(
                        "Embedding failed for %s",
                        document_id,
                        extra={"event": "ingestion.embedding_error"},
                    )
                    await self._fail_document(doc, "embedding_error")
                    return

                try:
                    await self.vector_store.upsert_chunks(
                        batch_chunks, dense, sparse, payload_metadata
                    )
                except Exception:
                    # Qdrant unreachable -> event=ingestion.qdrant_unavailable
                    logger.exception(
                        "Vector store upsert failed for %s",
                        document_id,
                        extra={"event": "ingestion.qdrant_unavailable"},
                    )
                    await self._fail_document(doc, "qdrant_unavailable")
                    return

            # 5. Success
            doc.status = DocumentStatus.READY
            await self.db.commit()
            logger.info(
                "Ingestion completed for document %s",
                document_id,
                extra={"event": "ingestion.status", "status": "ready"},
            )

        except Exception:
            logger.exception("Unhandled error during ingestion for %s", document_id)
            await self._fail_document(doc, "internal_error")

    async def _fail_document(self, doc: Document, reason: str) -> None:
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
