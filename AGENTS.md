# AGENTS.md — Engineering Contract

This file is the **permanent contract** for every AI agent and every developer working on this repository.
Read it **before every session**. Follow it **without exception**.

> Reading order for any agent starting work:
> 1. This file (`AGENTS.md`)
> 2. [Software Design Document](docs/sdd.md) — the Single Source of Truth (SST)
> 3. [Diagrams](docs/diagrams/) — when touching architecture or data flow

---

## 1. Engineering Principles & Clean Architecture

- **Clean Architecture** — The system is strictly divided into layers. Dependencies only point inward.
- **SOLID Principles** — Classes and functions must have single responsibilities, be open for extension but closed for modification, and depend on abstractions (Ports), not concretions (Adapters).
- **DRY & YAGNI** — One source of truth; eliminate duplication. Do not implement what is not required today.
- **KISS** — Prefer the simplest implementation that is correct and understandable.
- **Readability & Maintainability** — A developer reading this for the first time must understand it quickly. Changes in one layer must not silently break others.
- **Separation of Concerns** — Routing, business logic, persistence, and infrastructure are completely decoupled.
- **Fail Clearly** — Raise specific, named exceptions at layer boundaries. Do not swallow errors.

**Language Rule:** All code, comments, docstrings, commits, and documentation are written in **English only**.

---

## 2. Project Scope & Architecture

A production-grade **RAG (Retrieval-Augmented Generation) system**:
- **Backend:** Document ingestion (upload → parse → chunk → embed → store), hybrid retrieval, LLM-based question answering, async task queues for processing, chat sessions, and memory.
- **Frontend:** A highly polished, responsive Next.js application that streams chat responses, tracks uploads dynamically, and manages chat history.

**Development Hardware Constraints:**
- Limited VRAM (CPU inference focus). Embeddings (`BAAI/bge-m3`) run locally on CPU.
- LLM generation relies on an **external API** (OpenAI-compatible) behind a port/adapter, never a local GPU-heavy server.

---

## 3. Tech Stack

| Layer                       | Technology                                                                                                               |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Backend Framework**       | FastAPI (async routing) + `uv` package manager                                                                           |
| **ORM / Database**          | SQLAlchemy 2.x async + Alembic + SQLite (for metadata & sessions)                                                        |
| **Task Queue**              | ARQ (Redis-based) for async background tasks (e.g., document chunking & embedding)                                       |
| **Parsing & Chunking**      | `pypdf`, `markdown-it-py`, `python-docx` + Langchain `RecursiveCharacterTextSplitter` (standalone only)                  |
| **Embeddings & Vector**     | `sentence-transformers` (`BAAI/bge-m3` for CPU dense+sparse), **Qdrant** via `qdrant-client`                             |
| **Frontend Framework**      | Next.js 15+ (App Router), React 19, TypeScript                                                                           |
| **Frontend Styling/State**  | Tailwind CSS v4, shadcn/ui, Zustand (state management), Lucide React (icons)                                             |
| **Rate Limiting**           | `slowapi` (IP-based) + request-level validation                                                                          |
| **Infrastructure**          | Docker & Docker Compose (Qdrant & Redis containers)                                                                      |

*(Note: Do not substitute these core technologies without explicit user permission. E.g., No Prisma, no Django, no full LangChain agent framework).*

---

## 4. Architecture Layers (Backend)

```text
Client (Next.js)
    ↓ HTTP
app/apis/            — HTTP routing layer (thin, maps req/res)
app/schemas/         — Request/response contracts (Pydantic)
app/services/        — Use-case orchestration (business logic)
app/parsers/         — File → ParsedSegment
app/chunking/        — ParsedSegment → Chunk
app/embeddings/      — Text → dense+sparse vectors
app/retrieval/       — Query → ranked chunks
app/generation/      — Prompt building + response parsing
app/memory/          — Chat memory logic
app/models/          — ORM tables + domain value objects
app/infrastructure/  — Adapters for external systems (ports & adapters)
```

**Classification Rule:** Any package making a network call to a separate system (Qdrant, Redis, LLM API) belongs in `infrastructure/`. Data transformations happen in top-level domain packages.

---

## 5. Ports & Adapters (Swappability)

Every external system is accessed through a **Port** (`typing.Protocol`) with at least one **Adapter**.
Services **must** depend on ports, never on concrete adapters.

- **Ports** live in `app/infrastructure/ports.py`.
- **Adapters** live in `app/infrastructure/<system>/` (e.g., `vector_store`, `llm_provider`).
- **Factories** in `app/dependencies.py` inject the right adapter.
- Swapping an adapter must touch **only** the adapter + factory. No service changes.

---

## 6. Frontend Rules & UX

- **UI/UX Polish:** The frontend must feel like a premium, production-ready product. Ensure transitions, empty states, and loading states (spinners, skeletons) are seamless.
- **State Management:** Use `Zustand` for global state (e.g., chat sessions, uploads) and React hooks for local UI state.
- **Styling:** Strictly use **Tailwind v4** and `shadcn/ui`. Keep components modular.
- **Client/Server Components:** Maintain clear boundaries between React Server Components (RSC) and Client Components (`'use client'`).

---

## 7. API & Database Rules

- Routers are strictly for validation and HTTP mapping. **Never query the DB or touch the filesystem from a router.**
- **Database:** SQLAlchemy 2.x `AsyncSession` everywhere. One session per request. DB constraints (e.g., `content_hash UNIQUE`) are part of correctness.
- **Uploads:** Multi-file uploads must stream to disk and process concurrently via background tasks (ARQ/Redis) to prevent memory bloat and request timeouts.
- **Error Handling:** Standardized error shape: `{"error": {"code", "message", "details?"}}`. Do not leak internal stack traces to the client.

---

## 8. Verification & QA

Always verify your work before claiming a task is done:
```bash
# Backend checks
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app/
uv run uvicorn app.main:app --reload

# Frontend checks
cd frontend
pnpm lint
pnpm build
```
**Never blindly guess.** If an error occurs, use systematic debugging to trace root causes rather than applying band-aid fixes.
