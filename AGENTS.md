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
- **Frontend:** A responsive Next.js application with intentional UX, streaming chat responses, dynamic upload tracking, and chat history.

**Development Hardware Constraints:**
- Limited VRAM (CPU inference focus). Embeddings (`BAAI/bge-m3`) run locally on CPU.
- LLM generation relies on an **external API** (OpenAI-compatible) behind a port/adapter, never a local GPU-heavy server.

---

## 3. Tech Stack

| Layer                      | Technology                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Backend Framework**      | FastAPI (async routing) + `uv` package manager                                                          |
| **ORM / Database**         | SQLAlchemy 2.x async + Alembic + SQLite (for metadata & sessions)                                       |
| **Task Queue**             | ARQ (Redis-based) for async background tasks (e.g., document chunking & embedding)                      |
| **Parsing & Chunking**     | `pypdf`, `markdown-it-py`, `python-docx` + Langchain `RecursiveCharacterTextSplitter` (standalone only) |
| **Embeddings & Vector**    | `sentence-transformers` (`BAAI/bge-m3` for CPU dense+sparse), **Qdrant** via `qdrant-client`            |
| **Frontend Framework**     | Next.js (App Router), React 19, TypeScript                                                              |
| **Frontend Styling/State** | Tailwind CSS v4, shadcn/ui, Zustand (state management), Lucide React (icons)                            |
| **Rate Limiting**          | `slowapi` (IP-based) + request-level validation                                                         |
| **Infrastructure**         | Docker & Docker Compose (Qdrant & Redis containers)                                                     |

- `package.json`, `pyproject.toml`, and lockfiles are the authoritative source for installed package versions.
- Do not assume versions from this document when they differ from the repository.

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
- Services must depend on stable ports, not concrete external adapters.
- Adapter-specific implementation details must not leak into services.
- Replacing an adapter should normally require changes only to the adapter, its configuration, and dependency wiring. Changes outside these areas require an explicit architectural reason.

---

## 6. Frontend Engineering, UX & Performance

* **Framework:** Use Next.js App Router, React Server Components, and Client Components intentionally.
* **Server/Client Boundary:** Prefer Server Components by default. Use `'use client'` only when browser APIs, local interaction, or client-side state is required.
* **State:** Use Zustand only for shared client state that must persist across components/routes. Keep component-specific state local with React state/hooks.
* **Styling:** Use Tailwind CSS v4 and existing `shadcn/ui` components. Do not introduce another styling system or UI library without explicit approval.
* **Components:** Keep components small and focused. Reuse existing components before creating new ones. Avoid premature abstractions.
* **Data Fetching:** Follow the existing repository data-fetching pattern. Do not introduce a new fetching library or architecture without explicit approval.
* **Loading UX:** Every async user-facing operation must have an intentional loading state. Prefer skeletons/placeholders where appropriate; avoid unnecessary full-page loading states.
* **Error UX:** User-facing failures must have clear recovery states. Never expose raw exceptions, stack traces, or internal implementation details.
* **Empty States:** Pages and major UI sections must handle empty, loading, success, and error states explicitly.
* **Navigation:** Client-side navigation should remain responsive. Do not introduce unnecessary client-side work, blocking requests, or repeated data fetching during route transitions.
* **Performance:** Avoid unnecessary re-renders, large client bundles, duplicated requests, and converting Server Components to Client Components without a concrete reason.
* **Accessibility:** Interactive elements must remain keyboard accessible, have appropriate labels, focus states, and semantic HTML. Do not rely on color alone to communicate state.
* **Responsive Design:** UI must work across mobile, tablet, and desktop without breaking layout or interaction.
* **Consistency:** Follow existing design tokens, spacing, typography, interaction patterns, and component conventions before creating new patterns.
* **Visual Changes:** Do not redesign unrelated UI while implementing a feature or bug fix.
* **No Unnecessary Dependencies:** Do not add packages when the existing stack can solve the requirement cleanly.
* **No Speculation:** Do not invent frontend behavior, APIs, routes, response shapes, or UX requirements. Derive them from the codebase, SDD, API contracts, and task requirements.

---

## 7. API & Database Rules

- Routers are strictly for validation and HTTP mapping. **Never query the DB or touch the filesystem from a router.**
- **Database:** SQLAlchemy 2.x `AsyncSession` everywhere. One session per request. DB constraints (e.g., `content_hash UNIQUE`) are part of correctness.
- **Uploads:** Multi-file uploads must stream to disk and process concurrently via background tasks (ARQ/Redis) to prevent memory bloat and request timeouts.
- **Error Handling:** Standardized error shape: `{"error": {"code", "message", "details?"}}`. Do not leak internal stack traces to the client.

---

## 8. Verification & QA

Never claim a task is complete without verifying the actual change.

### Required Verification

Run the smallest relevant verification set first, then the full project checks when practical.

**Backend**

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app/
uv run pytest
```

**Frontend**

```bash
cd frontend
pnpm lint
pnpm build
```

### Runtime Verification

When a change affects runtime behavior, also perform an appropriate smoke test.

Do not treat starting a development server as proof of correctness. Prefer a deterministic check such as:

* API health/request verification
* targeted integration test
* targeted frontend build/type check
* browser verification for user-facing behavior

### Verification Rules

* Verify the behavior that was actually changed, not only unrelated checks.
* Prefer targeted tests before broad verification.
* Do not skip failing checks silently.
* If a check cannot be run, state exactly why.
* Never claim a test passed unless it actually passed.
* Never assume an existing implementation is correct without inspecting the relevant code.
* When fixing a bug, verify both the original failure and the corrected behavior when practical.
* When changing contracts, APIs, schemas, or data flow, verify all affected consumers.
* Check for unintended changes with:

```bash
git status
git diff
```

### Failure Handling

If verification fails:

1. Read the actual error.
2. Identify the root cause.
3. Fix the smallest correct scope.
4. Re-run the failing verification.
5. Re-run broader checks if the change affects additional areas.

Do not apply speculative fixes, suppress errors, weaken tests, or modify unrelated code merely to make verification pass.

**Completion Rule:** A task is complete only when the implementation satisfies the requested scope and the relevant verification has passed or any unavoidable limitation has been explicitly reported.


---

## 9. Agent Operating Rules

- Read `AGENTS.md` before making changes.
- Read `docs/sdd.md` before changing architecture, APIs, persistence, or data flow.
- Inspect the existing implementation before proposing or changing it.
- Treat the repository as the source of truth for current behavior.
- Do not invent files, APIs, models, routes, dependencies, configuration, or requirements.
- Do not assume a library is installed; verify it from `pyproject.toml`, `package.json`, lockfiles, or the actual codebase.
- Do not assume an API contract; inspect the backend schema/route and its frontend consumer.
- Do not replace an existing pattern with a new pattern unless the task requires it.
- Prefer the smallest correct change that satisfies the requirement.
- Do not refactor unrelated code.
- Do not add dependencies without a concrete requirement.
- Do not change architecture or core technologies without explicit approval.
- Before modifying a file, understand how it is used by the rest of the system.
- Before removing code, verify that it is unused.
- When uncertain, inspect the repository or documentation instead of guessing.
- Keep assumptions explicit and minimal.
- After implementation, review the diff for unintended changes.
- Never claim completion without verification.
- Before making architectural or cross-layer changes, state the affected layers and verify the relevant contracts.
