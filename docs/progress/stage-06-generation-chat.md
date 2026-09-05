# Stage 06 — Generation + Chat Endpoint

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [x] `POST /api/v1/chat/sessions/{id}/messages` answers questions using retrieved
      chunks + session memory, via an external LLM behind a swappable port.

## Scope (In)
- `app/infrastructure/ports.py`: `LLMProviderPort` (`generate(messages) -> str`).
- `app/infrastructure/llm_provider/`: `OpenAICompatibleLLM` — `httpx.AsyncClient`,
  base URL + API key + model from Settings; timeout and one retry on 5xx.
- `app/generation/`: prompt assembly —
  `system prompt → rolling summary → retrieved chunks (numbered, cited) → last N messages → question`,
  trimmed to `LLM_CONTEXT_TOKEN_BUDGET` using the Stage-05 trimmer; response parsing.
- `app/services/chat_service.py`: `ChatService.answer(session_id, question)` =
  load memory → retrieve → assemble → LLM → persist both messages → schedule summary update every K turns (BackgroundTasks).
- Endpoint: `POST /api/v1/chat/sessions/{id}/messages` → `{answer, sources: [{document_id, original_file_name, chunk_index}]}`.
- Settings: `LLM_BASE_URL`, `LLM_API_KEY` (env only, never committed), `LLM_MODEL`, `LLM_CONTEXT_TOKEN_BUDGET=6000`, `LLM_TIMEOUT_S=60`.
- Rolling summary writer: LLM call condensing old window + previous summary (background, never blocks the response).

## Out of Scope
- ❌ Streaming responses (Stage 09)
- ❌ Reranking (Stage 09)
- ❌ Provider failover across multiple LLM vendors
- ❌ Frontend

## Inputs
- Path: `session_id`. Body: `{ "question": string }`.

## Outputs
- `200` → `{answer, sources}`.
- `404 not_found` unknown session · `502 llm_provider_error` LLM failure · `400 empty_query` blank question.

## Business Rules
- Sources are mandatory — every answer returns the chunks it was built from.
- User message is persisted **before** the LLM call; on LLM failure the history still shows the question (truthful history).
- Summary updates run only every K turns and always in background.
- Prompt never exceeds `LLM_CONTEXT_TOKEN_BUDGET`; chunks are dropped lowest-score-first when trimming.

## Dependencies
- Stages 04 + 05 complete. A reachable OpenAI-compatible endpoint.

## Error Cases
- LLM timeout/5xx after retry → `502 llm_provider_error` (standard shape).
- Session missing → 404.
- No retrieved chunks → answer still generated but with an explicit "no relevant context found" system-prompt branch (never fabricate sources — `sources: []`).

## Implementation Steps
- [x] `LLMProviderPort` + adapter + factory + Settings fields.
- [x] `app/generation/` prompt builder + parser.
- [x] `ChatService` orchestration + summary trigger.
- [x] Router + schemas.
- [x] Run verification commands.

## Manual Verification
- [x] Ask about an ingested document → coherent answer with correct sources.
- [x] Follow-up question ("tell me more about it") → resolved via short-term memory.
- [x] After K turns → session `summary` is populated in SQLite.
- [x] Kill the LLM endpoint → `502 llm_provider_error`, question still in history.
- [x] New session → no leakage of the previous session's history.

## Done When
- [x] Manual verification passes with recorded output.
- [x] Lint/format pass.
- [x] `stage-06-summary.md` written; roadmap boxes ticked. STOP.
