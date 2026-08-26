# Stage 07 — Document Management

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [ ] Users can list their documents and delete one completely (DB row + file + vectors).

## Scope (In)
- `GET /api/v1/documents` → ordered list of `DocumentResponse` (newest first).
- `DELETE /api/v1/documents/{id}` → `204`; removes the DB row, the physical file via `FileStoragePort`, and all Qdrant points via `VectorStorePort.delete_by_document(document_id)`.
- Implement `delete_by_document` in `QdrantVectorStore` (payload filter on `document_id`).

## Out of Scope
- ❌ Re-ingestion / re-processing endpoints
- ❌ Pagination beyond a simple `limit`/`offset`
- ❌ Bulk delete
- ❌ Frontend

## Business Rules
- Deletion order: vectors → file → DB row. If vector deletion fails, abort with `502`
  and keep the rest (a document without vectors but with a row is recoverable; the
  reverse is a ghost).
- Deleting a document in status `processing` → `409 document_processing` (do not
  delete mid-ingestion).
- List endpoint exposes `status` so the UI can show ingestion progress.

## Error Cases
- Unknown id → `404 not_found`.
- File already missing on disk → log warning, continue deletion (idempotent).

## Implementation Steps
- [ ] `VectorStorePort.delete_by_document` implementation.
- [ ] Service methods `list_documents`, `delete_document` in `DocumentService`.
- [ ] Routers + schemas.
- [ ] Run verification commands.

## Manual Verification
- [ ] List after several uploads → correct order and statuses.
- [ ] Delete a `ready` document → row gone, file gone, Qdrant count drops by its chunk count; retrieval no longer returns its chunks.
- [ ] Delete unknown id → 404. Delete a `processing` document → 409.

## Done When
- [ ] Manual verification passes with recorded output.
- [ ] Lint/format pass.
- [ ] `stage-07-summary.md` written; roadmap boxes ticked. STOP.
