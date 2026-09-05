# Stage 02 Summary — SSE Streaming End-to-End

Date: 2024-11-20

## What was built
- **Backend:**
  - Added `generate_stream` to `LLMProviderPort` returning an `AsyncIterator[str]`.
  - Implemented `generate_stream` in `OpenAICompatibleLLM` using `httpx.AsyncClient.stream`, manually parsing `data:` chunks and catching rate limits/errors before streaming begins.
  - Refactored `ChatService` into an `answer_stream` generator yielding Server-Sent Events (SSE) structured dicts (`sources`, `token`, `done`, `error`).
  - Added `POST /api/v1/chat/sessions/{session_id}/messages/stream` using FastAPI's `StreamingResponse`.
  - Added tests for `test_streaming.py` that verify SSE event emission, event order, and mid-stream error handling (mocking dependencies to work around FastAPI `StreamingResponse` tear-down quirks in tests).
- **Frontend:**
  - Removed old polling logic (`getRagPhaseAction` polling is kept for typing but actual chat is streamed).
  - Implemented manual fetch streaming in `message-feed.tsx` using `response.body.getReader()`.
  - Processed raw SSE text into `sources`, `token`, `done`, and `error` updates by appending directly to Next.js state.
- **Documentation:**
  - Updated `docs/sdd.md` to reflect the removal of the old `POST /messages` in favor of `/messages/stream`.

## Decisions made
- We opted to mock the `SessionRepositoryPort` and `VectorStorePort` in `tests/test_streaming.py` because `ASGITransport` + `StreamingResponse` prematurely closes dependency context managers before the body is consumed (a known quirk with `httpx` and ASGI servers in test mode).
- SSE parsing in the Next.js client is done completely manually with `TextDecoder` and string manipulation to avoid introducing external SSE dependencies, maintaining a lean dependency graph.

## Deviations from spec
- The heartbeat `: ping\n\n` is technically challenging to yield exactly every 15s when `self._prepare` executes synchronously on the event loop (as a blocking async call). While we added parsing support in the frontend, the backend currently yields events as they happen without a background heartbeat task to avoid threading complexities with the SQLite session pool.

## Verification evidence
- Test output for backend streaming behavior:
```
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /mnt/d/A/4-Projects/RAG/project_1/backend
configfile: pyproject.toml
plugins: anyio-4.14.2, langsmith-0.11.1, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collecting 2 items                                                             collected 2 items

tests/test_streaming.py ..

============================== 2 passed in 1.40s ===============================
```
- Next.js build:
```
 ✓ Compiled successfully
 ✓ Linting and checking validity of types ...
 ✓ Type checking passed.
```

## Out-of-scope items flagged
- None.

## Follow-ups for later stages
- Revisit FastAPI background task / StreamingResponse behavior if we need actual 15-second heartbeat intervals while Qdrant queries are active.

## Files touched
- `backend/app/infrastructure/ports.py` — added `generate_stream` to LLM port.
- `backend/app/infrastructure/llm_provider/openai_compatible.py` — implemented HTTP streaming for LLM API.
- `backend/app/services/chat_service.py` — added `answer_stream` as primary flow instead of `_rag_phase`.
- `backend/app/apis/v1/chat.py` — added SSE endpoint.
- `backend/tests/test_streaming.py` — added test suite for endpoint.
- `frontend/components/message-feed.tsx` — updated React state and fetch logic.
- `docs/sdd.md` — updated endpoints.
