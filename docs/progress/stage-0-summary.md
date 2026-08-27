# Stage 0 Summary — Model Warm-up & Readiness

Date: 2026-08-27

## What was built
- **Backend**: `main.py` converted to use a FastAPI `lifespan` context manager.
- **Backend**: `get_embedding_model(settings.EMBEDDING_MODEL)` pre-loaded during server startup in a non-blocking `asyncio.Task`.
- **Backend**: `/healthz` (returns `{"status": "ok"}`) and `/readyz` (returns readiness state based on `app.state`) endpoints added to `system.py` and included in the base router.
- **Backend Tests**: Tests for system endpoints implemented in `tests/test_system.py`.
- **Frontend**: `getReadyStatusAction` added to `lib/api.ts` to poll `/readyz` backend endpoint.
- **Frontend**: `MessageFeed` (in `components/message-feed.tsx`) state updated to poll readiness and disable `AgentChat` composer + submit button while model loads. Added banner for spinner and errors with retry button.
- **Frontend**: Added `disabled` and `placeholder` props to `AgentChatProps` (in `ui/agent-chat.tsx`) and passed them down to `InputBar`.

## Decisions made
- We created the system tests first according to TDD principles to define expected behavior for `readyz`.
- Rather than rendering the loading spinner inside the `InputBar` (which isn't cleanly supported by textareas), we added a banner overlay at the top of the chat area while keeping the text area disabled and its placeholder reading "Waiting for model...".

## Deviations from spec
- Replaced missing `agent-chat.tsx` component logic that the spec assumed would be in `components/` (it was partially in `components/ui/agent-chat.tsx` and partially in `components/message-feed.tsx`) by updating both accurately.

## Verification evidence
```bash
> uv run ruff check . && uv run pytest tests/test_system.py
All checks passed!
============================= test session starts ==============================
...
tests/test_system.py ....                                                [100%]

======================== 4 passed in 156.41s (0:02:36) =========================

> npm run lint (frontend)
> ai-chat@0.1.0 lint
> next lint

✔ No ESLint warnings or errors
```

## Out-of-scope items flagged
- None.

## Follow-ups for later stages
- Ensure subsequent integrations (like reranker models) are also pre-loaded within the `lifespan` manager instead of blocking at first request.

## Files touched
- `backend/app/main.py` — added `lifespan` and updated FastAPI initialization
- `backend/app/apis/system.py` — added `/healthz` and `/readyz` endpoints
- `backend/tests/test_system.py` — created and added test suite for endpoints
- `frontend/lib/api.ts` — added `getReadyStatusAction` polling helper
- `frontend/components/ui/agent-chat.tsx` — updated `AgentChatProps` and `InputBar` to accept `disabled` and `placeholder` properties
- `frontend/components/message-feed.tsx` — added readiness polling hooks and conditional rendering for loading/error banners
- `docs/sdd.md` — updated lifecycle sections 4 & 9
- `docs/progress/roadmap.md` — added Stage 0
