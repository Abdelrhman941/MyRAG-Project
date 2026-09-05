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

- [ ] **1.1** Stream the upload body (no buffering)
  - Replace `await req.formData()` with raw streaming proxy
  - `sessionId` from query string, not form body
  - Update caller in use-documents.ts
  - _Verify_: upload 3 large PDFs, Next.js memory stays flat

- [ ] **1.2** Splash speed + phase text
  - MIN_SPLASH_DURATION_MS: 3000 → 900
  - Status text under loader driven by useReadiness()
  - Subtle cross-fade between texts
  - _Verify_: warm backend ≲1.5s; cold backend shows phase text

- [ ] **1.3** Refresh session list after first answer
  - On `done` event: if first exchange, call revalidateSessionsAction()
  - _Verify_: sidebar title updates after first Q&A without manual refresh

- [ ] **1.4** Phase label correction
  - `sources` event → phase = 'generating' (not 'retrieving')
  - _Verify_: phase indicator correct during streaming

- [ ] **1.5** Config cache
  - revalidate: 3600 → 60
  - _Verify_: config changes reflected within ~1 min

- [ ] **1.6** Stop the polling churn
  - Polling effect must NOT depend on `documents`
  - Read freshness from store directly inside interval callback
  - _Verify_: polling interval stable, no teardown/rebuild on each poll

- [ ] **1.7** Nits
  - confirmUpload/revertUpload: match by temp ID, not filename
  - Composer textarea: maxLength from useConfig().maxQuestionLength
  - generateMetadata: use new GET session/{id} endpoint
  - _Verify_: overlapping uploads don't eat placeholders; maxLength enforced

- [ ] **1.8** Frontend timezone hardening
  - `parseUtcDate()` helper in lib/utils.ts
  - Use in relativeDate, KB dates, message timestamps
  - _Verify_: fresh message shows "now", not "3h ago"

### Phase 1 gate: `pnpm build` + `pnpm lint` clean

---

## Phase 2 — Premium UX polish

- [ ] **2.1** Retry failed documents (KB table)
  - "Retry" ghost button (RotateCcw) on failed rows
  - Calls Phase 0.3 endpoint via server action
  - Error toast on 409/404
  - _Verify_: retry works end-to-end, toast on invalid state

- [ ] **2.2** Copy button on assistant messages
  - Hover-revealed copy icon, copies raw markdown
  - "Copied" micro-feedback
  - Disabled during streaming
  - _Verify_: copies correct content, feedback visible

- [ ] **2.3** Message timestamps
  - Small muted timestamp under each bubble
  - Using parseUtcDate(), toLocaleTimeString
  - _Verify_: correct local time displayed

- [ ] **2.4** Code blocks
  - Custom pre/code in ReactMarkdown
  - Dark surface, horizontal scroll, mono font
  - Copy-per-block button (hover)
  - Inline code pill background
  - Works in both light + dark themes
  - _Verify_: code blocks render correctly in both themes

- [ ] **2.5** Empty-state suggested prompts
  - Suggestion chips from session KB document names
  - "Summarize {file}", "What are the key points in {file}?"
  - ≥2 docs: "Compare the main ideas across my documents"
  - 0 docs: "Upload documents in the Knowledge Base to get started"
  - Clicking sends as message
  - _Verify_: chips appear with doc names, clicking sends message

- [ ] **2.6** Keyboard shortcuts
  - Ctrl/Cmd+K → New Chat
  - Ctrl/Cmd+/ → toggle sidebar
  - Ignore in input/textarea (except Cmd+K)
  - Tooltip hints on sidebar buttons
  - _Verify_: shortcuts work, tooltips visible

- [ ] **2.7** KB file-size column
  - "Size" column using file_size_bytes
  - Formatted KB/MB, one decimal
  - NULL → "—"
  - _Verify_: sizes display correctly

- [ ] **2.8** Session prefetch
  - `<Link prefetch={true}>` on sidebar session links
  - _Verify_: switching chats feels instant

### Phase 2 gate: `pnpm build` + `pnpm lint` clean

---

## Final Acceptance

- [ ] CHECKLIST.md all boxes checked with verification evidence
- [ ] Backend: ruff clean, Alembic migration applies AND downgrades
- [ ] Frontend: pnpm build + pnpm lint clean
- [ ] Citations visible on old messages after refresh
- [ ] Timestamps correct (never GMT-shifted)
- [ ] Upload doesn't balloon Next server memory
- [ ] Warm-boot splash ≲1.5s; cold boot shows phase text
- [ ] Sidebar session title auto-updates after first Q&A
- [ ] Failed doc → Retry → re-ingests; ready doc → 409 toast
- [ ] Copy, timestamps, code blocks, prompts, shortcuts, sizes, prefetch verified
- [ ] SDD updated for every contract change
