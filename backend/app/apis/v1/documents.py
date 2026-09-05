import logging
from uuid import UUID

from fastapi import APIRouter, Request, status

from ...core import DocumentStatus
from ...core.exceptions import InvalidDocumentStateError, NotFoundError
from ...dependencies import (
    ArqPoolDep,
    DocumentServiceDep,
    SessionDep,
)
from ...models import Document
from ...schemas import DocumentResponse

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


@router.post(
    "/{document_id}/retry",
    response_model=DocumentResponse,
    summary="Retry ingestion of a failed document",
)
async def retry_document(
    document_id: UUID,
    db: SessionDep,
    arq_pool: ArqPoolDep,
    request: Request,
) -> DocumentResponse:
    """Reset a failed document to 'uploaded' and re-enqueue for ingestion."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise NotFoundError(message=f"Document {document_id} not found")

    if doc.status != DocumentStatus.FAILED:
        raise InvalidDocumentStateError(
            message=(
                "Document must be in 'failed' state to retry. "
                f"Current state: '{doc.status.value}'."
            )
        )

    if request.app.state.arq_pool is None:
        from ...core.exceptions import AppError

        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="queue_unavailable",
            message="Background processing queue is unavailable.",
        )

    doc.status = DocumentStatus.UPLOADED
    await db.commit()
    await db.refresh(doc)

    await arq_pool.enqueue_job("ingest_document", str(doc.id))

    return DocumentResponse.model_validate(doc)
