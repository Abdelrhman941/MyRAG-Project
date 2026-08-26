# Stage 06 Summary: Generation + Chat Endpoint

## Completion Status
✅ **COMPLETED**

## What Was Completed
- **Ports & Adapters**: Implemented `LLMProviderPort` and the `OpenAICompatibleLLM` adapter using `httpx.AsyncClient` with settings (`LLM_BASE_URL`, `LLM_API_KEY`, etc.), handling timeouts and retries on 5xx errors.
- **Prompt Assembly**: Built `PromptBuilder` (`app/generation/prompt_builder.py`) to assemble the system prompt with the rolling summary and retrieved chunks, while adhering to the token budget (`LLM_CONTEXT_TOKEN_BUDGET=6000`). Chunks that don't fit are dropped, prioritizing higher-ranked chunks. "No relevant context found" branch explicitly instructs the LLM not to hallucinate sources when `RetrievalService` yields 0 chunks.
- **Token-budget Allocation**: Ensured sequential and shared token-budget allocation across the system prompt, chunks, and messages, with priority given to system instructions and chunks, followed by short-term chat history.
- **Orchestration**: Created `ChatService` (`app/services/chat_service.py`) to wire together hybrid retrieval, prompt building, LLM calling, and background summary updating.
- **Background Summarization**: A background task incrementally condenses chat history with the previous `Session.summary` string without blocking user API responses.
- **API Endpoint**: Exposed `POST /api/v1/chat/sessions/{id}/messages` taking a question and returning `{answer, sources}`. Handles errors gracefully (e.g. `404`, `502`, `400`), ensuring the user's question is persisted before hitting the LLM for truthful history.
- **Auto-titling**: Handled auto-titling a session dynamically using the first 60 characters of the user's first question.

## Deviations / Decisions
- The token-budget allocation drops messages or chunks rather than artificially truncating text, which respects document coherence. The budget is strictly passed sequentially to ensure the final context never exceeds `LLM_CONTEXT_TOKEN_BUDGET`.
- Created a Dummy LLM setup inside `verify_chat.py` because the environment does not provide a native OpenAI endpoint connection without mocking. `ChatService` handles the flow end-to-end exactly as described.

## Verification Evidence
- `verify_chat.py` successfully wired the dummy `OpenAICompatibleLLM` and the `QdrantVectorStore` adapter.
- Returned proper dummy responses demonstrating successful invocation of Prompt Builder and Chat Service logic.
- Background task successfully picked up the summary job on turn thresholds.
- Run `uv run ruff check .` and `uv run ruff format --check .` and `uv run mypy .` successfully cleanly.

## Next Steps
Proceed to **Stage 07 — User Interface (Next.js Setup)**.
