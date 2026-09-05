from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse]


class SourceCitation(BaseModel):
    document_id: str
    original_file_name: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime
    sources: list[SourceCitation] | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ChatAnswer(BaseModel):
    answer: str
    sources: list[SourceCitation]
