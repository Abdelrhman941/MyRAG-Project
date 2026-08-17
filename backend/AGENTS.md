# Backend Engineering Contract

This file is the permanent engineering contract for all backend work.
Read it before every stage. Follow it without exception.

---

## Engineering Principles

- **DRY** — one source of truth; eliminate duplication at every level.
- **YAGNI** — do not implement what the current stage does not require.
- **KISS** — prefer the simplest implementation that is correct and understandable.
- **Readability** — a developer reading this for the first time must understand it quickly.
- **Maintainability** — changes in one layer must not silently break others.
- **Testability** — every meaningful behavior must be independently verifiable.
- **Separation of concerns** — routing, business logic, persistence, and infrastructure are separate.
- **Explicit responsibility boundaries** — each module/class has one clear job; document it.
- **Security by default** — never trust client input for filesystem paths, IDs, or size limits.
- **Least privilege** — expose the minimum interface required; hide internals.
- **Fail clearly** — raise specific, named exceptions at layer boundaries; do not swallow errors.
- **Simple over speculative** — do not introduce abstractions for hypothetical future requirements.

---

## Project Scope & Hardware Constraints

This project is a **RAG (Retrieval-Augmented Generation) backend system**: document
ingestion (upload → parse → chunk → embed → store), retrieval, and LLM-based
question answering.

**Development hardware:** 2GB VRAM (not usable for real model inference),
CPU-only in practice, 16GB system RAM.

This is a hard constraint on every model/library choice in this file. Any
suggestion that requires a GPU, expects a local model larger than ~1-2GB on
disk, or spins up a local LLM inference server (Ollama, vLLM, llama.cpp,
text-generation-webui, ...) is **wrong for this project** — do not propose it,
do not download it "just to try."

---

## Frameworks & Libraries

Explicit choices. Do not substitute or add a framework without an explicit
stage instruction — this table exists specifically so an AI coding agent
does not guess.

| Concern | Use | Do NOT use |
|---|---|---|
| RAG pipeline orchestration | Hand-written code | LangChain, LlamaIndex, Haystack |
| Embeddings + sparse vectors | `sentence-transformers`, model `BAAI/bge-m3` — CPU, dense+sparse, ~2GB RAM | Any embedding model that doesn't run comfortably in ~2-4GB RAM |
| Reranking | `BAAI/bge-reranker-v2-m3` — CPU. **Deferred**: only add when a stage explicitly introduces it | — |
| Vector store | **Qdrant** via `qdrant-client`, using its native Query API for hybrid (dense+sparse) search and fusion | ChromaDB, FAISS, Pinecone, hand-rolled client-side fusion |
| LLM generation | External LLM API. Provider is fixed in the `generation` stage — do not assume one until then | Local LLM inference of any kind |
| Multi-step agent behavior | **Deferred**: LangGraph only, only if a stage explicitly requires query decomposition / tool use / self-correction loops | Full LangChain for this |

---

## Architecture Layers

```
Client HTTP request
    ↓
app/apis/            — HTTP routing layer
    ↓
app/schemas/         — request/response contracts
    ↓
app/services/        — business/application logic (orchestrates the packages below)
    ↓
app/parsers/         — file → ParsedSegment
app/chunking/         — ParsedSegment → Chunk
app/embeddings/       — Chunk/text → vector (local model, in-process, no network call)
app/retrieval/        — query → ranked chunks
app/generation/       — prompt building + response parsing
    ↓
app/models/           — ORM tables + shared domain value objects
app/infrastructure/   — adapters for external systems
    ↓
SQLite / filesystem / Qdrant / external LLM API
```

**Classification rule:** a package that makes a network call to a separate
running system (Qdrant server, an LLM API) belongs in `infrastructure/`. A
package that transforms data in-process using a local library or local model
(parsing, chunking, embedding) gets its own top-level package next to
`parsers/`.

### `app/apis/`
**Responsibility:** Map HTTP requests to service calls; map results to HTTP responses.
**Belongs here:** Route functions, request parsing, HTTP status codes, response shaping.
**Must NOT contain:** Business logic, SQL queries, filesystem operations, duplicate detection.
**Dependency direction:** Imports from `schemas/`, `services/`, `dependencies/`, `core/`.

### `app/schemas/`
**Responsibility:** Pydantic models that define HTTP request and response shapes.
**Belongs here:** `BaseModel` subclasses for API I/O.
**Must NOT contain:** ORM queries, filesystem access, business logic.
**Dependency direction:** Imports from `core/` only.

### `app/services/`
**Responsibility:** Orchestrate the RAG pipeline packages and persistence into use-cases.
**Belongs here:** `DocumentService` (upload lifecycle), `IngestionService` (parse → chunk → embed → store, one pipeline call, no duplicate compute), `RetrievalService` (query → ranked chunks), `RAGService` (retrieval + generation).
**Must NOT contain:** Parsing/chunking/embedding/retrieval logic itself, FastAPI objects, raw SQL, filesystem calls, direct Qdrant/LLM API calls — call into the packages below instead.
**Dependency direction:** Imports from `parsers/`, `chunking/`, `embeddings/`, `retrieval/`, `generation/`, `models/`, `infrastructure/`, `core/`.

