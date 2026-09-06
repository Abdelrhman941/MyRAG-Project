from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import NotFoundError
from ...models.chat import ChatMessageModel, ChatSession
from ..ports import MessageData, SessionData


def _ensure_utc(value: datetime | None) -> datetime:
    """Normalize SQLite datetime values to UTC-aware datetimes."""
    if value is None:
        return datetime.now(UTC)

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value


class SqliteSessionRepository:
    """SQLite implementation of the session repository port."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _session_to_dict(session: ChatSession) -> SessionData:
        return {
            "id": session.id,
            "title": session.title,
            "summary": session.summary,
            "summarized_message_count": session.summarized_message_count,
            "created_at": _ensure_utc(session.created_at),
            "updated_at": _ensure_utc(session.updated_at),
        }

    @staticmethod
    def _message_to_dict(message: ChatMessageModel) -> MessageData:
        return {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "created_at": _ensure_utc(message.created_at),
            "sources": message.sources,
        }

    async def create_session(self) -> UUID:
        """Create a new chat session."""
        chat_session = ChatSession()

        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)

        return chat_session.id

    async def get_session(
        self,
        session_id: UUID,
    ) -> SessionData | None:
        """Return a session by ID, if it exists."""
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
        )

        result = await self.session.execute(statement)
        session = result.scalar_one_or_none()

        if session is None:
            return None

        return self._session_to_dict(session)

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessionData]:
        """List sessions ordered from newest to oldest."""
        statement = (
            select(ChatSession)
            .order_by(
                ChatSession.created_at.desc(),
                ChatSession.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(statement)

        return [self._session_to_dict(session) for session in result.scalars().all()]

    async def delete_session(
        self,
        session_id: UUID,
    ) -> None:
        """Delete a chat session."""
        existing = await self.session.get(
            ChatSession,
            session_id,
        )

        if existing is None:
            raise NotFoundError(
                message=f"Session {session_id} not found",
            )

        await self.session.delete(existing)
        await self.session.commit()

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> MessageData:
        """Add a message to a chat session."""
        message = ChatMessageModel(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
        )

        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)

        return self._message_to_dict(message)

    async def count_messages(
        self,
        session_id: UUID,
    ) -> int:
        """Return the number of messages in a session."""
        statement = select(func.count()).where(
            ChatMessageModel.session_id == session_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one() or 0

    async def list_messages(
        self,
        session_id: UUID,
    ) -> list[MessageData]:
        """List all messages in chronological order."""
        statement = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(
                ChatMessageModel.created_at.asc(),
                ChatMessageModel.id.asc(),
            )
        )

        result = await self.session.execute(statement)

        return [self._message_to_dict(message) for message in result.scalars().all()]

    async def get_messages(
        self,
        session_id: UUID,
        offset: int,
        limit: int,
    ) -> list[MessageData]:
        """Return a chronological slice of session messages."""
        statement = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(
                ChatMessageModel.created_at.asc(),
                ChatMessageModel.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return [self._message_to_dict(message) for message in result.scalars().all()]

    async def get_recent_messages(
        self,
        session_id: UUID,
        n: int,
    ) -> list[MessageData]:
        """Return the latest N messages in chronological order."""
        if n <= 0:
            return []

        statement = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(
                ChatMessageModel.created_at.desc(),
                ChatMessageModel.id.desc(),
            )
            .limit(n)
        )

        result = await self.session.execute(statement)

        messages = list(result.scalars().all())
        messages.reverse()

        return [self._message_to_dict(message) for message in messages]

    async def update_summary(
        self,
        session_id: UUID,
        summary: str,
        summarized_count: int,
    ) -> None:
        """Update a session's running summary."""
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
        )

        result = await self.session.execute(statement)
        session = result.scalar_one_or_none()

        if session is None:
            raise NotFoundError(
                message=f"Session {session_id} not found",
            )

        session.summary = summary
        session.summarized_message_count = summarized_count

        await self.session.commit()

    async def update_title(
        self,
        session_id: UUID,
        title: str,
    ) -> None:
        """Update a session's title."""
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
        )

        result = await self.session.execute(statement)
        session = result.scalar_one_or_none()

        if session is None:
            raise NotFoundError(
                message=f"Session {session_id} not found",
            )

        session.title = title

        await self.session.commit()
