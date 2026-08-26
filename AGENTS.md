# AGENTS.md — Engineering Contract

This file is the **permanent contract** for every AI agent and every developer working on this repository.
Read it **before every session**. Follow it **without exception**.

> Reading order for any agent starting work:
> 1. This file (`AGENTS.md`)
> 2. [Software Design Document](docs/sdd.md) — the Single Source of Truth (SST)
> 3. [Roadmap](docs/progress/roadmap.md) — to find the current stage
> 4. The current stage file in `docs/progress/` — the active scope
> 5. [Diagrams](docs/diagrams/) — when touching architecture or data flow

---

## 1. Engineering Principles

- **DRY** — one source of truth; eliminate duplication at every level.
- **YAGNI** — do not implement what the current stage does not require.
- **KISS** — prefer the simplest implementation that is correct and understandable.
- **Readability** — a developer reading this for the first time must understand it quickly.
- **Maintainability** — changes in one layer must not silently break others.
- **Separation of concerns** — routing, business logic, persistence, and infrastructure are separate.
- **Explicit responsibility boundaries** — each module/class has one clear job; document it.
- **Security by default** — never trust client input for filesystem paths, IDs, or size limits.
- **Least privilege** — expose the minimum interface required; hide internals.
- **Fail clearly** — raise specific, named exceptions at layer boundaries; do not swallow errors.
- **Simple over speculative** — do not introduce abstractions for hypothetical future requirements.

**Language rule:** all code, comments, docstrings, commits, and documentation are written in **English only**.

---

## 2. Project Scope & Hardware Constraints

A **RAG (Retrieval-Augmented Generation) system**: multi-file, multi-format document
ingestion (upload → parse → chunk → embed → store), hybrid retrieval, LLM-based
question answering with chat sessions and memory.

**Development hardware (hard constraint):**
- 2 GB VRAM → **no usable GPU inference**
- 16 GB system RAM, CPU-only in practice

**Consequences:**
- No local LLM servers (Ollama, vLLM, llama.cpp, …). Generation is an **external LLM API** behind a port/adapter.
- Embeddings run locally on CPU with a model that fits comfortably in RAM (see stack table).
- Every library choice must justify its RAM/CPU footprint. Anything expecting a GPU is wrong for this project.

---

## 3. Tech Stack (fixed — do not substitute without a stage instruction)

| Concern | Use | Do NOT use |
|---|---|---|
| Backend framework | FastAPI (current official patterns) | Flask, Django |
| ORM / migrations | SQLAlchemy 2.x async + Alembic | raw SQL, `create_all` in prod |
| Metadata & chat sessions DB | SQLite (`sqlite+aiosqlite`) | PostgreSQL (until an explicit stage) |
| Parsing | `pypdf` (PDF), plain read (TXT), `markdown-it-py` (MD), `python-docx` (DOCX) | heavyweight ETL frameworks |
| Chunking | `langchain-text-splitters` (`RecursiveCharacterTextSplitter`, token-aware) — **standalone package only** | full LangChain framework |
| Embeddings | `sentence-transformers`, model `BAAI/bge-m3` (CPU, dense + sparse, ~2–3 GB RAM, loaded once as a singleton) | any model that doesn't fit ~4 GB RAM |
| Vector store | **Qdrant** via `qdrant-client`; hybrid (dense+sparse) fusion through Qdrant's native **Query API** | ChromaDB, FAISS, Pinecone, hand-rolled fusion in Python |
| Reranking | `BAAI/bge-reranker-v2-m3` (CPU) — **deferred**, only when a stage introduces it | — |
| LLM generation | External OpenAI-compatible API (provider chosen in the generation stage) behind `LLMProviderPort` | any local inference |
| Rate limiting | `slowapi` (IP-based) + request-level validation | custom middleware reinventing it |
| Agentic behavior | **Deferred**: LangGraph only, only if a stage explicitly requires multi-step reasoning | full LangChain agents |
| Frontend | Next.js (App Router) + **pnpm** + TailwindCSS + shadcn/ui; base template from 21st.dev (`ai-chat`), stripped to what we need | create-react-app, Vue |
| Package manager (backend) | `uv` | pip + requirements.txt |

