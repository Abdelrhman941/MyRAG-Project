# RAG Chatbot: Final Fixes + Premium UX Polish — CHECKLIST

> Tracks every task from Phases 0–2 of AGENT-MASTER-PROMPT.md.
> Mark `- [x]` only after running the listed verification step.

---

## Phase 0 — Backend (blocking)

- [x] **0.1** Persist message sources (citations survive refresh)
  - Alembic migration: `chat_messages.sources` JSON column
  - ChatService: persist `used_sources` in `_post_answer`
  - MessageData TypedDict: add `sources`
  - SqliteSessionRepository: update all message methods
  - ChatMessageResponse: add `sources` field
  - SDD §5 + §6 updated
  - _Verify_: send question → GET messages returns sources → survives restart

- [x] **0.2** Fix timezone serialization (timestamps 3h behind)
  - Normalize naive datetimes to UTC in session_store/sqlite.py
  - Also fix document query path
  - _Verify_: JSON `created_at` ends with `Z` or `+00:00`

- [x] **0.3** Retry endpoint for failed documents
  - `POST /api/v1/documents/{document_id}/retry`
  - 404 not_found / 409 invalid_document_state
  - Reset status → uploaded, enqueue ARQ job
  - New `InvalidDocumentStateError` exception
  - SDD §6 + §8 updated
  - _Verify_: corrupt PDF → failed → retry → re-ingests; ready doc → 409

- [x] **0.4** Small contract additions
  - `GET /api/v1/chat/sessions/{session_id}` → single SessionResponse
  - `file_size_bytes` column + migration + populate during upload
  - `max_question_length` in system config endpoint
  - SDD §5 + §6 updated
  - _Verify_: all new endpoints return expected data

### Phase 0 gate: `uv run ruff check .` + `uv run ruff format --check .` clean

---

## Phase 1 — Frontend stability fixes

- [x] **1.1** Stream the upload body
  - Replace `await req.formData()` in `api/upload/route.ts` with streaming (duplex: half)
  - Change `use-documents` to send `sessionId` in URL query params
  - _Verify_: uploading a 40MB file no longer crashes Next.js OOM

- [x] **1.2** Splash speed + phase text
  - `MIN_SPLASH_DURATION_MS = 900`
  - Add text label under loader using `useReadiness().status`
  - _Verify_: boot is faster, shows "Loading AI model..." etc

- [x] **1.3** Refresh session list after first answer
  - On the stream `done` event, if `messages.length === 2`, call a revalidate action
  - _Verify_: new chat → send msg → sidebar updates to real title instantly

- [x] **1.4** Phase label correction
  - In `use-chat-stream.ts`, when `sources` event arrives, phase should switch to `generating`, not `retrieving`
  - _Verify_: UI shows "Thinking..." instead of "Searching..." during token stream

- [x] **1.5** Config cache
  - Change config fetch revalidate from 3600 to 60
  - _Verify_: config updates propagate in 1m

- [x] **1.6** Stop the polling churn
  - Remove `documents` from `use-documents` polling effect dependencies
  - Use `useDocumentStore.getState()` inside the interval instead
  - _Verify_: React DevTools → interval is not constantly destroyed/recreated

- [x] **1.7** Nits
  - `confirmUpload` must match by ID, not filename
  - Set composer `maxLength` from config
  - Change `generateMetadata` to use GET session by ID instead of fetching all

- [x] **1.8** Frontend timezone hardening
  - Create `parseUtcDate` helper in `lib/utils.ts`
  - Use in sidebar `relativeDate`
  - _Verify_: "3h ago" becomes "now" for fresh chats_Verify_: fresh message shows "now", not "3h ago"

### Phase 1 gate: `pnpm build` + `pnpm lint` clean

---

## Phase 2 — Premium UX polish

- [x] **2.1** Retry failed documents (KB table)
  - "Retry" ghost button (RotateCcw) on failed rows
  - Calls Phase 0.3 endpoint via server action
  - Error toast on 409/404
  - _Verify_: retry works end-to-end, toast on invalid state

- [x] **2.2** Copy button on assistant messages
  - Hover-revealed copy icon, copies raw markdown
  - "Copied" micro-feedback
  - Disabled during streaming
  - _Verify_: copies correct content, feedback visible

- [x] **2.3** Message timestamps
  - Small muted timestamp under each bubble
  - Using parseUtcDate(), toLocaleTimeString
  - _Verify_: correct local time displayed

- [x] **2.4** Code blocks
  - Custom pre/code in ReactMarkdown
  - Dark surface, horizontal scroll, mono font
  - Copy-per-block button (hover)
  - Inline code pill background
  - Works in both light + dark themes
  - _Verify_: code blocks render correctly in both themes

- [x] **2.5** Empty-state suggested prompts
  - Suggestion chips from session KB document names
  - "Summarize {file}", "What are the key points in {file}?"
  - ≥2 docs: "Compare the main ideas across my documents"
  - 0 docs: "Upload documents in the Knowledge Base to get started"
  - Clicking sends as message
  - _Verify_: chips appear with doc names, clicking sends message

- [x] **2.6** Keyboard shortcuts
  - Ctrl/Cmd+K → New Chat
  - Ctrl/Cmd+/ → toggle sidebar
  - Ignore in input/textarea (except Cmd+K)
  - Tooltip hints on sidebar buttons
  - _Verify_: shortcuts work, tooltips visible

- [x] **2.7** KB file-size column
  - "Size" column using file_size_bytes
  - Formatted KB/MB, one decimal
  - NULL → "—"
  - _Verify_: sizes display correctly

- [x] **2.8** Session prefetch
  - `<Link prefetch={true}>` on sidebar session links
  - _Verify_: switching chats feels instant

### Phase 2 gate: `pnpm build` + `pnpm lint` clean

---

## Final Acceptance

- [x] CHECKLIST.md all boxes checked with verification evidence
- [x] Backend: ruff clean, Alembic migration applies AND downgrades
- [x] Frontend: pnpm build + pnpm lint clean
- [x] Citations visible on old messages after refresh
- [x] Timestamps correct (never GMT-shifted)
- [x] Upload doesn't balloon Next server memory
- [x] Warm-boot splash ≲1.5s; cold boot shows phase text
- [x] Sidebar session title auto-updates after first Q&A
- [x] Failed doc → Retry → re-ingests; ready doc → 409 toast
- [x] Copy, timestamps, code blocks, prompts, shortcuts, sizes, prefetch verified
- [x] SDD updated for every contract change

## Phase 3 — Final Fixes
- [x] Task 1: KB staleness bug
- [x] Task 2: Timezone validators
- [x] Task 3: ChatMessage sources schema
- [x] Task 4: UX polish on upload feedback
- [x] Task 5: Splash screen redesign
- [ ] Task 6: Nits (hooks, imports)
