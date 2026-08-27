from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ...core import get_settings

_engine = None
_session_maker = None


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_maker
    if _session_maker is None:
        settings = get_settings()
        _connect_args = (
            {"check_same_thread": False}
            if settings.DATABASE_URL.startswith("sqlite")
            else {}
        )
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            connect_args=_connect_args,
        )

        if settings.DATABASE_URL.startswith("sqlite"):

            @event.listens_for(_engine.sync_engine, "connect")
            def set_sqlite_pragma(
                dbapi_connection: Any, connection_record: Any
            ) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _session_maker = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async session."""
    maker = get_session_maker()
    async with maker() as session:
        yield session
