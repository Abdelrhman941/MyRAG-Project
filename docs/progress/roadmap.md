# Roadmap — Master Checklist

Parent: [../00-index.md](../00-index.md) · Rules: [../../AGENTS.md](../../AGENTS.md)

> How to use: find the **first unchecked stage** — that is the current scope.
> The agent works on exactly one stage, then writes its summary and ticks the boxes.
> Stage specs live beside this file as `stage-XX-*.md`. Summaries as `stage-XX-summary.md`.

**Legend:** ✅ done · 🔄 in progress · ⬜ pending

---

## Stage 00 — Foundation ✅
- [x] FastAPI app factory + logging middleware + exception handlers
- [x] Settings (pydantic-settings) + SQLite async + Alembic
- [x] `Document` model + migration
- [x] Single-file upload: streaming, SHA-256 dedup, size limit, orphan-safe
- [x] Local filesystem storage adapter
- Summary: existing codebase (pre-docs)

## Stage 01 — Batch Upload + Rate Limiting ✅
Spec: [stage-01-batch-upload.md](stage-01-batch-upload.md)
- [x] `POST /api/v1/documents/batch` — up to 10 files per request
- [x] Per-file result reporting (success / per-file error)
- [x] `slowapi` rate limit: 10 upload requests/hour/IP
- [x] DOCX added to supported types
- [x] Bounded concurrency so multi-file upload doesn't degrade
- [x] Summary written: `stage-01-summary.md`

## Stage 02 — Parsing + Chunking ✅
Spec: [stage-02-parsing-chunking.md](stage-02-parsing-chunking.md)
- [x] Pure functions for parsing PDF, TXT, MD, DOCX
- [x] Token-aware chunking (`langchain-text-splitters`)
- [x] `ParsedSegment` and `Chunk` domain models
- [x] Tested manually with sample files
- [x] Summary written: `stage-02-summary.md`

## Stage 03 — Embeddings + Qdrant Storage ✅
Spec: [stage-03-embeddings-qdrant.md](stage-03-embeddings-qdrant.md)
- [x] `app/embeddings/` — BGE-M3 lazy singleton (CPU, dense + sparse)
- [x] `VectorStorePort` + `QdrantVectorStore` adapter + factory
- [x] Qdrant collection `chunks` (dense + sparse, cosine)
- [x] `IngestionService`: parse → chunk → embed → upsert (one pass)
- [x] Wired into upload via BackgroundTasks; status → ready/failed
- [x] Summary written: `stage-03-summary.md`

## Stage 04 — Retrieval ✅
Spec: [stage-04-retrieval.md](stage-04-retrieval.md)
- [x] `app/retrieval/` — query embed → Qdrant Query API hybrid (dense+sparse, RRF fusion)
- [x] `RetrievalResult` domain object
- [x] Dense-only toggle via Settings (hybrid default)
- [x] Summary written: `stage-04-summary.md`

## Stage 05 — Chat Sessions + Memory ✅
Spec: [stage-05-chat-sessions-memory.md](stage-05-chat-sessions-memory.md)
- [x] `chat_sessions` + `chat_messages` tables + Alembic migration
- [x] `SessionRepositoryPort` + `SqliteSessionRepository` + factory
- [x] `app/memory/` — short-term window (last N) + rolling summary (every K turns)
- [x] Session CRUD endpoints
- [x] Summary written: `stage-05-summary.md`

## Stage 06 — Generation + Chat Endpoint ✅
Spec: [stage-06-generation-chat.md](stage-06-generation-chat.md)
- [x] `LLMProviderPort` + `OpenAICompatibleLLM` adapter (httpx) + factory
- [x] `app/generation/` — prompt assembly with token budget + response parsing
- [x] `ChatService` = memory + retrieval + generation, sources in response
- [x] `POST /api/v1/chat/sessions/{id}/messages`
- [x] Summary written: `stage-06-summary.md`

## Stage 07 — Document Management ✅
Spec: [stage-07-document-management.md](stage-07-document-management.md)
- [x] `GET /api/v1/documents` (list)
- [x] `DELETE /api/v1/documents/{id}` (row + file + Qdrant points)
- [x] Summary written: `stage-07-summary.md`

## Stage 07b — Backend Refactor: Session-Scoped Documents ✅
Spec: [stage-07b-session-scoping.md](stage-07b-session-scoping.md)
- [x] Reset utility (`scripts/reset_dev_data.py`)
- [x] Database migration (add `session_id`, composite unique constraint, cascade)
- [x] Route replacements (`/chat/sessions/{session_id}/documents`)
- [x] Pipeline propagation (upload → ingestion → Qdrant payload)
- [x] Retrieval filtering by `session_id`
- [x] Multi-system session deletion logic (Qdrant → FS → DB)
- [x] Summary written: `stage-07b-summary.md`

## Stage 08 — Frontend ✅
Spec: [stage-08-frontend.md](stage-08-frontend.md)
- [x] Next.js (App Router) + pnpm + TailwindCSS + shadcn/ui
- [x] Base template from 21st.dev (`ai-chat`) — **strip everything unused**, keep only what serves our API
- [x] Chat UI: session list, message history, source citations
- [x] Upload UI: multi-file picker, per-file status, dedup/rate-limit errors surfaced
- [x] Summary written: `stage-08-summary.md`

## Stage 09 — Hardening (deferred items) ⬜
Spec: [stage-09-hardening.md](stage-09-hardening.md)
- [ ] Automated test suite (pytest + httpx ASGITransport, isolated fixtures)
- [ ] Reranker `bge-reranker-v2-m3` behind a Settings flag
- [ ] Streaming responses (SSE)
- [ ] Semantic long-term memory (Qdrant `chat_memory` collection)
- [x] Summary written: `stage-09-summary.md`

---

**Current stage:** 09 — Hardening
