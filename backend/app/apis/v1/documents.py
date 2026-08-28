import logging
from uuid import UUID

from fastapi import APIRouter, status

from ...dependencies import (
    DocumentServiceDep,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: UUID,
    doc_service: DocumentServiceDep,
) -> None:
    """Delete a document entirely (vectors, file, and DB record)."""
    await doc_service.delete_document(document_id)
