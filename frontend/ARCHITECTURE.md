# Frontend Architecture

This document describes the current Next.js App Router frontend. It complements
the system-level design in `docs/sdd.md` and must be updated with material
frontend architecture changes.

## Routes and server/client boundaries

- `app/layout.tsx` loads server configuration, establishes metadata and the
  theme/config providers.
- `app/page.tsx` renders its route-owned client splash screen from
  `app/_components/`. The splash polls `/readyz` through a server action and
  only bootstraps a session after the backend is ready.
- `app/chat/layout.tsx` is the application shell. It loads sessions on the
  server and provides the sidebar.
- `app/chat/[session_id]/page.tsx` loads message history and renders the client
  chat feed from `features/chat`.
- `app/chat/[session_id]/documents/page.tsx` loads the session-scoped document
  list and returns the custom 404 boundary when the session does not exist.
- `app/error.tsx`, `app/chat/error.tsx`, and `app/not-found.tsx` provide
  consistent failure and not-found views.

Pages and layouts remain Server Components where possible. Interactive
components—the splash, sidebar, document manager, message feed, and composer—
are Client Components.

## Data and state

- `lib/api.ts` is the server-side FastAPI client and holds server actions for
  session and document mutations.
- `lib/backend-url.ts` centralizes the backend origin for server-rendered
  requests and route handlers. Prefer `BACKEND_API_URL`; the public API URL is
  a fallback for local development.
- `app/api/upload/route.ts` is the internal multipart upload proxy. Browser
  code sends files only to this route.
- `lib/api/stream.ts` is the sole browser SSE client. It uses
  `NEXT_PUBLIC_API_URL` because an abortable streamed response must be consumed
  by the browser.
- Zustand stores session-scoped document lists. `features/documents/useDocuments`
  owns optimistic upload/delete state, shares document requests between the
  sidebar and manager, and polls only while documents are `uploaded` or
  `processing`.
- `features/chat/useChatStream` owns optimistic messages, one `AbortController` per answer,
  SSE-derived phase, and partial-answer preservation after Stop.
- `useReadiness` owns the fixed two-second readiness polling used by both the
  splash screen and chat warm-up state.

## API mapping

| Feature | Backend endpoint | Frontend path |
| --- | --- | --- |
| Readiness | `GET /readyz` | `getReadyStatusAction` / `useReadiness` |
| Sessions | `/api/v1/chat/sessions` | server components and server actions |
| Messages | `/api/v1/chat/sessions/{id}/messages` | server component history |
| Streaming answer | `POST /api/v1/chat/sessions/{id}/messages/stream` | `streamChatAnswer` only |
| Documents | `/api/v1/chat/sessions/{id}/documents` | server history plus `useDocuments` |
| Batch upload | `POST .../documents/batch` | `/api/upload` route handler |
| Delete document | `DELETE /api/v1/documents/{id}` | server action |

## UI behavior

Feature components live with their related state and interaction logic:

- `features/chat/` contains the stream hook, chat feed, chat renderer, and
  citation chips.
- `features/documents/` contains the document store, document hook, and
  document manager.
- `components/layout/` contains shell-only UI, and `components/providers/`
  contains app-wide providers.
- `components/ui/` is reserved for reusable Base UI/shadcn-style primitives.

- The sidebar shows the active workspace, complete document list, sessions,
  destructive-action confirmation, and a persisted light/dark theme toggle.
- Citations are structured `SourceCitation` data. They are rendered as
  deduplicated chips only after assistant text starts, never appended to
  markdown content.
- Assistant text and completed message items are memoized; the in-flight
  assistant message uses a stable React key throughout the stream.
- Document upload validation uses limits supplied by `useConfig()`. Drag and
  drop and the picker follow the same validation path.
- All destructive operations use `AlertDialog`; session deletion retains the
  backend's force-delete recovery flow for processing documents.

## Operational conventions

- Use `BACKEND_API_URL` for server-to-server calls. Set
  `NEXT_PUBLIC_API_URL` when the browser needs to consume SSE from a separate
  backend origin.
- Do not add a second stream client or reintroduce `rag-phase` polling.
- Keep document lists session-scoped. A missing session must resolve to the
  custom not-found UI, not an empty workspace.
- Keep browser-only state in hooks/components and shared server operations in
  `lib/`; do not use custom DOM events for state synchronization.
