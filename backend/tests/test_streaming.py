import json
import logging
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_llm_provider
from app.infrastructure.ports import LLMProviderPort
from app.main import create_app
from app.models import ChatSession


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
async def db_session():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_streaming_endpoint(test_app, db_session):
    session = ChatSession(id=uuid.uuid4(), title="Test Session")
    db_session.add(session)
    await db_session.commit()

    class MockLLM(LLMProviderPort):
        async def generate(self, messages, temperature=0.7):
            return "Mock answer"

        async def generate_stream(self, messages, temperature=0.7):
            yield "Mock"
            yield " "
            yield "answer"

    test_app.dependency_overrides[get_llm_provider] = lambda: MockLLM()

    from app.infrastructure.ports import SessionRepositoryPort

    class MockRepo(SessionRepositoryPort):
        async def create_session(self, title=None):
            return session.id

        async def get_session(self, sid):
            return {"id": str(session.id), "title": session.title}

        async def list_sessions(self, limit=50, offset=0):
            return []

        async def delete_session(self, sid):
            pass

        async def update_title(self, sid, title):
            pass

        async def update_summary(self, sid, summary):
            pass

        async def add_message(self, sid, role, content):
            return {"id": uuid.uuid4(), "role": role, "content": content}

        async def list_messages(self, sid, limit=50, offset=0):
            return []

        async def count_messages(self, sid):
            return 1

    from app.dependencies import get_session_repository

    test_app.dependency_overrides[get_session_repository] = lambda: MockRepo()

    from app.infrastructure.ports import VectorStorePort

    class MockVectorStore(VectorStorePort):
        async def add_points(self, chunks):
            pass

        async def query(
            self, query_text, query_dense, query_sparse, limit=5, session_id=None
        ):
            return []

        async def delete_session_points(self, session_id):
            pass

    from app.dependencies import get_vector_store

    test_app.dependency_overrides[get_vector_store] = lambda: MockVectorStore()

    from app.dependencies import _get_db as get_db

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        async with client.stream(
            "POST",
            f"/api/v1/chat/sessions/{session.id}/messages/stream",
            json={"question": "What is the capital of France?"},
        ) as response:
            body = await response.aread()
            if response.status_code != 200:
                print("DEBUG BODY:", body.decode())
            assert response.status_code == 200

            text = body.decode()
            events = text.split("\n\n")
            assert "event: sources" in events[0]
            assert "event: token" in events[1]
            assert "Mock" in events[1]
            assert "event: done" in events[-2]


@pytest.mark.asyncio
async def test_streaming_mid_stream_error(test_app, db_session):
    session = ChatSession(id=uuid.uuid4(), title="Test Session")
    db_session.add(session)
    await db_session.commit()

    class ErrorMockLLM(LLMProviderPort):
        async def generate(self, messages, temperature=0.7):
            return "Mock answer"

        async def generate_stream(self, messages, temperature=0.7):
            yield "Mock"
            raise ValueError("Boom")
            yield "answer"

    test_app.dependency_overrides[get_llm_provider] = lambda: ErrorMockLLM()

    from app.infrastructure.ports import SessionRepositoryPort

    class MockRepo(SessionRepositoryPort):
        def __init__(self):
            self.messages = []

        async def create_session(self, title=None):
            return session.id

        async def get_session(self, sid):
            return {"id": str(session.id), "title": session.title}

        async def list_sessions(self, limit=50, offset=0):
            return []

        async def delete_session(self, sid):
            pass

        async def update_title(self, sid, title):
            pass

        async def update_summary(self, sid, summary):
            pass

        async def add_message(self, sid, role, content):
            self.messages.append((role, content))
            return {"id": uuid.uuid4(), "role": role, "content": content}

        async def list_messages(self, sid, limit=50, offset=0):
            return []

        async def count_messages(self, sid):
            return len(self.messages)

    repo = MockRepo()
    from app.dependencies import get_session_repository

    test_app.dependency_overrides[get_session_repository] = lambda: repo  # type: ignore

    from app.infrastructure.ports import VectorStorePort

    class MockVectorStore(VectorStorePort):
        async def add_points(self, chunks):
            pass

        async def query(
            self, query_text, query_dense, query_sparse, limit=5, session_id=None
        ):
            return []

        async def delete_session_points(self, session_id):
            pass

    from app.dependencies import get_vector_store

    test_app.dependency_overrides[get_vector_store] = lambda: MockVectorStore()

    from app.dependencies import _get_db as get_db

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        async with client.stream(
            "POST",
            f"/api/v1/chat/sessions/{session.id}/messages/stream",
            json={"question": "Fail please"},
        ) as response:
            assert response.status_code == 200
            body = await response.aread()
            text = body.decode()
            events = [e for e in text.split("\n\n") if e.strip()]
            assert "event: sources" in events[0]
            assert "event: token" in events[1]
            assert "Mock" in events[1]
            assert "event: error" in events[-1]
            assert "event: done" not in text

            # Ensure assistant message was NOT persisted completely
            assistant_messages = [m for m in repo.messages if m[0] == "assistant"]
            assert len(assistant_messages) == 1
            assert assistant_messages[0][1] == "Mock"
