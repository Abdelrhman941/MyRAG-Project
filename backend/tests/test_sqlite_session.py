from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.session_store.sqlite import SqliteSessionRepository
from app.models import Base


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_count_messages_correctness(db_session):
    repo = SqliteSessionRepository(db_session)
    session_id = await repo.create_session()

    count = await repo.count_messages(session_id)
    assert count == 0

    await repo.add_message(session_id, "user", "hi")
    count = await repo.count_messages(session_id)
    assert count == 1

    await repo.add_message(session_id, "assistant", "hello")
    count = await repo.count_messages(session_id)
    assert count == 2
