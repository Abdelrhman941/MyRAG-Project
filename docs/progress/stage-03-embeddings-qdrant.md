# Stage 03 — Embeddings + Qdrant Storage + Ingestion

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [x] Uploaded documents automatically become searchable vectors in Qdrant, with no
      manual step and no performance hit on the upload response.

## Scope (In)
- `app/embeddings/`: lazy **singleton** wrapper around `sentence-transformers` BGE-M3
  producing **dense (1024-dim) + sparse** vectors; batched encoding; `get_embedding_model()`
  is the only public accessor.
- `app/infrastructure/ports.py`: `VectorStorePort` (ensure_collection, upsert_chunks, query placeholder, delete_by_document).
- `app/infrastructure/vector_store/`: `QdrantVectorStore` adapter; collection `chunks` (dense named vector + sparse vector, cosine).
- `app/services/ingestion_service.py`: `IngestionService.ingest(document_id)` =
  parse → chunk → embed → upsert → status `ready` (or `failed` + logged reason). One pass, no duplicate compute.
- Wire ingestion into both upload endpoints via FastAPI `BackgroundTasks`.
- Settings: `QDRANT_URL` (default `http://localhost:6333`), `EMBEDDING_MODEL="BAAI/bge-m3"`, `EMBEDDING_BATCH_SIZE=16`.
- `docker-compose.yml` with a Qdrant service (dev convenience).

## Out of Scope
- ❌ Query/retrieval API (Stage 04) — the port's `query` may stay unimplemented past a stub that raises `NotImplementedError` internally
- ❌ Reranking, semantic memory collection
- ❌ OCR fallback for empty parses (Stage 09 candidate)

## Inputs
- `document_id` for a row in status `uploaded`.
- Qdrant reachable at `QDRANT_URL`.

## Outputs
- Qdrant points: id = `uuid5(document_id + chunk_index)`, dense+sparse vectors, payload `{document_id, chunk_index, text, original_file_name, created_at}`.
- Document status transitions: `uploaded → processing → ready | failed`.

## Business Rules
- The embedding model loads **once** per process (lazy singleton); first ingestion may be slow — log it, don't optimize.
- Embedding runs in a worker thread (`asyncio.to_thread`) so the event loop never blocks.
- Batched encoding with `EMBEDDING_BATCH_SIZE`; documents larger than memory budget stream chunks through the batcher.
- Upsert is idempotent (deterministic point ids) — re-ingesting the same document must not duplicate points.

## Dependencies
- New packages: `sentence-transformers`, `qdrant-client`.
- Stages 01–02 complete. Qdrant running (docker-compose).

## Error Cases
- Qdrant unreachable → document `failed`, structured log with `event=ingestion.qdrant_unavailable`. Upload response is unaffected (already returned).
- Empty chunk list (scanned PDF) → document `failed` with reason `no_extractable_text`.
- OOM-risk batch → reduce batch size via Settings; never load the whole document's chunks into one encode call.

## Implementation Steps
- [x] docker-compose: Qdrant service.
- [x] `app/embeddings/` singleton + batch encode API.
- [x] `VectorStorePort` + `QdrantVectorStore` + `get_vector_store()` factory.
- [x] `IngestionService` orchestrating Stage-02 outputs → Qdrant.
- [x] BackgroundTasks wiring in both upload routes.
- [x] Status transition logging (`event=ingestion.status` per transition).
- [x] Run verification commands.

## Manual Verification
- [x] `docker compose up -d` → Qdrant healthy.
- [x] Upload a PDF → response is immediate; within seconds the row flips to `ready`; Qdrant dashboard shows points with correct payloads.
- [x] Re-upload same content → `409`, zero new points.
- [x] Stop Qdrant, upload → row becomes `failed`, logs show the reason.
- [x] Upload 5 files in one batch → all reach `ready`; RAM stays within budget (watch `free -m`).

## Done When
- [x] Manual verification passes with recorded output.
- [x] Lint/format pass.
- [x] `stage-03-summary.md` written; roadmap boxes ticked. STOP.
