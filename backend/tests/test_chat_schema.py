from datetime import datetime
from uuid import uuid4

from app.schemas.chat import ChatMessageResponse, ChatSessionResponse


def test_chat_message_response_timezone():
    # Naive datetime
    dt = datetime(2023, 1, 1, 12, 0, 0)

    msg = ChatMessageResponse(
        id=uuid4(),
        role="user",
        content="Hello",
        created_at=dt,
    )

    # Check that tzinfo is set to UTC
    assert msg.created_at.tzinfo is not None
    assert msg.created_at.tzinfo.tzname(None) == "UTC"

    # Check JSON serialization contains Z or +00:00
    json_dump = msg.model_dump_json()
    assert "Z" in json_dump or "+00:00" in json_dump


def test_chat_session_response_timezone():
    dt = datetime(2023, 1, 1, 12, 0, 0)

    session = ChatSessionResponse(
        id=uuid4(),
        title="Test Session",
        created_at=dt,
    )

    assert session.created_at.tzinfo is not None
    assert session.created_at.tzinfo.tzname(None) == "UTC"
