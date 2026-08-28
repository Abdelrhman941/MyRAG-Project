import asyncio
import contextlib
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks
from pydantic import BaseModel

from ..core import Settings
from ..core.exceptions import AppError, EmptyQueryError, NotFoundError
from ..generation.prompt_builder import PromptBuilder
from ..infrastructure.ports import LLMProviderPort, SessionRepositoryPort, SessionData
from ..memory.manager import MemoryManager
from ..models.chat import ChatMessage
from ..retrieval.service import RetrievalService

logger = logging.getLogger(__name__)


class SourceCitation(BaseModel):
    document_id: str
    original_file_name: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None


class ChatAnswer(BaseModel):
    answer: str
    sources: list[SourceCitation]


class ChatService:
    def __init__(
        self,
        repository: SessionRepositoryPort,
        retrieval_service: RetrievalService,
        llm: LLMProviderPort,
        settings: Settings,
    ):
        self.repository = repository
        self.retrieval_service = retrieval_service
        self.llm = llm
        self.settings = settings
        self.memory = MemoryManager(repository, settings)
        self.prompt_builder = PromptBuilder(settings)

    async def _prepare(
        self, session_id: UUID, question: str
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]], SessionData]:

        # 1 & 2. Verify session exists and load memory concurrently
        session, history = await asyncio.gather(
            self.repository.get_session(session_id),
            self.memory.load_short_term(session_id),
        )

        if not session:
            raise NotFoundError(message=f"Session {session_id} not found")

        if history and history[-1].role == "user":
            history = history[:-1]

        summary = session.get("summary")

        # 3. Rewrite query (optional)
        search_query = question
        if self.settings.QUERY_REWRITE_ENABLED:
            rewrite_prompt = self.prompt_builder.build_query_rewrite_prompt(
                summary, history[-2:] if len(history) >= 2 else history, question
            )
            try:
                rewritten = await self.llm.generate(rewrite_prompt, temperature=0.0)
                if rewritten and rewritten.strip():
                    search_query = rewritten.strip()
            except Exception as e:
                logger.warning(f"Query rewrite failed, falling back to original: {e}")

        # 4. Retrieve Chunks
        chunks = await self.retrieval_service.retrieve(search_query, session_id)

        # 5. Build prompt
        messages, used_sources = self.prompt_builder.build_chat_prompt(
            summary=summary,
            chunks=chunks,
            history=history,
            question=question,
            memory_manager=self.memory,
        )
        return messages, used_sources, session

    async def answer(
        self, session_id: UUID, question: str, background_tasks: BackgroundTasks
    ) -> ChatAnswer:
        if not question.strip():
            raise EmptyQueryError()

        # 2. Persist user message IMMEDIATELY
        await self.repository.add_message(session_id, "user", question)

        messages, used_sources, session = await self._prepare(session_id, question)
        raw_answer_text = await self.llm.generate(messages)
        answer_text = self._filter_citations_text(raw_answer_text, len(used_sources))

        # 7. Persist assistant message
        await self.repository.add_message(session_id, "assistant", answer_text)

        # 8. Trigger summary update if needed
        msg_count = await self.repository.count_messages(session_id)
        if self.memory.should_update_summary(msg_count):
            background_tasks.add_task(self._update_summary, session_id)

        sources = [
            SourceCitation(
                document_id=s["document_id"],
                original_file_name=s["original_file_name"],
                chunk_index=s["chunk_index"],
                page_number=s.get("page_number"),
                section=s.get("section"),
            )
            for s in used_sources
        ]

        if msg_count == 2 and not session.get("title"):
            background_tasks.add_task(self._generate_title, session_id, question)

        return ChatAnswer(answer=answer_text, sources=sources)

    async def answer_stream(
        self, session_id: UUID, question: str, background_tasks: BackgroundTasks
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async generator yielding stream events for the SSE endpoint."""

        if not question.strip():
            raise EmptyQueryError()

        await self.repository.add_message(session_id, "user", question)

        try:
            # We want to yield ping while preparing if it's slow, but _prepare
            # isn't a generator. To do that, we could run _prepare in a task
            # and yield ping while waiting. But for simplicity let's just await it:
            messages, used_sources, session = await self._prepare(session_id, question)

            sources = [
                {
                    "document_id": s["document_id"],
                    "original_file_name": s["original_file_name"],
                    "chunk_index": s["chunk_index"],
                    "page_number": s.get("page_number"),
                    "section": s.get("section"),
                }
                for s in used_sources
            ]
            yield {"event": "sources", "data": sources}

            answer_text = ""

            async def token_generator() -> AsyncGenerator[dict[str, Any], None]:
                async for t in self.llm.generate_stream(messages):
                    yield {"event": "token", "data": {"text": t}}

            async for event in self._filter_citations_stream(
                token_generator(), len(used_sources)
            ):
                yield event
                if event["event"] == "token":
                    answer_text += event["data"]["text"]

            msg = await self.repository.add_message(
                session_id, "assistant", answer_text
            )

            msg_count = await self.repository.count_messages(session_id)
            if self.memory.should_update_summary(msg_count):
                background_tasks.add_task(self._update_summary, session_id)
            if msg_count == 2 and not session.get("title"):
                background_tasks.add_task(self._generate_title, session_id, question)

            yield {
                "event": "done",
                "data": {"message_id": str(msg["id"]), "finish": "stop"},
            }

        except asyncio.CancelledError:
            # Client disconnected mid-stream. Best effort save:
            if "answer_text" in locals() and answer_text:
                with contextlib.suppress(Exception):
                    await self.repository.add_message(
                        session_id, "assistant", answer_text
                    )
            raise
        except Exception as e:
            # Catch LLM errors or other errors
            if isinstance(e, AppError):
                yield {"event": "error", "data": {"code": e.code, "message": e.message}}
            else:
                yield {
                    "event": "error",
                    "data": {
                        "code": "internal_error",
                        "message": "An unexpected error occurred.",
                    },
                }

            if "answer_text" in locals() and answer_text:
                with contextlib.suppress(Exception):
                    await self.repository.add_message(
                        session_id, "assistant", answer_text
                    )
            logger.exception(f"Streaming error for session {session_id}")

    async def _generate_title(self, session_id: UUID, first_question: str) -> None:
        try:
            session = await self.repository.get_session(session_id)
            if not session or session.get("title"):
                return

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that creates a concise 3-6 word "
                        "title for a chat based on the user's first message. "
                        "Output ONLY the title, no quotes, no extra text."
                    ),
                },
                {"role": "user", "content": first_question},
            ]
            title = await self.llm.generate(messages, temperature=0.5)
            title = title.strip("\"'")
            await self.repository.update_title(session_id, title)
        except Exception as e:
            logger.error(f"Failed to generate session title for {session_id}: {e}")
            await self.repository.update_title(session_id, first_question[:60])

    async def _update_summary(self, session_id: UUID) -> None:
        try:
            session = await self.repository.get_session(session_id)
            if not session:
                return

            total_count = await self.repository.count_messages(session_id)
            summarized_count = session.get("summarized_message_count", 0)
            short_term_n = self.settings.MEMORY_SHORT_TERM_N

            end_index = total_count - short_term_n
            if end_index <= summarized_count:
                return

            limit = end_index - summarized_count
            offset = summarized_count

            recent_msgs_raw = await self.repository.get_messages(
                session_id, offset=offset, limit=limit
            )
            if not recent_msgs_raw:
                return

            recent_msgs = [ChatMessage.model_validate(m) for m in recent_msgs_raw]

            previous_summary = session.get("summary")

            messages = self.prompt_builder.build_summary_prompt(
                previous_summary, recent_msgs
            )
            new_summary = await self.llm.generate(messages, temperature=0.3)

            await self.repository.update_summary(session_id, new_summary, end_index)
        except Exception as e:
            logger.error(f"Failed to update session summary for {session_id}: {e}")

    def _filter_citations_text(self, text: str, max_sources: int) -> str:
        """Strip [n] citations from the text if n > max_sources."""

        return re.sub(
            r"\[(\d+)\]",
            lambda m: m.group(0) if int(m.group(1)) <= max_sources else "",
            text,
        )

    async def _filter_citations_stream(
        self, stream: AsyncGenerator[dict[str, Any], None], max_sources: int
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Intercept the token stream and buffer partially formed citations [n].
        This ensures the UI never receives an out-of-bounds citation like [12]
        if max_sources is 2.
        Wait, stream yields `{"event": "token", "data": {"text": "..."}}`.
        """

        buffer = ""

        async for event in stream:
            if event["event"] != "token":
                yield event
                continue

            token = event["data"]["text"]
            buffer += token

            # Keep yielding while there's no `[` or we know it's not a citation
            while buffer:
                idx = buffer.find("[")
                if idx == -1:
                    yield {"event": "token", "data": {"text": buffer}}
                    buffer = ""
                    break

                if idx > 0:
                    yield {"event": "token", "data": {"text": buffer[:idx]}}
                    buffer = buffer[idx:]

                end_idx = buffer.find("]")
                if end_idx != -1:
                    citation = buffer[: end_idx + 1]
                    buffer = buffer[end_idx + 1 :]

                    match = re.match(r"^\[(\d+)\]$", citation)
                    if match:
                        if int(match.group(1)) <= max_sources:
                            yield {"event": "token", "data": {"text": citation}}
                    else:
                        yield {"event": "token", "data": {"text": citation}}
                else:
                    if len(buffer) > 6:
                        # Flush the '[' if it's too long to be a citation like '[123456'
                        yield {"event": "token", "data": {"text": buffer[0]}}
                        buffer = buffer[1:]
                    else:
                        break

        if buffer:
            yield {"event": "token", "data": {"text": buffer}}
