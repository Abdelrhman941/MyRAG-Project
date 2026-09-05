from datetime import datetime, UTC
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from ..core import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    """Response schema for document metadata."""

    id: UUID
    session_id: UUID
    original_file_name: str
    document_type: DocumentType
    status: DocumentStatus
    file_size_bytes: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


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


__all__: list[str] = [
    "BatchUploadError",
    "BatchUploadResponse",
    "BatchUploadResult",
    "DocumentResponse",
]
