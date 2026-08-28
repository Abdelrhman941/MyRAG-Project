from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.chat import ChatMessage
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_query_rewrite_disabled():
    mock_repo = AsyncMock()
    mock_retrieval = AsyncMock()
    mock_llm = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.QUERY_REWRITE_ENABLED = False
    mock_settings.LLM_CONTEXT_TOKEN_BUDGET = 6000

    mock_repo.get_session.return_value = {"id": uuid4()}

    service = ChatService(mock_repo, mock_retrieval, mock_llm, mock_settings)

    await service._prepare(uuid4(), "where is it?")

    # Retrieval should be called with original question
    mock_retrieval.retrieve.assert_called_once_with(
        "where is it?", mock_repo.get_session.return_value["id"]
    )


@pytest.mark.asyncio
async def test_query_rewrite_enabled():
    mock_repo = AsyncMock()
    mock_retrieval = AsyncMock()
    mock_llm = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.QUERY_REWRITE_ENABLED = True
    mock_settings.LLM_CONTEXT_TOKEN_BUDGET = 6000

    session_id = uuid4()
    mock_repo.get_session.return_value = {"id": session_id}

    mock_llm.generate.return_value = "rewritten query"

    service = ChatService(mock_repo, mock_retrieval, mock_llm, mock_settings)

    await service._prepare(session_id, "where is it?")

    # LLM generate should be called for rewrite
    mock_llm.generate.assert_called_once()

    # Retrieval should be called with rewritten query
    mock_retrieval.retrieve.assert_called_once_with("rewritten query", session_id)
