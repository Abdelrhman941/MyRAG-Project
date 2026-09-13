from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks

from ..core import Settings
from ..core.exceptions import AppError
from ..generation.prompt_builder import PromptBuilder
from ..infrastructure.ports import (
    LLMProviderPort,
    SessionData,
    SessionRepositoryPort,
)
from ..memory.manager import MemoryManager
from ..models.chat import ChatMessage
from ..retrieval.service import RetrievalService
from ..schemas.chat import ChatAnswer, SourceCitation

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrate retrieval, generation, memory, and chat persistence."""

    def __init__(
        self,
        repository: SessionRepositoryPort,
        retrieval_service: RetrievalService,
        llm: LLMProviderPort,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.retrieval_service = retrieval_service
        self.llm = llm
        self.settings = settings
        self.memory = MemoryManager(repository, settings)
        self.prompt_builder = PromptBuilder(settings)

    async def _prepare(
        self,
        session_id: UUID,
        session: SessionData,
        question: str,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Prepare history, retrieval context, and generation messages."""
        history = await self.memory.load_short_term(session_id)

        if history and history[-1].role == "user":
            history = history[:-1]

        summary = session.get("summary")

        search_query = question

        if self.settings.QUERY_REWRITE_ENABLED:
            rewrite_prompt = self.prompt_builder.build_query_rewrite_prompt(
                summary,
                history[-2:] if len(history) >= 2 else history,
                question,
            )

            try:
                rewritten = await self.llm.generate(
                    rewrite_prompt,
                    temperature=0.0,
                )

                if rewritten and rewritten.strip():
                    search_query = rewritten.strip()

            except Exception as exc:
                logger.warning(
                    "Query rewrite failed; using original question: %s",
                    exc,
                )

        chunks = await self.retrieval_service.retrieve(
            search_query,
            session_id,
        )

        messages, used_sources = self.prompt_builder.build_chat_prompt(
            summary=summary,
            chunks=chunks,
            history=history,
            question=question,
            memory_manager=self.memory,
        )

        return messages, used_sources

    async def _post_answer(
        self,
        session_id: UUID,
        session: SessionData,
        question: str,
        answer_text: str,
        used_sources: list[dict[str, Any]],
        background_tasks: BackgroundTasks,
    ) -> tuple[Any, list[SourceCitation]]:
        """Persist an assistant answer and schedule memory tasks."""
        message = await self.repository.add_message(
            session_id,
            "assistant",
            answer_text,
            sources=used_sources or None,
        )

        message_count = await self.repository.count_messages(
            session_id,
        )

        if self.memory.should_update_summary(message_count):
            background_tasks.add_task(
                self._update_summary,
                session_id,
            )

        if message_count == 2 and not session.get("title"):
            background_tasks.add_task(
                self._generate_title,
                session_id,
                question,
            )

        sources = [
            SourceCitation(
                document_id=source["document_id"],
                original_file_name=source["original_file_name"],
                chunk_index=source["chunk_index"],
                page_number=source.get("page_number"),
                section=source.get("section"),
            )
            for source in used_sources
        ]

        return message, sources

    async def answer(
        self,
        session_id: UUID,
        session: SessionData,
        question: str,
        background_tasks: BackgroundTasks,
    ) -> ChatAnswer:
        """Generate and persist a complete assistant answer."""
        await self.repository.add_message(
            session_id,
            "user",
            question,
        )

        messages, used_sources = await self._prepare(
            session_id,
            session,
            question,
        )

        raw_answer_text = await self.llm.generate(
            messages,
        )

        answer_text = self._filter_citations_text(
            raw_answer_text,
            len(used_sources),
        )

        _, sources = await self._post_answer(
            session_id,
            session,
            question,
            answer_text,
            used_sources,
            background_tasks,
        )

        return ChatAnswer(
            answer=answer_text,
            sources=sources,
        )

    async def answer_stream(
        self,
        session_id: UUID,
        session: SessionData,
        question: str,
        background_tasks: BackgroundTasks,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream assistant events using the LLM provider."""
        answer_text = ""

        try:
            await self.repository.add_message(
                session_id,
                "user",
                question,
            )

            messages, used_sources = await self._prepare(
                session_id,
                session,
                question,
            )

            sources = [
                {
                    "document_id": source["document_id"],
                    "original_file_name": source["original_file_name"],
                    "chunk_index": source["chunk_index"],
                    "page_number": source.get("page_number"),
                    "section": source.get("section"),
                }
                for source in used_sources
            ]

            yield {
                "event": "sources",
                "data": sources,
            }

            async def token_generator() -> AsyncGenerator[
                dict[str, Any],
                None,
            ]:
                async for token in self.llm.generate_stream(
                    messages,
                ):
                    yield {
                        "event": "token",
                        "data": {"text": token},
                    }

            async for event in self._filter_citations_stream(
                token_generator(),
                len(used_sources),
            ):
                yield event

                if event["event"] == "token":
                    answer_text += event["data"]["text"]

            message, _ = await self._post_answer(
                session_id,
                session,
                question,
                answer_text,
                used_sources,
                background_tasks,
            )

            yield {
                "event": "done",
                "data": {
                    "message_id": str(message["id"]),
                    "finish": "stop",
                },
            }

        except asyncio.CancelledError:
            if answer_text:
                with contextlib.suppress(Exception):
                    await self.repository.add_message(
                        session_id,
                        "assistant",
                        answer_text,
                    )
            raise

        except Exception as exc:
            if isinstance(exc, AppError):
                yield {
                    "event": "error",
                    "data": {
                        "code": exc.code,
                        "message": exc.message,
                    },
                }
            else:
                yield {
                    "event": "error",
                    "data": {
                        "code": "internal_error",
                        "message": "An unexpected error occurred.",
                    },
                }

            if answer_text:
                with contextlib.suppress(Exception):
                    await self.repository.add_message(
                        session_id,
                        "assistant",
                        answer_text,
                    )

            logger.exception(
                "Streaming error for session %s",
                session_id,
            )

    async def _generate_title(
        self,
        session_id: UUID,
        first_question: str,
    ) -> None:
        """Generate a concise title for a new chat session."""
        try:
            session = await self.repository.get_session(
                session_id,
            )

            if not session or session.get("title"):
                return

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You create a concise 3-6 word title for a chat "
                        "based on the user's first message. "
                        "Output only the title."
                    ),
                },
                {
                    "role": "user",
                    "content": first_question,
                },
            ]

            title = await self.llm.generate(
                messages,
                temperature=0.5,
            )

            title = title.strip("\"'")

            await self.repository.update_title(
                session_id,
                title,
            )

        except Exception as exc:
            logger.error(
                "Failed to generate session title for %s: %s",
                session_id,
                exc,
            )

            with contextlib.suppress(Exception):
                await self.repository.update_title(
                    session_id,
                    first_question[:60],
                )

    async def _update_summary(
        self,
        session_id: UUID,
    ) -> None:
        """Update the running conversation summary."""
        try:
            session = await self.repository.get_session(
                session_id,
            )

            if not session:
                return

            total_count = await self.repository.count_messages(
                session_id,
            )

            summarized_count = session.get(
                "summarized_message_count",
                0,
            )

            short_term_n = self.settings.MEMORY_SHORT_TERM_N

            end_index = total_count - short_term_n

            if end_index <= summarized_count:
                return

            limit = end_index - summarized_count
            offset = summarized_count

            recent_messages_raw = await self.repository.get_messages(
                session_id,
                offset=offset,
                limit=limit,
            )

            if not recent_messages_raw:
                return

            recent_messages = [
                ChatMessage.model_validate(message) for message in recent_messages_raw
            ]

            previous_summary = session.get("summary")

            messages = self.prompt_builder.build_summary_prompt(
                previous_summary,
                recent_messages,
            )

            new_summary = await self.llm.generate(
                messages,
                temperature=0.3,
            )

            await self.repository.update_summary(
                session_id,
                new_summary,
                end_index,
            )

        except Exception as exc:
            logger.error(
                "Failed to update session summary for %s: %s",
                session_id,
                exc,
            )

    def _filter_citations_text(
        self,
        text: str,
        max_sources: int,
    ) -> str:
        """Strip out-of-range source citations from a complete response."""
        return re.sub(
            r"\[(\d+)\]",
            lambda match: match.group(0) if int(match.group(1)) <= max_sources else "",
            text,
        )

    async def _filter_citations_stream(
        self,
        stream: AsyncGenerator[dict[str, Any], None],
        max_sources: int,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Filter out-of-range citations while preserving streaming."""
        buffer = ""

        async for event in stream:
            if event["event"] != "token":
                yield event
                continue

            token = event["data"]["text"]
            buffer += token

            while buffer:
                index = buffer.find("[")

                if index == -1:
                    yield {
                        "event": "token",
                        "data": {"text": buffer},
                    }
                    buffer = ""
                    break

                if index > 0:
                    yield {
                        "event": "token",
                        "data": {"text": buffer[:index]},
                    }
                    buffer = buffer[index:]

                end_index = buffer.find("]")

                if end_index != -1:
                    citation = buffer[: end_index + 1]
                    buffer = buffer[end_index + 1 :]

                    match = re.match(
                        r"^\[(\d+)\]$",
                        citation,
                    )

                    if match:
                        if int(match.group(1)) <= max_sources:
                            yield {
                                "event": "token",
                                "data": {"text": citation},
                            }
                    else:
                        yield {
                            "event": "token",
                            "data": {"text": citation},
                        }

                elif len(buffer) > 6:
                    yield {
                        "event": "token",
                        "data": {"text": buffer[0]},
                    }
                    buffer = buffer[1:]
                else:
                    break

        if buffer:
            yield {
                "event": "token",
                "data": {"text": buffer},
            }
