# Stage 07 — Document Management

## What Was Done
1. **Added `list_documents` API**: Implemented `GET /api/v1/documents` supporting simple limit/offset pagination and newest-first ordering.
2. **Added `delete_document` API**: Implemented `DELETE /api/v1/documents/{document_id}` enforcing the exact sequence: Vectors -> Filesystem -> Database.
3. **Robust Error Handling & Transaction Safety**:
   - `409 DocumentProcessingConflictError` is raised if a document is deleted while still ingesting.
   - Vector store exceptions are trapped and explicitly mapped to `RetrievalError` (returning `502`).
   - If the `storage.delete()` fails, the database row is correctly preserved, avoiding the creation of ghost records (as per the spec's warning against assuming perfect cross-system transactions).
   - If the file is already missing on disk, `unlink()` safely ignores it, making the filesystem deletion step natively idempotent without errors.
4. **Types**: Mypy strictly verified all new methods and DI injects.

## Decisions Made
- Chose to inject `VectorStoreDep` strictly at the router layer in `delete_document` instead of refactoring the global `DocumentService` constructor used in upload, preventing unnecessary dependency chains in endpoints that don't need Qdrant access.
- Confirmed that `app/infrastructure/file_storage/storage.py`'s `delete` method uses `path.unlink()` within a `path.exists()` guard, inherently fulfilling the idempotency requirement natively without raising unneeded errors.

## Next Steps
- Stage 08 — Frontend!
