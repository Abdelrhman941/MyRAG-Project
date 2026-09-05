# Stage 1 — Correctness & Performance Quick Wins

## Work Accomplished
- **S1.1 Qdrant hybrid prefetch filter:** Fixed a bug where candidate filtering did not scope to session_id prior to RRF fusion, resulting in incomplete queries. Added regression test.
- **S1.2 App-scoped singletons:** Initialized `QdrantVectorStore`, `httpx.AsyncClient` (for OpenAI Compatible LLM), and `DocumentStorage` within the FastAPI lifespan context manager. They are attached to `app.state` and retrieved via FastAPI `Request` dependencies to prevent recreating clients per request.
- **S1.3 Qdrant payload indexes:** Ensured payload indexes are created on `session_id` and `document_id` for efficient filtering on retrieval/deletion. Moved `QDRANT_COLLECTION` to Settings.
- **S1.4 Dead lock removal:** Removed an unnecessary `asyncio.Lock()` in `DocumentService` and relied on DB `UNIQUE` constraint for deduplication. Added test for concurrent batch upload.
- **S1.5 count_messages port:** Added `count_messages()` method in `SessionRepositoryPort` (and SQLite implementation) avoiding loading all messages into memory to check if title generation / summary is needed.
- **S1.6 `get_session_or_404` dependency:** Abstracted session existence checking into a reusable dependency injected into endpoints reducing inline code. Moved `NotFoundError` imports to the top of files.
- **S1.7 Threadpool offloading:** Offloaded CPU-heavy text parsing and token-aware chunking to `asyncio.to_thread` preventing blocking the async event loop during PDF parsing.
- **S1.8 CORS implementation:** Configured standard `CORSMiddleware` reading allowed origins from application settings (`CORS_ORIGINS`).
- **S1.9 Optimized upload streaming:** Increased file chunk read size from 8KB to 256KB during upload streaming for reduced I/O overhead.

## Architecture & SDD Updates
- Updated SDD Component Design to document app-scoped singletons in `app.state`.
- Added mentions of CPU-bound operations being offloaded to a threadpool.
- Verified and documented `content_hash` UNIQUE constraint replacing app-level lock.
- Added Stage 1 completions to Current State list.

## Deviations from Spec
- Replaced `import("uuid").UUID` type hint initially written in `dependencies.py` to a proper module-level import.
- Tested `QDRANT_URL=":memory:"` via mock in Pytest, instead of env-overrides due to pydantic-settings config parsing behavior for urls.

## Next Steps
- Stage 1 is fully complete and all tests pass. Ready to proceed to next stage.
