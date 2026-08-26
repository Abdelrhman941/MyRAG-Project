from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import NotFoundError
from ...models.chat import ChatMessageModel, ChatSession


class SqliteSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self) -> UUID:
        chat_session = ChatSession()
        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)
        return chat_session.id

    async def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            return None
        return {
            "id": chat_session.id,
            "title": chat_session.title,
            "summary": chat_session.summary,
            "created_at": chat_session.created_at,
            "updated_at": chat_session.updated_at,
        }

    async def list_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        stmt = (
            select(ChatSession)
            .order_by(ChatSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "id": s.id,
                "title": s.title,
                "summary": s.summary,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in result.scalars().all()
        ]

    async def delete_session(self, session_id: UUID) -> None:
        stmt = delete(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundError(message=f"Session {session_id} not found")
        await self.session.commit()

    async def add_message(
        self, session_id: UUID, role: str, content: str
    ) -> dict[str, Any]:
        msg = ChatMessageModel(session_id=session_id, role=role, content=content)
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at,
        }

    async def list_messages(self, session_id: UUID) -> list[dict[str, Any]]:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in result.scalars().all()
        ]

    async def get_recent_messages(
        self, session_id: UUID, n: int
    ) -> list[dict[str, Any]]:
        # Need to fetch the latest N messages, but return them in chronological order
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.desc())
            .limit(n)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        return [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ]

    async def update_summary(self, session_id: UUID, summary: str) -> None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise NotFoundError(message=f"Session {session_id} not found")
        chat_session.summary = summary
        await self.session.commit()

    async def update_title(self, session_id: UUID, title: str) -> None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise NotFoundError(message=f"Session {session_id} not found")
        chat_session.title = title
        await self.session.commit()