**Note on "strong tools per stage":** we use the best *focused* library for each
pipeline stage (e.g. `langchain-text-splitters` for chunking, `sentence-transformers`
for embeddings, `qdrant-client` Query API for hybrid retrieval). We deliberately do
**not** adopt a monolithic RAG framework — the pipeline stages are our own thin,
explicit modules that wrap these libraries. This gives strong per-stage quality
without framework lock-in or hidden behavior.

---

## 4. Architecture Layers

```
Client (Next.js)
    ↓ HTTP
app/apis/            — HTTP routing layer (thin)
app/schemas/         — request/response contracts (Pydantic)
app/services/        — use-case orchestration (business logic)
app/parsers/         — file → ParsedSegment
app/chunking/        — ParsedSegment → Chunk
app/embeddings/      — text → dense+sparse vectors (local, in-process)
app/retrieval/       — query → ranked chunks
app/generation/      — prompt building + response parsing
app/memory/          — short-term + long-term chat memory logic
app/models/          — ORM tables + shared domain value objects
app/infrastructure/  — adapters for external systems (ports & adapters)
    ↓
SQLite / filesystem / Qdrant / external LLM API
```

**Classification rule:** a package that makes a network call to a separate running
system (Qdrant server, LLM API) belongs in `infrastructure/`. A package that
transforms data in-process using a local library/model gets its own top-level package.

See [docs/diagrams/architecture.md](docs/diagrams/architecture.md) for the full diagram.

---

## 5. Ports & Adapters Rule (swappability)

Every external system is accessed through a **Port** (a `typing.Protocol`) with at
least one **Adapter**. Services depend on ports, never on concrete adapters.

| Port | Current adapter | Swap target (future) |
|---|---|---|
| `FileStoragePort` | `LocalDocumentStorage` (filesystem) | S3 / MinIO |
| `VectorStorePort` | `QdrantVectorStore` | another vector DB |
| `LLMProviderPort` | `OpenAICompatibleLLM` (httpx) | any provider |
| `SessionRepositoryPort` | `SqliteSessionRepository` | PostgreSQL repository |

- Ports live in `app/infrastructure/ports.py`.
- Adapters live in `app/infrastructure/<system>/`.
- **Factory selection** happens in `app/dependencies.py` (one `get_*` provider per port), driven by `Settings`.
- Swapping an adapter must touch **only** the adapter + factory. No service changes.

See [docs/diagrams/component-design.md](docs/diagrams/component-design.md).

---

## 6. Layer Responsibilities

### `app/apis/`
Map HTTP requests to service calls; map results to HTTP responses.
No business logic, no SQL, no filesystem, no duplicate detection.

### `app/schemas/`
Pydantic models for API I/O only. Imports from `core/` only.

### `app/services/`
Orchestrate pipeline packages and persistence into use-cases:
`DocumentService` (upload lifecycle), `IngestionService` (parse → chunk → embed → store,
one pipeline call, no duplicate compute), `RetrievalService` (query → ranked chunks),
`ChatService` (retrieval + memory + generation). No parsing/chunking/embedding logic
itself; no FastAPI objects; no direct Qdrant/LLM calls — go through ports.

### `app/parsers/` · `app/chunking/` · `app/embeddings/`
In-process transformations. One responsibility each. Import from `models/`, `core/` only.

### `app/retrieval/`
Query embedding → vector-store port call → optional rerank. No prompt building, no LLM calls.

### `app/generation/`
Prompt templates, context assembly, response parsing. The LLM API call itself lives in `infrastructure/llm_provider/`.

### `app/memory/`
Short-term window loading, rolling summary updates, token-budget trimming.
Persistence goes through `SessionRepositoryPort`.

### `app/models/`
SQLAlchemy ORM tables + shared domain value objects (`ParsedSegment`, `Chunk`, `RetrievalResult`, `ChatMessage`). No business logic.

### `app/infrastructure/`
Adapters only: `file_storage/`, `vector_store/`, `llm_provider/`, `db/`, `session_store/`. No business rules.

### `app/core/`
Config, enums, exceptions, logging. Imports nothing from other app layers.

### `app/dependencies.py`
FastAPI dependency providers + **adapter factories**: `get_settings`, `get_db`,
`get_storage`, `get_vector_store`, `get_llm_provider`, `get_session_repository`.

