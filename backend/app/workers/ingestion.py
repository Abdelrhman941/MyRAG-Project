from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import arq
from arq import Retry
from arq.connections import RedisSettings
from sqlalchemy import select

from ..core import DocumentStatus, get_settings
from ..core.exceptions import PermanentIngestionError, TransientIngestionError
from ..embeddings import get_embedding_model
from ..infrastructure import DocumentStorage, build_vector_store
from ..infrastructure.db.session import get_session_maker
from ..models import Document
from ..services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


async def ingest_document(ctx: dict[str, Any], document_id: str) -> None:
    """Execute the ingestion pipeline for one document."""
    settings = get_settings()
    session_maker = get_session_maker()

    storage = ctx["storage"]
    vector_store = ctx["vector_store"]

    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        logger.error(
            "Invalid document ID received by ingestion worker: %s",
            document_id,
        )
        return

    async with session_maker() as db:
        service = IngestionService(
            db,
            storage,
            vector_store,
            settings,
        )

        try:
            logger.info(
                "Starting ingestion for document %s",
                document_id,
                extra={"event": "ingestion.started"},
            )

            await service.ingest(doc_uuid)

            logger.info(
                "Ingestion job completed for document %s",
                document_id,
                extra={"event": "ingestion.completed"},
            )

        except TransientIngestionError as exc:
            job_try = ctx.get("job_try", 1)
            max_tries = settings.INGESTION_MAX_TRIES

            if job_try >= max_tries:
                logger.error(
                    "Document %s exhausted retries (%d/%d): %s",
                    document_id,
                    job_try,
                    max_tries,
                    exc.reason,
                    extra={
                        "event": "ingestion.retry_exhausted",
                        "reason": exc.reason,
                    },
                )

                doc = await db.get(Document, doc_uuid)
                if doc is not None:
                    await service.fail_document(doc, exc.reason)

                return

            logger.warning(
                "Transient ingestion error for document %s (try %d/%d): %s. Retrying.",
                document_id,
                job_try,
                max_tries,
                exc.reason,
                extra={
                    "event": "ingestion.retry",
                    "reason": exc.reason,
                    "job_try": job_try,
                },
            )

            raise Retry() from exc

        except PermanentIngestionError as exc:
            logger.error(
                "Permanent ingestion error for document %s: %s",
                document_id,
                exc.reason,
                extra={
                    "event": "ingestion.permanent_error",
                    "reason": exc.reason,
                },
            )

            doc = await db.get(Document, doc_uuid)
            if doc is not None:
                await service.fail_document(doc, exc.reason)

        except Exception:
            logger.exception(
                "Unexpected ingestion error for document %s",
                document_id,
                extra={"event": "ingestion.unexpected_error"},
            )

            doc = await db.get(Document, doc_uuid)
            if doc is not None:
                await service.fail_document(doc, "internal_error")


async def on_startup(ctx: dict[str, Any]) -> None:
    """Initialize worker resources and recover unfinished documents."""
    settings = get_settings()

    ctx["storage"] = DocumentStorage()
    ctx["vector_store"] = build_vector_store(settings)

    logger.info("Warming up embedding model")
    await asyncio.to_thread(
        get_embedding_model,
        settings.EMBEDDING_MODEL,
    )
    logger.info(
        "Embedding model warmed up",
        extra={"event": "embedding.model_ready"},
    )

    logger.info("Starting recovery sweep")

    session_maker = get_session_maker()

    async with session_maker() as db:
        statement = select(Document).where(
            Document.status.in_(
                [
                    DocumentStatus.UPLOADED,
                    DocumentStatus.PROCESSING,
                ]
            )
        )

        result = await db.execute(statement)
        documents = result.scalars().all()

        if not documents:
            logger.info("Recovery sweep found no unfinished documents")
            return

        logger.warning(
            "Recovery sweep found %d unfinished document(s)",
            len(documents),
            extra={"event": "ingestion.recovery_started"},
        )

        redis = ctx["redis"]

        for document in documents:
            document.status = DocumentStatus.UPLOADED

            await redis.enqueue_job(
                "ingest_document",
                str(document.id),
            )

        await db.commit()

        logger.info(
            "Recovery sweep completed for %d document(s)",
            len(documents),
            extra={
                "event": "ingestion.recovery_completed",
                "recovered_count": len(documents),
            },
        )


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """Release worker-owned resources."""
    logger.info("Worker shutdown started")

    vector_store = ctx.get("vector_store")
    if vector_store is None:
        logger.info("Worker shutdown complete")
        return

    client = getattr(vector_store, "client", None)
    close = getattr(client, "close", None)

    if close is not None:
        try:
            result = close()
            if result is not None:
                await result
        except Exception:
            logger.exception("Failed to close worker vector store client")

    logger.info("Worker shutdown complete")


async def stalled_watchdog(ctx: dict[str, Any]) -> None:
    """Fail documents that remained processing beyond the timeout."""
    settings = get_settings()
    session_maker = get_session_maker()

    threshold = datetime.now(UTC) - timedelta(
        seconds=settings.INGESTION_JOB_TIMEOUT_S + 60
    )

    async with session_maker() as db:
        statement = select(Document).where(
            Document.status == DocumentStatus.PROCESSING,
            Document.updated_at < threshold,
        )

        result = await db.execute(statement)
        documents = result.scalars().all()

        if not documents:
            return

        service = IngestionService(
            db,
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            settings,
        )

        for document in documents:
            logger.warning(
                "Watchdog failing stalled document %s",
                document.id,
                extra={
                    "event": "ingestion.stalled",
                    "document_id": str(document.id),
                },
            )

            await service.fail_document(
                document,
                "stalled",
            )


settings = get_settings()


class WorkerSettings:
    """ARQ worker configuration."""

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [ingest_document]  # noqa: RUF012
    cron_jobs = [arq.cron(stalled_watchdog, minute=set(range(60)))]  # noqa: RUF012

    on_startup = on_startup
    on_shutdown = on_shutdown

    max_jobs = settings.INGESTION_WORKER_MAX_JOBS
    job_timeout = settings.INGESTION_JOB_TIMEOUT_S
    max_tries = settings.INGESTION_MAX_TRIES
