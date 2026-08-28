from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.chat import ChatMessage
from app.retrieval.service import RetrievalService
from app.services.chat_service import ChatService


@pytest.mark.asyncio
@patch("app.retrieval.service.get_embedding_model")
async def test_retrieval_threshold_filters_out_chunks(mock_get_embedding):
    mock_store = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.RETRIEVAL_MIN_SCORE = 0.5
    mock_settings.RETRIEVAL_TOP_K = 5
    mock_settings.EMBEDDING_MODEL = "test"

    # Store returns 2 chunks, one above, one below threshold
    mock_store.query.return_value = [
        {
            "_score": 0.6,
            "document_id": str(uuid4()),
            "chunk_index": 0,
            "text": "high score",
            "original_file_name": "a.txt",
        },
        {
            "_score": 0.4,
            "document_id": str(uuid4()),
            "chunk_index": 1,
            "text": "low score",
            "original_file_name": "b.txt",
        },
    ]

    mock_model = MagicMock()
    mock_model.encode_batch.return_value = ([[0.1]], [{1: 0.1}])
    mock_get_embedding.return_value = mock_model

    retrieval = RetrievalService(mock_store, mock_settings)

    chunks = await retrieval.retrieve("test", uuid4())

    assert len(chunks) == 1
    assert chunks[0].score == 0.6


@pytest.mark.asyncio
async def test_retrieval_threshold_empty_triggers_no_context():
    # Test chat service empty branch
    mock_repo = AsyncMock()
    mock_repo.get_session.return_value = {"id": uuid4()}

    mock_retrieval = AsyncMock()
    mock_retrieval.retrieve.return_value = []  # All filtered out

    mock_llm = AsyncMock()
    mock_settings = MagicMock()

    service = ChatService(mock_repo, mock_retrieval, mock_llm, mock_settings)

    messages, used_sources, _session = await service._prepare(uuid4(), "where is it?")

    assert len(used_sources) == 0
    # PromptBuilder should use the "no context" prompt
    # We can check if "without context" or similar is in the prompt
    sys_prompt = next(m["content"] for m in messages if m["role"] == "system")
    assert (
        "No relevant context" in sys_prompt
        or "without using context" in sys_prompt.lower()
    )
