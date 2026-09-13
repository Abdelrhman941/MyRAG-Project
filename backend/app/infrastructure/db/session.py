from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ...core import get_settings

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the application-wide async SQLAlchemy engine."""
    global _engine

    if _engine is None:
        settings = get_settings()

        connect_args = (
            {"check_same_thread": False}
            if settings.DATABASE_URL.startswith("sqlite")
            else {}
        )

        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            connect_args=connect_args,
        )

        if settings.DATABASE_URL.startswith("sqlite"):

            @event.listens_for(_engine.sync_engine, "connect")
            def configure_sqlite(
                dbapi_connection: object,
                _connection_record: object,
            ) -> None:
                cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
                try:
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA busy_timeout=5000")
                finally:
                    cursor.close()

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the application-wide async session factory."""
    global _session_maker

    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    return _session_maker


async def dispose_engine() -> None:
    """Dispose the application-wide database engine."""
    global _engine, _session_maker

    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _session_maker = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with get_session_maker()() as session:
        yield session
