import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from app.core import DocumentStatus
from app.core.exceptions import TransientIngestionError, PermanentIngestionError
from app.models import Document
from app.workers.ingestion import ingest_document, on_startup
import asyncio


@pytest.mark.asyncio
async def test_happy_path_enqueue_ready():
    ctx = {"job_try": 1}
    doc_id = str(uuid4())

    with (
        patch("app.workers.ingestion.get_session_maker") as mock_maker,
        patch("app.workers.ingestion.IngestionService") as MockService,
        patch("app.workers.ingestion.get_settings"),
    ):
        mock_session = AsyncMock()
        mock_maker.return_value = MagicMock(
            __aenter__=AsyncMock(return_value=mock_session)
        )

        mock_service_instance = AsyncMock()
        MockService.return_value = mock_service_instance

        await ingest_document(ctx, doc_id)

        mock_service_instance.ingest.assert_called_once()


@pytest.mark.asyncio
async def test_permanent_failure_no_retry():
    ctx = {"job_try": 1}
    doc_id = str(uuid4())

    with (
        patch("app.workers.ingestion.get_session_maker") as mock_maker,
        patch("app.workers.ingestion.IngestionService") as MockService,
        patch("app.workers.ingestion.get_settings"),
    ):
        mock_session = AsyncMock()
        mock_maker.return_value = MagicMock(
            __aenter__=AsyncMock(return_value=mock_session)
        )

        mock_service_instance = AsyncMock()
        mock_service_instance.ingest.side_effect = PermanentIngestionError(
            reason="parsing_error"
        )
        MockService.return_value = mock_service_instance

        mock_doc = Document(id=doc_id, status=DocumentStatus.UPLOADED)
        mock_session.get.return_value = mock_doc

        await ingest_document(ctx, doc_id)

        mock_service_instance.ingest.assert_called_once()
        mock_service_instance._fail_document.assert_called_once_with(
            mock_doc, "parsing_error"
        )


@pytest.mark.asyncio
async def test_transient_failure_retries_then_failed():
    ctx = {"job_try": 1}
    doc_id = str(uuid4())

    with (
        patch("app.workers.ingestion.get_session_maker") as mock_maker,
        patch("app.workers.ingestion.IngestionService") as MockService,
        patch("app.workers.ingestion.get_settings") as mock_settings,
    ):
        mock_settings.return_value.INGESTION_MAX_TRIES = 3
        mock_session = AsyncMock()
        mock_maker.return_value = MagicMock(
            __aenter__=AsyncMock(return_value=mock_session)
        )

        mock_service_instance = AsyncMock()
        mock_service_instance.ingest.side_effect = TransientIngestionError(
            reason="qdrant_unavailable"
        )
        MockService.return_value = mock_service_instance

        # Test attempt 1
        from arq import Retry

        with pytest.raises(Retry):
            await ingest_document(ctx, doc_id)

        # Test final attempt
        ctx["job_try"] = 3
        mock_doc = Document(id=doc_id, status=DocumentStatus.UPLOADED)
        mock_session.get.return_value = mock_doc

        await ingest_document(ctx, doc_id)
        mock_service_instance._fail_document.assert_called_once_with(
            mock_doc, "qdrant_unavailable"
        )


@pytest.mark.asyncio
async def test_recovery_sweep():
    ctx = {}
    with (
        patch("app.workers.ingestion.get_session_maker") as mock_maker,
        patch("app.workers.ingestion.get_settings") as mock_settings,
        patch("app.workers.ingestion.create_pool") as mock_create_pool,
        patch("app.workers.ingestion.get_embedding_model"),
    ):
        mock_settings.return_value.REDIS_URL = "redis://localhost:6379"

        mock_session = AsyncMock()
        mock_maker.return_value = MagicMock(
            __aenter__=AsyncMock(return_value=mock_session)
        )

        mock_doc = Document(id=uuid4(), status=DocumentStatus.PROCESSING)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_doc]
        mock_session.execute.return_value = mock_result

        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        await on_startup(ctx)

        assert mock_doc.status == DocumentStatus.UPLOADED
        mock_pool.enqueue_job.assert_called_once_with(
            "ingest_document", str(mock_doc.id)
        )
        mock_session.commit.assert_called_once()
