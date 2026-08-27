from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..core import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    """Response schema for document metadata."""

    id: UUID
    session_id: UUID
    original_file_name: str
    document_type: DocumentType
    status: DocumentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchUploadError(BaseModel):
    """Per-file error detail within a batch response."""

    code: str
    message: str


class BatchUploadResult(BaseModel):
    """Outcome for a single file in a batch upload request.

    Exactly one of ``document`` or ``error`` is set depending on ``ok``.
    """

    filename: str
    ok: bool
    document: DocumentResponse | None = None
    error: BatchUploadError | None = None


class BatchUploadResponse(BaseModel):
    """Response for ``POST /api/v1/chat/sessions/{session_id}/documents/batch``."""

    results: list[BatchUploadResult]

    model_config = ConfigDict(arbitrary_types_allowed=True)


__all__: list[Any] = [
    "BatchUploadError",
    "BatchUploadResponse",
    "BatchUploadResult",
    "DocumentResponse",
]
