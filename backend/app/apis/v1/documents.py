import logging
from uuid import UUID

from fastapi import APIRouter, status

from ...core import get_settings
from ...dependencies import (
    SessionDep,
    SettingsDep,
    StorageDep,
    VectorStoreDep,
    get_storage,
    get_vector_store,
)
from ...infrastructure.db import get_session_maker
from ...services import DocumentService, IngestionService

logger = logging.getLogger(__name__)


async def run_ingestion_background(document_id: UUID) -> None:
    """Background task: ingest a document after upload response has been sent.

    Creates its own DB session and adapters because the request-scoped session
    is closed by the time this runs.
    """
    settings = get_settings()
    storage = get_storage()
    vector_store = get_vector_store(settings)
    maker = get_session_maker()
    async with maker() as db:
        service = IngestionService(db, storage, vector_store, settings)
        try:
            await service.ingest(document_id)
        except Exception:
            logger.exception("Background ingestion failed for document %s", document_id)


router = APIRouter(prefix="/documents", tags=["documents"])


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: UUID,
    db: SessionDep,
    storage: StorageDep,
    vector_store: VectorStoreDep,
    settings: SettingsDep,
) -> None:
    """Delete a document entirely (vectors, file, and DB record)."""
    service = DocumentService(db, storage, settings, vector_store)
    await service.delete_document(document_id)
