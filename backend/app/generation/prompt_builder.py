from __future__ import annotations

import logging
from typing import Any

import tiktoken

from ..core.config import Settings
from ..memory.manager import MemoryManager
from ..models import RetrievalResult
from ..models.chat import ChatMessage
from .language import PromptLanguage, detect_language
from .prompts import PromptTemplates
from .prompts.ar import ARABIC_PROMPTS
from .prompts.en import ENGLISH_PROMPTS

logger = logging.getLogger(__name__)

_PROMPTS: dict[PromptLanguage, PromptTemplates] = {
    PromptLanguage.AR: ARABIC_PROMPTS,
    PromptLanguage.EN: ENGLISH_PROMPTS,
}


class PromptBuilder:
    """Build localized, token-budgeted prompts for LLM generation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def _get_prompts(self, text: str) -> PromptTemplates:
        """Select prompt templates based on the dominant language of text."""
        language = detect_language(text)
        return _PROMPTS[language]

    def build_chat_prompt(
        self,
        summary: str | None,
        chunks: list[RetrievalResult],
        history: list[ChatMessage],
        question: str,
        memory_manager: MemoryManager,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Build a localized chat prompt within the configured token budget."""
        prompts = self._get_prompts(question)
        budget = self.settings.LLM_CONTEXT_TOKEN_BUDGET

        system_base = prompts.chat_system

        if summary:
            system_base += f"\n\nPrevious Conversation Summary:\n{summary}"

        budget -= self._count_tokens(system_base)

        question_cost = self._count_tokens(question) + 4

        if budget < question_cost:
            logger.warning(
                "LLM context budget is too small for the user question",
            )
            budget = 0
        else:
            budget -= question_cost

        formatted_chunks: list[str] = []
        used_sources: list[dict[str, Any]] = []

        for index, result in enumerate(chunks, start=1):
            document_id = str(result.chunk.document_id)
            file_name = result.original_file_name
            chunk_index = result.chunk.chunk_index
            text = result.chunk.text

            chunk_str = (
                f"--- Source [{index}] ---\n"
                f"{prompts.source_file_label}: {file_name}\n"
                f"{prompts.source_context_label}: {text}\n"
            )

            chunk_tokens = self._count_tokens(chunk_str)

            if chunk_tokens > budget:
                break

            budget -= chunk_tokens
            formatted_chunks.append(chunk_str)

            used_sources.append(
                {
                    "document_id": document_id,
                    "original_file_name": file_name,
                    "chunk_index": chunk_index,
                    "page_number": result.chunk.page_number,
                    "section": result.chunk.section,
                }
            )

        if formatted_chunks:
            system_msg = (
                f"{system_base}\n\n"
                f"{prompts.source_header}\n"
                f"{'\n'.join(formatted_chunks)}"
            )
        else:
            system_msg = f"{system_base}\n\n{prompts.no_context}"

            used_sources = []

        trimmed_history = memory_manager.trim_to_budget(
            history,
            budget,
        )

        messages = [
            {
                "role": "system",
                "content": system_msg,
            }
        ]

        messages.extend(
            {
                "role": message.role,
                "content": message.content,
            }
            for message in trimmed_history
        )

        messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        return messages, used_sources

    def build_summary_prompt(
        self,
        previous_summary: str | None,
        new_messages: list[ChatMessage],
    ) -> list[dict[str, str]]:
        """Build a localized summary prompt from new conversation messages."""
        language_source = "\n".join(
            message.content for message in new_messages if message.content
        )

        prompts = self._get_prompts(
            language_source,
        )

        prompt = ""

        if previous_summary:
            prompt += f"Previous Summary:\n{previous_summary}\n\n"

        prompt += "New Messages:\n"

        for message in new_messages:
            prompt += f"{message.role.capitalize()}: {message.content}\n"

        prompt += "\nWrite the updated summary now."

        return [
            {
                "role": "system",
                "content": prompts.summary_system,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

    def build_query_rewrite_prompt(
        self,
        summary: str | None,
        recent_history: list[ChatMessage],
        current_question: str,
    ) -> list[dict[str, str]]:
        """Build a localized query-rewrite prompt."""
        prompts = self._get_prompts(current_question)

        prompt = ""

        if summary:
            prompt += f"Conversation Summary:\n{summary}\n\n"

        if recent_history:
            prompt += "Recent Messages:\n"

            for message in recent_history:
                prompt += f"{message.role.capitalize()}: {message.content}\n"

        prompt += (
            f"\n{prompts.query_rewrite_input_label}: "
            f"{current_question}\n\n"
            f"{prompts.query_rewrite_output_label}:"
        )

        return [
            {
                "role": "system",
                "content": prompts.query_rewrite_system,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
