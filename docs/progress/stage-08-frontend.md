# Stage 08 — Frontend (Next.js)

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [ ] A web UI for chatting with documents and uploading files, built on the
      21st.dev `ai-chat` template, **stripped to exactly what our API needs**.

## Scope (In)
- Next.js (App Router) + **pnpm** + TailwindCSS + shadcn/ui in `frontend/`.
- Base template: https://21st.dev/?qt=ai-chat — install, then **remove every
  component, page, hook, and dependency we don't use** (demo auth, mock data,
  unused AI-provider SDKs, marketing sections). Keep only what serves the API below.
- **Chat page**: session sidebar (create/select/delete), message history per session,
  markdown-rendered answers, source citations (document name + chunk) under each answer.
- **Upload view**: multi-file picker (≤10), per-file progress/status, friendly display
  of `duplicate_document`, `file_too_large`, `unsupported_document_type`, `429`.
- **Documents view**: list with status badges (uploaded/processing/ready/failed) + delete.
- API client layer (`lib/api.ts`): one typed function per backend endpoint; base URL
  from env (`NEXT_PUBLIC_API_URL`); surfaces the standard error shape.

## Out of Scope
- ❌ Auth / accounts
- ❌ Streaming rendering of tokens (Stage 09 backend first)
- ❌ Any backend changes
- ❌ Deployment config

## Business Rules
- All server communication goes through `lib/api.ts` — components never call `fetch` directly.
- Failed uploads show the backend's error `code` mapped to a human message; unknown codes show a generic fallback.
- Empty states everywhere (no sessions, no documents, no messages).

## Dependencies
- Backend Stages 01–07 complete and running locally.
- pnpm; Node LTS.

## Error Cases
- Backend unreachable → global error toast + retry button.
- 429 on upload → "You're uploading too fast — try again later" + cooldown hint.

## Implementation Steps
- [ ] Scaffold from the template with pnpm; strip unused parts (document what was removed in the stage summary).
- [ ] `lib/api.ts` typed client.
- [ ] Chat page (sessions + messages + citations).
- [ ] Upload view with per-file results.
- [ ] Documents view with delete.
- [ ] `pnpm lint` + `pnpm build` clean.

## Manual Verification
- [ ] Full user loop: upload 3 files → wait for `ready` → create session → ask → see answer + citations → follow-up question works.
- [ ] Duplicate upload shows the friendly duplicate message.
- [ ] Delete a document from the UI → it disappears and its citations stop appearing in new answers.

## Done When
- [ ] Manual verification passes (record screenshots/output).
- [ ] `pnpm lint` and `pnpm build` pass.
- [ ] `stage-08-summary.md` written; roadmap boxes ticked. STOP.
