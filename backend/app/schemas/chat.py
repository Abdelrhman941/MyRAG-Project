from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime


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


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ChatAnswer(BaseModel):
    answer: str
    sources: list[SourceCitation]
