from uuid import uuid4

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest

from app.core.config import Settings
from app.infrastructure.vector_store.qdrant import QdrantVectorStore


@pytest.fixture
def settings():
    return Settings(QDRANT_URL="http://dummy")


@pytest.mark.asyncio
async def test_qdrant_hybrid_search_session_filter(settings: Settings):
    store = QdrantVectorStore(settings)
    # Patch to use memory
    store.client = AsyncQdrantClient(location=":memory:")
    await store.ensure_collection()

    session_1 = uuid4()
    session_2 = uuid4()

    # We need to test upsert and query
    # Insert some dummy points
    dense_vec1 = [0.1] * 1024
    dense_vec2 = [0.9] * 1024
    sparse_vec = {1: 0.5}

    from app.models import Chunk

    doc1 = uuid4()
    doc2 = uuid4()

    chunk1 = Chunk(document_id=doc1, chunk_index=0, text="session 1 text")
    chunk2 = Chunk(document_id=doc2, chunk_index=0, text="session 2 text")

    await store.upsert_chunks(
        [chunk1],
        [dense_vec1],
        [sparse_vec],
        {"session_id": str(session_1), "original_file_name": "f1"},
    )
    await store.upsert_chunks(
        [chunk2],
        [dense_vec2],
        [sparse_vec],
        {"session_id": str(session_2), "original_file_name": "f2"},
    )

    # Now query for session 1 using hybrid search (which uses prefetch)
    res = await store.query(
        query_dense=dense_vec2,  # deliberately closer to session 2's vector
        query_sparse=sparse_vec,
        session_id=session_1,
        limit=1,
    )

    assert len(res) == 1
    assert res[0]["session_id"] == str(session_1)
    assert res[0]["text"] == "session 1 text"
