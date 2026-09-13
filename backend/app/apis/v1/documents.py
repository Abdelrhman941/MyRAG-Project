from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from ...core import DocumentStatus
from ...core.exceptions import InvalidDocumentStateError, NotFoundError
from ...dependencies import (
    ArqPoolDep,
    DocumentServiceDep,
    SessionDep,
)
from ...models import Document
from ...schemas import DocumentResponse

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@router.delete(
    "/{document_id}",
    status_code=204,
    summary="Delete a document",
)
async def delete_document(
    document_id: UUID,
    doc_service: DocumentServiceDep,
) -> None:
    """Delete a document and all associated data."""
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
) -> DocumentResponse:
    """Reset a failed document and enqueue it for ingestion."""
    document = await db.get(
        Document,
        document_id,
    )

    if document is None:
        raise NotFoundError(
            message=f"Document {document_id} not found",
        )

    if document.status != DocumentStatus.FAILED:
        raise InvalidDocumentStateError(
            message=(
                "Document must be in 'failed' state to retry. "
                f"Current state: '{document.status.value}'."
            ),
        )

    document.status = DocumentStatus.UPLOADED

    await db.commit()
    await db.refresh(document)

    await arq_pool.enqueue_job(
        "ingest_document",
        str(document.id),
    )

    return DocumentResponse.model_validate(document)
