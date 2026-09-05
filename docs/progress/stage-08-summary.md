# Stage 08: Frontend Experience (Summary)

**Date Completed:** 2026-08-27

## What Was Done

1. **App Shell & Design System:**
   - Initialized `shadcn/ui` (base-nova style) with Next.js 16.3, Tailwind v4, and `@base-ui/react`.
   - Set up `Toaster` (via `sonner`) and `TooltipProvider` in root layout.
   - Built `AppSidebar` with session list, active-session navigation (Chat + Knowledge Base links), session creation, and deletion with redirect fallback.

2. **Session-Scoped Document Manager (`/chat/[session_id]/documents`):**
   - `DocumentManager` client component with batch upload via Server Action → `POST /api/v1/chat/sessions/{id}/documents/batch`.
   - Polls `GET /api/v1/chat/sessions/{id}/documents` every 2 seconds **only while at least one document has status `processing` or `uploaded`**; stops immediately when list is stable.
   - Optimistic UI for uploads; per-code error toasts (`too_many_files`, `file_too_large`, `unsupported_document_type`, `duplicate_document`).
   - Enforces 10-file frontend limit before upload.

3. **Chat Feed (`/chat/[session_id]`):**
   - `MessageFeed` with `react-markdown` rendering assistant responses.
   - Optimistic user-message append; user message is never removed on LLM failure.
   - Inline assistant error state on generation failure preserving the user question.
   - Source citations rendered per message.
   - `PromptComposer` with auto-resize textarea and Enter-to-send.

4. **BFF API Layer (`lib/api.ts`):**
   - Single `"use server"` file; all exports are `async function` (no exported constants — satisfies Next.js RSC boundary).
   - Data fetchers: `getSessions`, `getMessages`, `getDocuments`.
   - Mutations: `createSessionAction`, `deleteSessionAction`, `deleteDocumentAction`, `uploadBatchAction`, `sendMessageAction`.
   - Typed against `lib/types.ts` (`Session`, `Message`, `Document`) — zero `any` usages.

5. **First-Visit Splash (`/`):**
   - Creates a new session via Server Action and redirects to `/chat/{session_id}`.
   - Never shown for `/chat/*` navigations.

6. **IDE Configuration:**
   - `.vscode/settings.json` sets `"css.lint.unknownAtRules": "ignore"` to suppress IDE CSS linter false positives for valid Tailwind v4 at-rules (`@custom-variant`, `@theme`, `@apply`, `@plugin`). These are not build errors — `pnpm build` compiles the CSS cleanly.

## API Contracts Used

| Action | Endpoint |
|--------|----------|
| List sessions | `GET /api/v1/chat/sessions` |
| Create session | `POST /api/v1/chat/sessions` |
| Delete session | `DELETE /api/v1/chat/sessions/{id}` |
| List messages | `GET /api/v1/chat/sessions/{id}/messages` |
| Send message | `POST /api/v1/chat/sessions/{id}/messages` |
| List documents | `GET /api/v1/chat/sessions/{id}/documents` |
| Batch upload | `POST /api/v1/chat/sessions/{id}/documents/batch` |
| Delete document | `DELETE /api/v1/documents/{id}` |

## Post-Implementation Bug Fixes (Debugging Pass)

1. **`SidebarMenuButton` / `asChild` TS errors** — Root cause: local `sidebar.tsx` uses `@base-ui/react`'s `useRender` pattern (`render={<element />}`), not `asChild`. Fixed in `AppSidebar`.

2. **`"use server"` non-function export** — Root cause: `export const BACKEND_URL = ...` violates the rule that `"use server"` files may only export `async function`. Fixed by removing `export` — `BACKEND_URL` is now a private module constant.

3. **`apiFetch` not exported (IDE diagnostic)** — Intentionally private. All callers are within `lib/api.ts`. `tsc` passes with 0 errors. No action needed.

4. **`Cannot find module './prompt-composer'` (IDE diagnostic)** — File exists at `components/prompt-composer.tsx`, export name and casing correct. Stale language server cache. `tsc` passes with 0 errors. No action needed.

5. **`setState` inside `useEffect`** — `DocumentManager`: replaced with React derived-state pattern (`if (initialDocuments !== prevInitial) { ... }`). `use-mobile.ts`: replaced with lazy `useState` initializer.

6. **`any` usages** — All replaced with `Document`, `Session`, `Message` from `lib/types.ts`. Catch blocks use `unknown` + structural narrowing. Zero `any` in `app/`, `components/`, `lib/`.

7. **Unused `e` binding** — Bare catch clauses (`catch (e)` → `catch`) where the error is not used.

## Final Verification Evidence (2026-08-27)

```
pnpm lint
→ exit 0  (no output — zero errors, zero warnings)

pnpm exec tsc --noEmit
→ exit 0  (no output — zero type errors)

pnpm build
→ ✓ Compiled successfully in 27.1s
→ ✓ Finished TypeScript in 54s
→ ✓ Collecting page data using 7 workers in 14.7s
→ ✓ Generating static pages (5/5) in 2.5s
→ ✓ Finalizing page optimization in 86ms
→ exit 0

Route (app)
  ○ /                               (Static)
  ○ /_not-found                     (Static)
  ƒ /chat                           (Dynamic)
  ƒ /chat/[session_id]              (Dynamic)
  ƒ /chat/[session_id]/documents    (Dynamic)
```

**Note:** `/chat` and sub-routes are correctly `ƒ (Dynamic)` — they use `revalidate: 0` to always serve fresh backend data. The `DYNAMIC_SERVER_USAGE` logged during build is Next.js's internal bailout mechanism that *classifies* the route as dynamic; it is not a build error. The build exits with code 0.

## Next Step

Stage 09 — Hardening (automated tests, reranker, streaming, semantic memory).
