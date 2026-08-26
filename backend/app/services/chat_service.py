import logging
from uuid import UUID

from fastapi import BackgroundTasks
from pydantic import BaseModel

from ..core import Settings
from ..core.exceptions import EmptyQueryError
from ..generation.prompt_builder import PromptBuilder
from ..infrastructure.ports import LLMProviderPort, SessionRepositoryPort
from ..memory.manager import MemoryManager
from ..retrieval.service import RetrievalService

logger = logging.getLogger(__name__)


class SourceCitation(BaseModel):
    document_id: str
    original_file_name: str
    chunk_index: int


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

    async def answer(
        self, session_id: UUID, question: str, background_tasks: BackgroundTasks
    ) -> ChatAnswer:
        if not question.strip():
            raise EmptyQueryError()

        # 1. Verify session exists
        session = await self.repository.get_session(session_id)
        if not session:
            from ..core.exceptions import NotFoundError

            raise NotFoundError(message=f"Session {session_id} not found")

        # 2. Persist user message IMMEDIATELY (truthful history)
        await self.repository.add_message(session_id, "user", question)

        # 3. Retrieve Chunks
        chunks = await self.retrieval_service.retrieve(question)

        # 4. Load memory (which now includes the user's question)
        history = await self.memory.load_short_term(session_id)

        # We skip adding the last message since we explicitly pass `question`
        # to PromptBuilder. Using slice of N-1 because we just added it.
        if history and history[-1].role == "user":
            history = history[:-1]

        summary = session.get("summary")

        # 5. Build prompt
        messages, used_sources = self.prompt_builder.build_chat_prompt(
            summary=summary,
            chunks=chunks,
            history=history,
            question=question,
            memory_manager=self.memory,
        )

        # 6. Call LLM
        answer_text = await self.llm.generate(messages)

        # 7. Persist assistant message
        await self.repository.add_message(session_id, "assistant", answer_text)

        # 8. Trigger summary update if needed
        # We need to know the total message count.
        all_msgs = await self.repository.list_messages(session_id)
        if self.memory.should_update_summary(len(all_msgs)):
            background_tasks.add_task(self._update_summary, session_id)

        # Format sources
        sources = [
            SourceCitation(
                document_id=s["document_id"],
                original_file_name=s["original_file_name"],
                chunk_index=s["chunk_index"],
            )
            for s in used_sources
        ]

        # Auto-title the session if it's the very first exchange
        if len(all_msgs) == 2 and not session.get("title"):
            title = question[:60]
            background_tasks.add_task(self.repository.update_title, session_id, title)

        return ChatAnswer(answer=answer_text, sources=sources)

    async def _update_summary(self, session_id: UUID) -> None:
        try:
            session = await self.repository.get_session(session_id)
            if not session:
                return

            previous_summary = session.get("summary")
            # Load the window we want to summarize (e.g. last K * 2 messages)
            recent_msgs = await self.memory.load_short_term(session_id)

            messages = self.prompt_builder.build_summary_prompt(
                previous_summary, recent_msgs
            )
            new_summary = await self.llm.generate(messages, temperature=0.3)

            await self.repository.update_summary(session_id, new_summary)
        except Exception as e:
            logger.error(f"Failed to update session summary for {session_id}: {e}")
