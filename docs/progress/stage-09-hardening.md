# Stage 09 — Hardening (Deferred Items)

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

> This stage collects everything deliberately deferred. Pick items one at a time —
> each bullet below can become its own feature spec before implementation.

## Goal
- [ ] Production-grade verification and optional quality upgrades.

## Scope (In) — pick per sub-feature, one spec each

### 09a — Automated test suite
- pytest + `httpx.AsyncClient` with `ASGITransport`.
- `app.dependency_overrides` for DB/storage/vector-store/LLM — no monkeypatching.
- Isolation: in-memory SQLite, `tmp_path` storage, Qdrant `:memory:`.
- Cover behavior and contracts (upload dedup, rate limits, batch results, ingestion
  transitions, retrieval ordering, chat memory isolation), not private internals.

### 09b — Reranker
- `BAAI/bge-reranker-v2-m3` in `app/embeddings/`, behind `RERANK_ENABLED=false` default.
- Pipeline: hybrid top-k×2 → rerank → top-k. Measure RAM before enabling by default.

### 09c — Streaming responses
- SSE on the chat endpoint; frontend renders tokens incrementally.

### 09d — Semantic long-term memory
- Qdrant `chat_memory` collection: embedded past Q&A pairs recalled across sessions.
- New port method or dedicated port — decide in the sub-spec.

## Out of Scope
- ❌ Auth, multi-user, cloud deployment — separate project stages, not this one
- ❌ Any change to stages 01–08 contracts without updating the SDD

## Verification
- 09a: full suite green + lint.
- 09b–09d: each gets its own manual verification list when specced.

## Done When
- [ ] The chosen sub-feature's spec is written, implemented, verified, summarized.
- [ ] Roadmap updated. STOP after each sub-feature.
