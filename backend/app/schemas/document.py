from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..core import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    """Response schema for document metadata."""

    id: UUID
    original_file_name: str
    document_type: DocumentType
    status: DocumentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