### `app/parsers/`
**Responsibility:** Convert a raw uploaded file into `ParsedSegment` objects.
**Belongs here:** Format-specific parsers (PDF/TXT/MD), OCR fallback, table extraction, text normalization.
**Must NOT contain:** Chunking, embedding, HTTP, database access.
**Dependency direction:** Imports from `models/`, `core/` only.

### `app/chunking/`
**Responsibility:** Split `ParsedSegment` objects into `Chunk` objects sized for embedding.
**Belongs here:** One chunking strategy to start (fixed-size or recursive). Do not add a second strategy speculatively.
**Must NOT contain:** Parsing, embedding, HTTP.
**Dependency direction:** Imports from `models/`, `core/` only.

### `app/embeddings/`
**Responsibility:** Convert text into vectors using a local model.
**Belongs here:** `BGE-M3` wrapper (dense + sparse output), reranker wrapper (once introduced).
**Must NOT contain:** Chunking logic, Qdrant calls, HTTP.
**Dependency direction:** Imports from `models/`, `core/` only.

### `app/retrieval/`
**Responsibility:** Turn a user query into ranked chunks.
**Belongs here:** Query embedding call, calling `infrastructure/vector_store/`, optional reranking pass.
**Must NOT contain:** Prompt building, LLM calls, HTTP.
**Dependency direction:** Imports from `embeddings/`, `infrastructure/`, `models/`, `core/`.

