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


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]
