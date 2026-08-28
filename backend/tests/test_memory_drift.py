from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.chat import ChatMessage
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_update_summary_slices_correctly():
    # Setup mocks
    mock_repo = AsyncMock()
    mock_retrieval = AsyncMock()
    mock_llm = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.MEMORY_SHORT_TERM_N = 2

    session_id = uuid4()

    # Fake session with summarized_message_count
    mock_repo.get_session.return_value = {
        "id": session_id,
        "summary": "Old summary",
        "summarized_message_count": 2,
    }

    # 6 messages total in DB
    mock_repo.count_messages.return_value = 6

    # The slice to summarize should be [2 : 6 - 2] = [2:4]
    # (i.e. messages 3 and 4, which are index 2 and 3)
    # Let's mock repo.get_messages(session_id, offset=2, limit=2)
    mock_repo.get_messages.return_value = [
        {
            "id": uuid4(),
            "role": "user",
            "content": "turn 2 user",
            "created_at": None,
            "session_id": session_id,
        },
        {
            "id": uuid4(),
            "role": "assistant",
            "content": "turn 2 asst",
            "created_at": None,
            "session_id": session_id,
        },
    ]

    mock_llm.generate.return_value = "New summary"

    service = ChatService(mock_repo, mock_retrieval, mock_llm, mock_settings)

    with patch.object(
        service.prompt_builder, "build_summary_prompt"
    ) as mock_build_prompt:
        await service._update_summary(session_id)

        # Verify the slice was requested from DB
        mock_repo.get_messages.assert_called_once_with(session_id, offset=2, limit=2)

        # Verify prompt builder was called with those 2 messages
        args, _kwargs = mock_build_prompt.call_args
        assert args[0] == "Old summary"
        assert len(args[1]) == 2
        assert args[1][0].content == "turn 2 user"
        assert args[1][1].content == "turn 2 asst"

        # Verify summarized_message_count was updated to 4
        mock_repo.update_summary.assert_called_once_with(session_id, "New summary", 4)
