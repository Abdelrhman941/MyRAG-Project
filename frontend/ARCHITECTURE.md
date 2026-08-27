# Frontend Architecture (Stage 08)

This document maps the product requirements from `PRODUCT.md` to a concrete frontend architecture for the RAG application.

## 1. Application Structure (Next.js App Router)
The frontend uses a Next.js App Router structure optimized for server-driven data fetching and minimal client-side state.

**Route Structure:**
- `app/layout.tsx`: Root layout, providing global styles and the Impeccable/shadcn base theme.
- `app/page.tsx`: Bootstrap route (`/`). Displays the initial splash and routes to a new session.
- `app/chat/layout.tsx`: The App Shell. Renders the Sidebar (Session List) alongside the main `children`.
- `app/chat/[session_id]/page.tsx`: The active Chat Session view (Messages + Composer).
- `app/chat/[session_id]/documents/page.tsx`: The active Session's Document management view.

**Client/Server Boundaries:**
- **Server Components (Default):** Layouts, page shells, session list fetching, message history fetching, and document list fetching. Individual message rendering remains server-first where possible.
- **Client Components (Interactive):** `PromptComposer`, `MessageFeed` (needs auto-scroll/interaction), `SidebarNavigation` (needs active state styling), `DocumentUploader`, and `DocumentManager`.

## 2. State & Data Architecture
We will **not** introduce external state libraries (Zustand, React Query, SWR) for the MVP. React native state + Next.js Server/Client boundaries are sufficient.

- **Loading Sessions:** `chat/layout.tsx` fetches sessions on the server and passes the list to a Client Sidebar component.
- **Active Session:** Inferred directly from the URL route (`params.session_id`).
- **Loading Messages:** `chat/[session_id]/page.tsx` fetches messages on the server. The Client Component takes initial messages as props and appends new ones to a local `useState` array during the current interaction.
- **Loading Documents:** `chat/[session_id]/documents/page.tsx` fetches the initial document list on the server.
- **Document Status Polling:**
  - The server-rendered document list is passed to the client.
  - The client polls approximately every 2 seconds **only** if at least one visible document has `status === "processing"`.
  - Polling stops immediately when no visible document is processing.
  - The UI does not poll continuously when the list is stable.
- **Session Deletion Fallback:**
  - Deleting the active session is **not** optimistic.
  - The UI waits for the `DELETE` request to succeed.
  - On success: If other sessions exist, navigate to the most recent remaining session. If no sessions remain, create a new session and navigate to it (do not redirect to `/`).
  - On failure: The session remains visible and the error is surfaced.

## 3. Browser ↔ FastAPI API Client Architecture
The frontend and FastAPI backend are separate applications. To maintain a strict boundary, arbitrary Client Components must not construct backend URLs directly.

We will use a minimal **BFF (Backend-For-Frontend)** approach via Next.js Server Actions and Route Handlers:
- **Configuration:** A single `BACKEND_API_URL` environment variable is used purely on the Next.js server side.
- **Server Components to FastAPI:** Server Components use native `fetch()` directly against the FastAPI URL.
- **Client Mutations:** Client Components invoke mutations (upload, delete, send message) by calling Next.js Server Actions or internal Next.js Route Handlers (`/api/...`), which securely proxy the request to FastAPI.
- **CORS Mitigation:** Because the browser communicates exclusively with the Next.js BFF, no CORS configuration is required on the FastAPI backend for browser-based preflight requests.
- **Abstraction:** We rely on simple, typed fetch wrappers in a shared `lib/api.ts` file rather than a heavy API abstraction framework.

**Endpoint Mapping (through BFF layer):**
| Feature | FastAPI Endpoint | Frontend Implementation |
|---|---|---|
| Create Session | `POST /api/v1/chat/sessions` | Server Action triggered by `app/page.tsx` or "New Chat". |
| List Sessions | `GET /api/v1/chat/sessions` | Server Component fetch in `chat/layout.tsx`. |
| Get Messages | `GET /api/v1/chat/sessions/{id}/messages` | Server Component fetch in `chat/[session_id]/page.tsx`. |
| Delete Session | `DELETE /api/v1/chat/sessions/{id}` | Server Action; handles fallback navigation on success. |
| Upload Batch | `POST /api/v1/chat/sessions/{id}/documents/batch` | Next.js Route Handler (to pass `FormData`). |
| List Documents | `GET /api/v1/chat/sessions/{id}/documents` | Server Component initial fetch + Route Handler for polling. |
| Delete Document| `DELETE /api/v1/documents/{id}` | Server Action; updates client state on success. |
| Send Message | `POST /api/v1/chat/sessions/{id}/messages` | Server Action or Route Handler. |

## 4. UI Architecture & Design System
We adhere to **shadcn/ui** primitives and minimal **21st.dev** chat inspiration.

**App Shell:**
- **Sidebar (Left):** Prominent "New Chat" button, a clean list of past sessions, and a link to the current session's documents. No complex dashboards.
- **Main Area (Right):** Fluid width, max-width constrained for reading comfort.

**Chat View:**
- **Header:** Simple session title.
- **Message List:** User messages distinct from Assistant messages. Assistant messages parse markdown. Server-first rendering where possible.
- **Sources:** Rendered as inline minimal pills at the bottom of the assistant message.
- **Composer:** Fixed to bottom, `Enter` to send, `Shift+Enter` for newline. Disabled during generation.

