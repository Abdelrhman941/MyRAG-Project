import pytest

from app.services.chat_service import ChatService


class AsyncGeneratorMock:
    def __init__(self, items):
        self.items = items

    async def __aiter__(self):
        for item in self.items:
            yield item


@pytest.mark.asyncio
async def test_citation_filter_stream():
    service = ChatService(None, None, None, None)

    stream = AsyncGeneratorMock(
        ["This is a test ", "[1", "]", " and [2", "3] and [2", "]."]
    )

    result = ""
    async for event in service._filter_citations_stream(stream, max_sources=2):
        if event["event"] == "token":
            result += event["data"]["text"]

    assert result == "This is a test [1] and  and [2]."


@pytest.mark.asyncio
async def test_citation_filter_text():
    service = ChatService(None, None, None, None)

    text = "This is a test [1] and [23] and [2]."
    result = service._filter_citations_text(text, max_sources=2)

    assert result == "This is a test [1] and  and [2]."
