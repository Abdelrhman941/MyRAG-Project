# Stage 05 — Chat Sessions + Memory

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [ ] Users can create multiple independent chat sessions, each with persistent
      history and a rolling long-term summary — all in SQLite behind a swappable port.

## Scope (In)
- Models + Alembic migration: `chat_sessions` (id, title, summary nullable, created_at, updated_at), `chat_messages` (id, session_id FK cascade + index, role, content, created_at + index).
- `app/models/`: `ChatMessage` domain object (role, content, created_at).
- `app/infrastructure/ports.py`: `SessionRepositoryPort` (create_session, get_session, list_sessions, delete_session, add_message, list_messages, get_recent_messages(n), update_summary, update_title).
- `app/infrastructure/session_store/`: `SqliteSessionRepository` + `get_session_repository()` factory.
- `app/memory/`:
  - `load_short_term(session_id)` → last N messages.
  - `should_update_summary(message_count)` → every K turns.
  - Token-budget trimmer used at prompt time (lives here, used by Stage 06).
- Endpoints: `POST /api/v1/chat/sessions`, `GET /api/v1/chat/sessions`, `GET /api/v1/chat/sessions/{id}/messages`, `DELETE /api/v1/chat/sessions/{id}`.
- Settings: `MEMORY_SHORT_TERM_N=10`, `MEMORY_SUMMARY_EVERY_K=6`.
- Session title auto-derived from the first user message (first 60 chars) — done at message time by the service, not the router.

## Out of Scope
- ❌ The actual answering endpoint (Stage 06) — sessions exist but messages can't be "asked" yet
- ❌ LLM-based summary writing (Stage 06 adds the call; this stage provides the storage + triggers)
- ❌ Semantic memory collection
- ❌ Auth / multi-user

## Inputs / Outputs
- Session create: `{}` → `{id, title: null, created_at}`.
- Message history: ordered list `{role, content, created_at}`.

## Business Rules
- Deleting a session cascades to its messages (DB-level FK).
- `get_recent_messages(n)` returns chronological order (oldest→newest).
- One session can never read another's messages — every query is scoped by `session_id`.

## Dependencies
- Stage 01–04 patterns; Alembic.

## Error Cases
- Unknown session id → `404 not_found` (new `NotFoundError` AppError subclass).
- Empty title auto-derivation (whitespace message) → fallback title `New chat`.

## Implementation Steps
- [ ] Models + migration.
- [ ] `SessionRepositoryPort` + SQLite adapter + factory.
- [ ] `app/memory/` helpers.
- [ ] Schemas + routers under `apis/v1/chat.py`.
- [ ] Run verification commands + `alembic check`.

## Manual Verification
- [ ] Create 2 sessions; add messages to each via repository; confirm isolation.
- [ ] Delete a session → its messages are gone (cascade).
- [ ] `alembic check` passes; `alembic downgrade -1 && upgrade head` round-trips.

## Done When
- [ ] Manual verification passes with recorded output.
- [ ] Lint/format pass.
- [ ] `stage-05-summary.md` written; roadmap boxes ticked. STOP.