### `app/generation/`
**Responsibility:** Build the prompt from retrieved chunks and parse the LLM's response.
**Belongs here:** Prompt templates, response formatting/parsing.
**Must NOT contain:** The LLM API call itself (that's `infrastructure/llm_provider/`), HTTP routing.
**Dependency direction:** Imports from `infrastructure/llm_provider/`, `models/`, `core/`.

### `app/models/`
**Responsibility:** SQLAlchemy ORM table definitions (persisted document metadata) AND shared
domain value objects passed between RAG stages.
**Belongs here:** `DeclarativeBase` subclasses; dataclasses/Pydantic models — `ParsedSegment`, `Chunk`, `RetrievalResult`.
**Must NOT contain:** Business logic, Pydantic API schemas (those go in `schemas/`), route handlers.
**Dependency direction:** Imports from `core/` only.

### `app/infrastructure/`
**Responsibility:** Adapters for external systems — anything reachable only over the network or disk I/O treated as swappable.
**Belongs here:**
- `file_storage/` — `DocumentStorage` (local filesystem)
- `vector_store/` — Qdrant client wrapper (collections, upsert, hybrid query via Query API)
- `llm_provider/` — external LLM API client

**Must NOT contain:** Business rules, prompt building, chunking/embedding logic.
**Dependency direction:** Imports from `core/` only.

### `app/core/`
**Responsibility:** Application-wide shared concerns — config, enums, exceptions, logging.
**Belongs here:** `Settings`, `DocumentStatus`, `AppError` and subclasses, logging setup.
**Must NOT contain:** Route handlers, SQL queries, filesystem operations.
**Dependency direction:** Imports nothing from other app layers. Everything imports from here.

### `app/dependencies.py`
**Responsibility:** FastAPI dependency providers.
**Belongs here:** `get_settings()` (existing), `get_db()`, `get_storage()`, `get_vector_store()`, `get_llm_provider()` — added as each stage introduces them.
**Must NOT contain:** Business logic or infrastructure implementation.

### `tests/`
**Responsibility:** Automated behavioral verification.
**Belongs here:** Test modules, `conftest.py` fixtures.
**Must NOT contain:** Application code, production imports that bypass the API contract.

---

## Current Storage Architecture

| Concern | Implementation |
|---|---|
| Document metadata + lifecycle | SQLite via SQLAlchemy 2.x async |
| Original files | Local filesystem (`storage/documents/<uuid><ext>`) |
| Chunk embeddings (dense + sparse) | **Qdrant** |
| Migrations | Alembic |

**UUID-based filenames:** The physical filename on disk is always `<document_id><ext>`.
The client-supplied filename is stored as `original_file_name` in the database only.
It is never used as a filesystem path.

**`DocumentStorage`** lives in `infrastructure/file_storage/`. It is injected via
`get_storage()` in `dependencies.py` so it can be overridden in tests.

**Qdrant client** lives in `infrastructure/vector_store/`. It is injected via
`get_vector_store()` so it can be overridden in tests. Hybrid search (dense +
sparse fusion) and reranking are expressed through Qdrant's own Query API —
do not reimplement fusion logic in Python.

---

## API Rules

- Routers are thin. They validate inputs, call services, and return responses.
- Routers must not query the database directly.
- Routers must not write to the filesystem directly.
- HTTP concerns (status codes, response models) live in the API layer only.
- Business logic lives in services, not in route functions.
- Use `UploadFile` + `multipart/form-data` for file uploads.
- Use current official FastAPI patterns. Do not copy outdated tutorials.

---

## Schema Rules

There are four distinct kinds of schema in this project:

| Kind | Location | Purpose |
|------|----------|---------|
| HTTP response/request schema | `schemas/` | Exposed to client via API |
| ORM model / domain value object | `models/` | Database table mapping + cross-stage data (`ParsedSegment`, `Chunk`, `RetrievalResult`) |
| Infrastructure object | `infrastructure/` | Not a schema; adapter |
| Internal transfer object | `services/` (if needed) | Cross-boundary data |

Do not create an internal schema merely to have one.
Only introduce it when a real boundary exists that benefits from a typed contract.

Do not pass ORM models directly to response schemas. Map explicitly.

---

## Database Rules

- Use **SQLAlchemy 2.x** with `AsyncSession` throughout.
- One `AsyncSession` per request or background task. Never share across requests.
- The session is provided by `get_db()` and injected via FastAPI dependency.
- All schema changes go through **Alembic migrations**. Never `Base.metadata.create_all` in production.
- Review generated migrations before applying. Alembic auto-generate is a starting point, not a final answer.
- Database constraints (UNIQUE, NOT NULL, FK) are part of correctness, not just application-level validation.
  The `content_hash UNIQUE` constraint on `documents` must hold at the DB level.

---

## File Handling Rules

- **Never** use client-supplied filenames as filesystem paths.
- Always use the server-generated document UUID as the physical filename.
- Do not load large files fully into memory when a streaming approach suffices.
- All filesystem operations belong inside `infrastructure/file_storage/`.
- Wrap low-level `OSError` at the infrastructure boundary — callers see `StorageError` only.
- `StorageError` is defined in `core/exceptions.py`.

---

## FastAPI Rules

- Use `httpx.AsyncClient` with `ASGITransport` for async testing (official FastAPI pattern).
- Use `Annotated[list[UploadFile], File(...)]` for multi-file uploads.
- Use `BackgroundTasks` for post-response processing in the MVP.
- Override dependencies via `app.dependency_overrides` in tests, not monkeypatching.
- Do not add middleware or abstractions merely to shorten route functions.

---

## Testing Rules

- Tests verify **behavior and contracts**, not private implementation details.
- Do not test what a private method does internally unless the behavior cannot otherwise be observed.
- Avoid excessive mocking. Mock only external boundaries (filesystem failures, DB failures, Qdrant/LLM API failures).
- Fixtures must have genuine reuse value. Do not build fixture hierarchies speculatively.
- **Database isolation:** Each test uses an isolated in-memory SQLite instance.
- **Filesystem isolation:** Each test uses a `tmp_path`-backed `DocumentStorage`.
- **Vector store isolation:** Each test uses a Qdrant in-memory/local instance (`:memory:` mode) or a fake, never a shared external Qdrant.
- **HTTP isolation:** Use `app.dependency_overrides` to inject test DB and storage.
- Use **TDD** for feature work: write failing tests, then implement, then verify.
- Distinguish **expected RED** (production not implemented yet) from **test bugs**.
- Do not use `pytest.xfail` as a substitute for a real contract assertion.

---

## Code Quality Rules

- Prefer clear code over clever code.
- Do not introduce generic repositories, CRUD base classes, or abstract interfaces without a concrete reason.
- Remove dead code immediately — do not leave `...` stubs long-term.
- Name things consistently with the domain vocabulary in `docs/v1/`.
- Keep functions focused. A function that does three things should be three functions.
- Do not split files merely because they are long. Split by **responsibility**, not by line count.
- All lint/format checks must pass before marking a stage complete.

---

## Workflow

```
Design → Plan → TDD → Implement → Refactor → Verify → Document → STOP → Next Stage
```

- Do not skip verification.
- Do not claim success without actual command output.
- Do not mark a stage complete without updating `docs/v1/implementation/<stage>.md`.
- Do not continue automatically to the next stage.
- Each stage must have a corresponding file in `docs/v1/Done/`.

---

## Verification Commands

Run before marking any stage complete:

```bash
uv run python -m pytest
uv run ruff check .
uv run ruff format --check .
uv run alembic check   # when DB schema was changed
```

---

## MVP Boundaries

**Now in scope** (this and upcoming stages): document parsing, chunking,
embeddings (`BGE-M3`), Qdrant vector storage, dense retrieval, single-pass
generation.

**Still out of scope** until explicitly introduced by a separate stage instruction:

- Authentication / multi-user
- PostgreSQL / cloud storage / Redis / Celery
- Hybrid search, reranking, streaming responses — start with dense-only
  retrieval and single-pass generation; add these once quality actually needs them
- Any RAG framework (LangChain, LlamaIndex, Haystack) or agentic/multi-step
  reasoning (LangGraph) — see Frameworks & Libraries above
- Frontend
- Persistent chat sessions beyond a single request/response
