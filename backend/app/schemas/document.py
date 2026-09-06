from __future__ import annotations

from datetime import UTC, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ..core import DocumentStatus, DocumentType


def _ensure_utc(value: datetime) -> datetime:
    """Normalize naive datetimes to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value


class DocumentResponse(BaseModel):
    """API representation of document metadata."""

    id: UUID
    session_id: UUID
    original_file_name: str
    document_type: DocumentType
    status: DocumentStatus
    file_size_bytes: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    _normalize_created_at = field_validator(
        "created_at",
        mode="before",
    )(_ensure_utc)


class BatchUploadError(BaseModel):
    """Per-file error detail within a batch response."""

    code: str
    message: str


class BatchUploadResult(BaseModel):
    """Outcome for a single file in a batch upload."""

    filename: str
    ok: bool
    document: DocumentResponse | None = None
    error: BatchUploadError | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        """Ensure exactly one success/failure payload matches the status."""
        has_document = self.document is not None
        has_error = self.error is not None

        if self.ok and (not has_document or has_error):
            raise ValueError(
                "Successful batch results must contain a document only.",
            )

        if not self.ok and (has_document or not has_error):
            raise ValueError(
                "Failed batch results must contain an error only.",
            )

        return self


class BatchUploadResponse(BaseModel):
    """Response for a batch document upload."""

    results: list[BatchUploadResult]


__all__ = [
    "BatchUploadError",
    "BatchUploadResponse",
    "BatchUploadResult",
    "DocumentResponse",
]
