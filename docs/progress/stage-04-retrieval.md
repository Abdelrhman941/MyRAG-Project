# Stage 04 — Retrieval

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [ ] A natural-language question returns the top-k most relevant chunks via hybrid search.

## Scope (In)
- `app/models/`: `RetrievalResult` domain object (chunk + score).
- `app/retrieval/`: `RetrievalService.retrieve(query, top_k) -> list[RetrievalResult]`
  — embed query (dense+sparse) → `VectorStorePort.query()` → ranked results.
- Implement `VectorStorePort.query` in `QdrantVectorStore` using Qdrant's **native
  Query API**: prefetch dense + prefetch sparse → **RRF fusion** inside Qdrant.
  Never fuse in Python.
- Settings: `RETRIEVAL_TOP_K=8`, `RETRIEVAL_HYBRID=true` (false → dense-only path).
- Internal-only verification hook: a temporary CLI script or `__main__` block — **no public endpoint yet**.

## Out of Scope
- ❌ Any LLM call or prompt building (Stage 06)
- ❌ Reranker (Stage 09)
- ❌ Chat/session integration (Stage 05–06)
- ❌ Public HTTP endpoint

## Inputs
- Query string, `top_k` (default from Settings).

## Outputs
- Ordered `list[RetrievalResult]`, best first; each carries chunk text, score, document_id, chunk_index, original_file_name.

## Business Rules
- Only chunks whose document has `status=ready` are eligible — enforced by deleting
  failed documents' points at ingestion time (Stage 03 guarantee); retrieval itself
  does not re-check the DB.
- Empty query string → `ValidationError`-style `AppError` (400 `empty_query`).
- Fewer indexed chunks than `top_k` → return what exists; never pad.

## Dependencies
- Stages 02–03 complete. Qdrant with data.

## Error Cases
- Qdrant unreachable → `RetrievalError` (502 `retrieval_unavailable`).
- Empty result → return `[]` (not an error).

## Implementation Steps
- [ ] `RetrievalResult` in `app/models/`.
- [ ] `RetrievalError` in `app/core/exceptions.py`.
- [ ] `VectorStorePort.query` implementation (Query API, prefetch+RRF; dense-only branch when hybrid=false).
- [ ] `RetrievalService` (embed → port call → map to domain objects).
- [ ] Verification hook script.
- [ ] Run verification commands.

## Manual Verification
- [ ] Ingest 2–3 distinct documents; ask a question answerable from exactly one → top results come from that document.
- [ ] Toggle `RETRIEVAL_HYBRID=false` → still returns sensible results.
- [ ] Query with an unrelated phrase → low scores / empty; no crash.
- [ ] Record timings: embed + query should be well under 1 s on CPU.

## Done When
- [ ] Manual verification passes with recorded output.
- [ ] Lint/format pass.
- [ ] `stage-04-summary.md` written; roadmap boxes ticked. STOP.
