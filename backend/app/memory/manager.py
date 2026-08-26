from uuid import UUID

import tiktoken

from ..core.config import Settings
from ..infrastructure.ports import SessionRepositoryPort
from ..models.chat import ChatMessage


class MemoryManager:
    def __init__(self, repository: SessionRepositoryPort, settings: Settings):
        self.repository = repository
        self.settings = settings
        # Use cl100k_base for token counting (typical for OpenAI/LLMs).
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def load_short_term(self, session_id: UUID) -> list[ChatMessage]:
        """Load the last N messages from the session."""
        raw_msgs = await self.repository.get_recent_messages(
            session_id, self.settings.MEMORY_SHORT_TERM_N
        )
        return [ChatMessage.model_validate(m) for m in raw_msgs]

    def should_update_summary(self, message_count: int) -> bool:
        """Return True if a summary update is due."""
        # Update summary every K user-assistant turns (K * 2 messages).
        # Check if message_count % MEMORY_SUMMARY_EVERY_K == 0.
        k = self.settings.MEMORY_SUMMARY_EVERY_K
        if k <= 0 or message_count == 0:
            return False
        return message_count % (k * 2) == 0

    def trim_to_budget(
        self, messages: list[ChatMessage], max_tokens: int
    ) -> list[ChatMessage]:
        """Trim messages from the top (oldest) to fit within max_tokens."""
        # Count tokens backwards to keep the most recent context
        trimmed = []
        current_tokens = 0

        for msg in reversed(messages):
            # Approx tokens: tokens in content + ~4 for role/formatting.
            tokens = len(self.tokenizer.encode(msg.content)) + 4
            if current_tokens + tokens > max_tokens:
                break
            current_tokens += tokens
            trimmed.append(msg)

        trimmed.reverse()
        return trimmed