---

## 7. API Rules

- Routers are thin: validate inputs → call services → return responses.
- Never query the DB or touch the filesystem from a router.
- Use `UploadFile` + `multipart/form-data` for uploads; `Annotated[list[UploadFile], File(...)]` for multi-file.
- **Multi-file upload must not degrade performance:** process files with bounded concurrency (async semaphore), stream to disk, never buffer whole files in memory.
- Use `BackgroundTasks` for post-response ingestion in the MVP.
- Consistent error shape: `{"error": {"code", "message", "details?", "request_id?"}}` (already implemented in `apis/exception_handlers.py` — keep it the single error path).

---

## 8. Database Rules

- SQLAlchemy 2.x `AsyncSession` everywhere; one session per request/background task.
- All schema changes via **Alembic** migrations; review auto-generated migrations before applying.
- DB constraints are part of correctness: `documents.content_hash UNIQUE` must hold at the DB level.
- Sessions feature stores **chat sessions and messages in SQLite** behind `SessionRepositoryPort` so it can be swapped later without service changes.

---

## 9. File Handling & Deduplication Rules

- **Never** use client-supplied filenames as filesystem paths. Physical filename is always `<document_id><ext>`.
- **Content-hash deduplication (already implemented):** SHA-256 of file content is computed while streaming; identical content under a different filename is rejected with `409 duplicate_document`. Do not weaken this.
- Stream large files; never load fully into memory.
- Wrap `OSError` at the infrastructure boundary — callers see `StorageError` only.

---

## 10. Rate Limiting Rules

- Upload endpoint: **max 10 files per request** (request validation) and **10 uploads/hour per IP** (`slowapi`).
- File size limit enforced while streaming (existing `MAX_FILE_SIZE_MB`).
- Rate-limit errors return `429` with the standard error shape.

---

## 11. Memory Rules (chat)

- **Short-term:** last N messages of the session (N from `Settings`), loaded via `SessionRepositoryPort`, trimmed to a token budget before prompt assembly.
- **Long-term:** a rolling per-session summary, updated every K turns, stored in SQLite.
- **Semantic memory (deferred):** embedding past Q&A into a dedicated Qdrant collection — only when a stage introduces it.
- Memory logic lives in `app/memory/`; persistence behind the session port. No direct SQL from `app/memory/`.

---

## 12. Testing Policy (current)

**Automated tests are deferred** to a later dedicated stage (token economy decision).
Until then:
- Each stage file lists **manual verification steps** — execute them and record the output.
- When the tests stage starts: `httpx.AsyncClient` + `ASGITransport`, `app.dependency_overrides` (no monkeypatching), isolated in-memory SQLite, `tmp_path` storage, Qdrant `:memory:`.

---

## 13. Workflow

```
Read stage file → Confirm scope → Implement → Manual verify → Lint →
Write stage summary → Update roadmap checkboxes → STOP → wait for next stage
```

- **Never** work outside the current stage's *Scope (In)*. If something out of scope seems necessary, **flag it — don't do it**.
- **Never** continue automatically to the next stage.
- After finishing a stage, the agent **must**:
  1. Write `docs/progress/stage-XX-summary.md` from [the summary template](docs/progress/_stage-summary-template.md).
  2. Tick the checkboxes in [docs/progress/roadmap.md](docs/progress/roadmap.md).
- Before implementing, the agent summarizes its understanding in 3–5 bullet points and asks about anything ambiguous.

---

## 14. Verification Commands

```bash
uv run ruff check .
uv run ruff format --check .
uv run alembic check        # when the DB schema changed
uv run uvicorn app.main:app --reload   # smoke run
```

Do not claim success without actual command output.

---

## 15. MVP Boundaries

**In scope now:** parsing, chunking, embeddings (BGE-M3), Qdrant storage, dense
retrieval (hybrid as a toggle), single-pass generation, chat sessions in SQLite,
short-term + summary memory, upload rate limiting, multi-file upload.

**Out of scope until an explicit stage instruction:**
- Authentication / multi-user
- PostgreSQL / cloud storage / Redis / Celery
- Reranking, semantic long-term memory, streaming responses
- Agentic multi-step reasoning (LangGraph)
- Automated test suite (deferred stage)
