from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _ensure_utc(value: datetime) -> datetime:
    """Normalize naive datetimes to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value


class ChatSessionResponse(BaseModel):
    """API representation of a chat session."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime

    _normalize_created_at = field_validator(
        "created_at",
        mode="before",
    )(_ensure_utc)


class ChatSessionListResponse(BaseModel):
    """List of chat sessions."""

    sessions: list[ChatSessionResponse]


class SourceCitation(BaseModel):
    """Source metadata attached to an assistant answer."""

    document_id: str
    original_file_name: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None


class ChatMessageResponse(BaseModel):
    """API representation of a chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime
    sources: list[SourceCitation] | None = None

    _normalize_created_at = field_validator(
        "created_at",
        mode="before",
    )(_ensure_utc)


class ChatMessageListResponse(BaseModel):
    """List of chat messages."""

    messages: list[ChatMessageResponse]


class ChatAnswer(BaseModel):
    """Non-streaming chat response."""

    answer: str
    sources: list[SourceCitation]


class ChatRequest(BaseModel):
    """Incoming chat question."""

    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """Reject whitespace-only questions and normalize surrounding space."""
        value = value.strip()

        if not value:
            raise ValueError("Question cannot be empty.")

        return value
