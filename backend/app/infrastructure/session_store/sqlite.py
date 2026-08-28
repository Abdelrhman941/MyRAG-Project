from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import NotFoundError
from ...models.chat import ChatMessageModel, ChatSession
from ..ports import MessageData, SessionData


class SqliteSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _session_to_dict(s: ChatSession) -> SessionData:
        return {
            "id": s.id,
            "title": s.title,
            "summary": s.summary,
            "summarized_message_count": s.summarized_message_count,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }

    @staticmethod
    def _message_to_dict(m: ChatMessageModel) -> MessageData:
        return {
            "id": m.id,
            "session_id": m.session_id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }

    async def create_session(self) -> UUID:
        chat_session = ChatSession()
        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)
        return chat_session.id

    async def get_session(self, session_id: UUID) -> SessionData | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            return None
        return self._session_to_dict(chat_session)

    async def list_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> list[SessionData]:
        stmt = (
            select(ChatSession)
            .order_by(ChatSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [self._session_to_dict(s) for s in result.scalars().all()]

    async def delete_session(self, session_id: UUID) -> None:
        stmt = delete(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundError(message=f"Session {session_id} not found")
        await self.session.commit()

    async def add_message(
        self, session_id: UUID, role: str, content: str
    ) -> MessageData:
        msg = ChatMessageModel(session_id=session_id, role=role, content=content)
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return self._message_to_dict(msg)

    async def count_messages(self, session_id: UUID) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).where(ChatMessageModel.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def list_messages(self, session_id: UUID) -> list[MessageData]:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [self._message_to_dict(m) for m in result.scalars().all()]

    async def get_messages(
        self, session_id: UUID, offset: int, limit: int
    ) -> list[MessageData]:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self._message_to_dict(m) for m in result.scalars().all()]

    async def get_recent_messages(self, session_id: UUID, n: int) -> list[MessageData]:
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
        return [self._message_to_dict(m) for m in messages]

    async def update_summary(
        self, session_id: UUID, summary: str, summarized_count: int
    ) -> None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise NotFoundError(message=f"Session {session_id} not found")
        chat_session.summary = summary
        chat_session.summarized_message_count = summarized_count
        await self.session.commit()

    async def update_title(self, session_id: UUID, title: str) -> None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise NotFoundError(message=f"Session {session_id} not found")
        chat_session.title = title
        await self.session.commit()
