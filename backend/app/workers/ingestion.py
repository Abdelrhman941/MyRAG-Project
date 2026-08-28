import asyncio
import logging
from typing import Any
from uuid import UUID

from arq import Retry, create_pool
from arq.connections import RedisSettings
from sqlalchemy import select

from ..core import DocumentStatus, get_settings
from ..core.exceptions import PermanentIngestionError, TransientIngestionError
from ..embeddings import get_embedding_model
from ..infrastructure import DocumentStorage
from ..infrastructure.db.session import get_session_maker
from ..infrastructure.vector_store.qdrant import QdrantVectorStore
from ..models import Document
from ..services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


async def ingest_document(ctx: dict[str, Any], document_id: str) -> None:
    """ARQ job to ingest a document."""
    settings = get_settings()
    session_maker = get_session_maker()
    storage = DocumentStorage()
    vector_store = QdrantVectorStore(settings)

    doc_uuid = UUID(document_id)

    async with session_maker() as db:
        service = IngestionService(db, storage, vector_store, settings)

        try:
            await service.ingest(doc_uuid)
        except TransientIngestionError as e:
            # Check if this is the last try
            job_try = ctx.get("job_try", 1)
            max_tries = settings.INGESTION_MAX_TRIES

            if job_try >= max_tries:
                logger.error(
                    "Document %s failed after %d tries: %s",
                    document_id,
                    job_try,
                    e.reason,
                )
                # Mark as failed permanently
                doc = await db.get(Document, doc_uuid)
                if doc:
                    await service.fail_document(doc, e.reason)
            else:
                logger.warning(
                    "Transient error on doc %s (try %d/%d), raising arq.Retry: %s",
                    document_id,
                    job_try,
                    max_tries,
                    e.reason,
                )

                # Raise Retry so it uses default backoff
                raise Retry() from e

        except PermanentIngestionError as e:
            logger.error("Permanent error on doc %s: %s", document_id, e.reason)
            doc = await db.get(Document, doc_uuid)
            if doc:
                await service.fail_document(doc, e.reason)


async def on_startup(ctx: dict[str, Any]) -> None:
    """Worker startup: warm up model and perform recovery sweep."""
    settings = get_settings()

    logger.info("Warming up embedding model...")
    # asyncio.to_thread? No, just call it, but ARQ allows blocking in startup?
    # ARQ startup runs in the async loop. get_embedding_model is sync and takes a while.
    # We should run it in a thread.

    await asyncio.to_thread(get_embedding_model, settings.EMBEDDING_MODEL)
    logger.info("Embedding model warmed up.")

    logger.info("Starting recovery sweep for stuck documents...")
    session_maker = get_session_maker()

    async with session_maker() as db:
        # Find UPLOADED or PROCESSING documents
        stmt = select(Document).where(
            Document.status.in_([DocumentStatus.UPLOADED, DocumentStatus.PROCESSING])
        )
        result = await db.execute(stmt)
        docs = result.scalars().all()

        if docs:
            logger.info(
                "Found %d stuck documents. Resetting and enqueuing...",
                len(docs),
            )

            # Use same redis settings as worker
            redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
            pool = await create_pool(redis_settings)

            for doc in docs:
                doc.status = DocumentStatus.UPLOADED
                await pool.enqueue_job("ingest_document", str(doc.id))

            await db.commit()
            await pool.close()
            logger.info("Recovery sweep complete.")
        else:
            logger.info("No stuck documents found in recovery sweep.")


async def on_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Worker shutting down.")


# Configure worker
settings = get_settings()


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [ingest_document]  # noqa: RUF012
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = settings.INGESTION_WORKER_MAX_JOBS
    job_timeout = settings.INGESTION_JOB_TIMEOUT_S
    max_tries = settings.INGESTION_MAX_TRIES
