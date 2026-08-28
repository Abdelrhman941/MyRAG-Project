import asyncio
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.exceptions import DuplicateDocumentError
from app.infrastructure import DocumentStorage
from app.models import Base
from app.services.document_service import DocumentService


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_duplicate_batch_upload_concurrency(db_session: AsyncSession, tmp_path):
    settings = Settings()
    # Setup
    settings.UPLOAD_DIR = tmp_path
    storage = DocumentStorage()
    storage.upload_dir = tmp_path

    # We pass None for vector_store as it's not needed for upload
    service = DocumentService(
        db=db_session, storage=storage, settings=settings, vector_store=None
    )
    session_id = uuid4()

    from app.models import ChatSession

    session_obj = ChatSession(id=session_id, title="Test")
    db_session.add(session_obj)
    await db_session.commit()

    # Create an async mock file reader
    class MockFile:
        def __init__(self, name, content):
            self.filename = name
            self._content = content
            self._read = False

        async def read(self, size=-1):
            if not self._read:
                self._read = True
                return self._content
            return b""

    # Prepare 5 identical files
    files = [MockFile("test.txt", b"duplicate content") for _ in range(5)]

    # Upload them concurrently using the service's batch method
    # It should yield exactly 1 success and 4 DuplicateDocumentError
    results = await service.upload_batch(files, session_id)

    successes = [r for r in results if not isinstance(r, Exception)]
    duplicates = [r for r in results if isinstance(r, DuplicateDocumentError)]
    others = [
        r
        for r in results
        if isinstance(r, Exception) and not isinstance(r, DuplicateDocumentError)
    ]
    if others:
        print("Other errors:", others)

    assert len(successes) == 1
    assert len(duplicates) == 4
