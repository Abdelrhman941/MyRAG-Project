import logging
from typing import Any

import tiktoken

from ..core.config import Settings
from ..models import RetrievalResult
from ..models.chat import ChatMessage
from ..memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class PromptBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def build_chat_prompt(
        self,
        summary: str | None,
        chunks: list[RetrievalResult],
        history: list[ChatMessage],
        question: str,
        memory_manager: MemoryManager,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """
        Builds the messages payload and returns the used sources.
        Enforces the shared LLM_CONTEXT_TOKEN_BUDGET allocation.
        """
        budget = self.settings.LLM_CONTEXT_TOKEN_BUDGET

        # 1. System Prompt Base
        system_base = (
            "You are a helpful AI assistant answering questions "
            "based on the provided documents. "
            "Always cite your sources using the chunk numbers "
            "provided (e.g. [1], [2]). "
            "If the provided documents do not contain the answer, "
            "you must state that you do not "
            "know based on the context, or answer based on "
            "general knowledge if appropriate, "
            "but clearly distinguish between document facts "
            "and general knowledge."
        )
        if summary:
            system_base += f"\n\nPrevious Conversation Summary:\n{summary}"

        if not chunks:
            system_base += (
                "\n\n[SYSTEM]: No relevant context was found in the documents. "
                "Answer based only "
                "on prior chat context or explicitly state you do "
                "not have the information."
            )

        budget -= self._count_tokens(system_base)

        # 2. Reserve budget for the user's question first
        # ~4 tokens overhead for role mapping
        question_cost = self._count_tokens(question) + 4
        if budget < question_cost:
            logger.warning("Token budget too small for the user question alone!")
            # Still append it, but we have 0 budget for anything else
            budget = 0
        else:
            budget -= question_cost

        # 3. Trim Chunks
        formatted_chunks = []
        used_sources = []
        for i, res in enumerate(chunks, 1):
            doc_id = str(res.chunk.document_id)
            file_name = res.original_file_name
            chunk_idx = res.chunk.chunk_index
            text = res.chunk.text

            chunk_str = f"--- Source [{i}] ---\nFile: {file_name}\nContext: {text}\n"
            tokens = self._count_tokens(chunk_str)

            if budget - tokens > 0:
                budget -= tokens
                formatted_chunks.append(chunk_str)
                used_sources.append(
                    {
                        "document_id": doc_id,
                        "original_file_name": file_name,
                        "chunk_index": chunk_idx,
                    }
                )
            else:
                break

        if formatted_chunks:
            system_context = "\n\nRetrieved Documents:\n" + "\n".join(formatted_chunks)
            system_msg = system_base + system_context
        else:
            system_msg = system_base
            used_sources = []

        # 4. Trim History with the REST of the budget
        trimmed_history = memory_manager.trim_to_budget(history, budget)

        messages = [{"role": "system", "content": system_msg}]
        for msg in trimmed_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Unconditionally append the user's question
        messages.append({"role": "user", "content": question})

        return messages, used_sources

    def build_summary_prompt(
        self, previous_summary: str | None, new_messages: list[ChatMessage]
    ) -> list[dict[str, str]]:
        """Prompt to incrementally condense the conversation."""
        system_msg = (
            "You are an AI assistant tasked with condensing a "
            "conversation history into a running summary. "
            "Combine the previous summary (if any) with the new "
            "messages to create a new, concise summary "
            "that retains the key facts, user preferences, and "
            "main topics discussed."
        )

        prompt = ""
        if previous_summary:
            prompt += f"Previous Summary:\n{previous_summary}\n\n"

        prompt += "New Messages:\n"
        for msg in new_messages:
            prompt += f"{msg.role.capitalize()}: {msg.content}\n"

        prompt += "\nWrite the updated summary now."

        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]