**Documents View:**
- Clean table/list UI.
- File dropzone/button for batch upload.
- Badges indicating `ready`, `processing`, or `failed`. Localized indeterminate spinners strictly on processing badges.
- Trash icon for deletion.

## 5. Session-Scoped Document Invariant
The UI strictly enforces the Stage 07b architecture:
- There is no "global" document library.
- The "Documents" navigation link exists *inside* the context of an active session.
- Uploads and document lists explicitly use the URL's `[session_id]`.
- Changing the URL `session_id` inherently unmounts the current document view and fetches the isolated documents for the new session.

## 6. Loading and Perceived Performance
- **First-Visit Splash (`/` bootstrap):** The `/` route acts strictly as a bootstrap. It displays a brief, purposeful branded boot state, creates a new session in the background, and redirects to `/chat/{session_id}`. No artificial delays are imposed.
- **Route Navigations:** Normal navigation to `/chat/...` **never** shows the splash screen. Navigations use standard `loading.tsx` Skeleton UIs.
- **Skeletons:** Exact-dimension placeholders matching the final layout to prevent CLS.
- **Message Generation:** A localized typing indicator or skeleton block inside the message list, while the composer remains disabled.

## 7. Design System Guidelines
- **Tokens:** Minimal color palette (monochrome emphasis, single accent color). Premium minimal visual language.
- **Components:** Rely on `shadcn/ui` buttons, dialogs, dropdowns, and skeletons.
- **21st.dev Integration:** The chat composer UX and message threading styles will be selectively adapted from the referenced 21st components, but stripped of excess tooling/plugin UI. Impeccable guidance applies.

## 8. Responsive Behavior
- **Desktop (>1024px):** Fixed Sidebar (250px), Main Content fills remaining space.
- **Tablet (768px - 1024px):** Sidebar remains fixed but collapsable via an icon toggle.
- **Mobile (<768px):** Sidebar hidden entirely behind a top-left hamburger menu. Composer padding adjusts to prevent iOS Safari keyboard occlusion.

## 9. Accessibility (a11y)
- **Focus Management:** `shadcn/ui` focus rings enabled globally.
- **Keyboard:** The chat composer captures focus cleanly. Sidebar items are fully navigable via `Tab`.
- **Aria Labels:** All icon buttons (Delete Document, Send Message, Toggle Sidebar) will have explicit `aria-label` attributes.
- **Destructive Actions:** Deleting a session requires a Shadcn `AlertDialog` confirmation.
- **Motion:** All CSS transitions wrapped in `@media (prefers-reduced-motion: no-preference)`.

## 10. Error Model & Mapping
Backend errors are gracefully intercepted:
- `not_found` → Renders a generic 404 page / redirects to a new session.
- `duplicate_document` (409) → Toast: "This document already exists in the current session."
- `too_many_files` (400) → Toast: "You can only upload a maximum of 10 files at once."
- `file_too_large` (413) → Toast: "One or more files exceed the maximum allowed file size."
- `unsupported_document_type` (422) → Toast: "Unsupported file type. Supported types are PDF, TXT, MD, and DOCX."
- `rate_limit_exceeded` (429) → Toast: "You're moving too fast. Please try again in a moment."
- `document_processing` (409) → Toast: "Cannot delete session while documents are processing."
- `llm_provider_error` (502) → Render an inline assistant error state while explicitly preserving the user's question (as the backend successfully persisted it prior to the LLM call).

## 11. Performance Principles
- Minimize Client Components (`"use client"`).
- Immediate local preview for uploaded files before the upload request finishes.
- Use Next.js layout caching.
- Prevent unnecessary re-renders of the entire message list when typing in the composer.

## 12. Deferred Real-time Capabilities
**Explicitly Deferred (Do Not Add):**
- WebSockets
- WebRTC
- WebTransport
- SSE
- Streaming LLM tokens
- Zustand / React Query
- Unrelated dashboard features

## 13. Component Inventory
- `AppShell` (Server)
- `Sidebar` (Client, handles responsive toggle)
- `SessionList` (Server)
- `ChatArea` (Server)
- `MessageFeed` (Client, handles auto-scroll)
- `MessageBubble` (Server/Client boundary)
- `SourceCitation` (Server)
- `PromptComposer` (Client, handles input & submit)
- `DocumentManager` (Client, handles polling logic)
- `DocumentUploadDropzone` (Client)
- `DocumentRow` (Client)
- `Skeletons` (SidebarSkeleton, ChatSkeleton, DocumentSkeleton)

## 14. Verification Strategy
Once implemented, verify via this manual script:
1. **Boot:** Navigating to `/` displays a brief splash, creates a session, and seamlessly redirects to `/chat/{session_id}`.
2. **Scoping:** Navigate to `/chat/{session_id}/documents`, upload "Test.pdf". Wait for processing. Return to chat, click "New Chat". Ensure "Test.pdf" is absent in the new session's `/chat/{new_session_id}/documents`.
3. **Chat:** Ask a question in the first session. Verify the markdown answer and the source citation pills appear.
4. **Error Handling:** Try uploading 11 files at once to trigger the batch limit error toast.
5. **Session Deletion Check (Processing):** Attempt to delete a session while a file is processing. Ensure the 409 toast fires and the session remains intact.
6. **Session Deletion Fallback:** Delete an active session. Verify the UI waits for success, then correctly falls back to the most recent previous session (or creates a new one).
7. **Responsiveness:** Shrink window to mobile width; ensure the sidebar collapses into a hamburger menu and the composer is usable.
8. **Accessibility:** Tab through the UI to ensure focus rings are visible on all interactive elements.
