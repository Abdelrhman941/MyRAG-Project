# Stage 01 Summary — Batch Upload + Rate Limiting

Date: 2026-08-26

## What was built
- `POST /api/v1/documents/batch` endpoint added, accepting up to 10 files using `Annotated[list[UploadFile], File(...)]`.
- Reused per-file logic cleanly by extracting `DocumentService._upload_single` to ensure deduplication (DRY).
- Added batch schemas: `BatchUploadResponse`, `BatchUploadResult`, and `BatchUploadError` for per-file outcome mapping without failing the batch request.
- Added `slowapi` dependency and attached a global limiter configuration.
- Decorated both `POST /api/v1/documents` and `POST /api/v1/documents/batch` with `@limiter.limit("10/hour")`.
- Extended `DocumentType` enum with `DOCX` and applied the schema version bump via an Alembic migration.
- Handled SQL Alchemy session concurrency by adding an `asyncio.Lock()` to DB flush operations and expunging retrieved entities to prevent cross-task expiration.

## Decisions made
- We created a custom `rate_limit_exceeded_handler` to convert `slowapi`'s built-in 429 exceptions to our unified standard API error structure. It's centrally registered alongside other handlers in `exception_handlers.py`.
- In `_upload_single`, we wrapped `self.db.add`, `commit`, and `refresh` inside a `asyncio.Lock()` instance bound to the service and added a `self.db.expunge(document)` statement. This safely allowed bounded concurrent uploading via `asyncio.gather` for the batch without causing SQLAlchemy async context violations or `MissingGreenlet` loading errors on subsequent task commits.
- SQLite does not use native enums (`native_enum=False`) so the Alembic `document_type` column migration was effectively a metadata version bump without executing an invalid SQLite `ALTER COLUMN ... TYPE` statement. The migration file was simplified to handle this as a schema-version bump.

## Deviations from spec
- Added a `TooManyFilesError` (400) subclass to gracefully integrate the `MAX_FILES_PER_REQUEST` guard into the existing unified error handlers.

## Verification evidence
```
uv run --with ruff ruff check .
All checks passed!

uv run --with ruff ruff format .
35 files left unchanged

1. 3 Valid file upload:
curl -s -X POST "http://localhost:8000/api/v1/documents/batch" -F "files=@fresh1.pdf" -F "files=@fresh2.txt" -F "files=@fresh3.md"
-> {"results":[{"filename":"fresh1.pdf","ok":true,"document":{"id":"4b79a698-c3d1-4bc1-a554-f2dca27e98e7",...}}...]}

2. Same bytes twice (dedup validation):
curl -s -X POST "http://localhost:8000/api/v1/documents/batch" -F "files=@newdup1.txt" -F "files=@newdup2.txt"
-> {"results":[{"filename":"newdup1.txt","ok":true,...},{"filename":"newdup2.txt","ok":false,"document":null,"error":{"code":"duplicate_document","message":"This document already exists."}}]}

3. 11 Files guard:
curl -s -w "\n%{http_code}" -X POST "http://localhost:8000/api/v1/documents/batch" -F "files=@limit1.txt" ... (11 files)
-> {"error":{"code":"too_many_files","message":"Too many files. Maximum 10 files per request.","request_id":"0d0782b2-2a2d-414c-815c-a0c93c499690"}}
400

4. Hit endpoint 11 times within an hour:
for i in {1..12}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST ... -F "file=@test2.txt"; done
-> 409 (x10)
-> 429 (x2)

5. Upload 60 MB file:
curl -s -X POST "http://localhost:8000/api/v1/documents/batch" -F "files=@large.txt" -F "files=@fresh2.txt"
-> {"results":[{"filename":"large.txt","ok":false,"document":null,"error":{"code":"file_too_large","message":"File exceeds maximum allowed size of 50MB."}},{"filename":"fresh2.txt","ok":false,"document":null,"error":{"code":"duplicate_document","message":"This document already exists."}}]}
```

## Out-of-scope items flagged
- The `fastapi` route function signature required adding the `request: Request` parameter in order for `slowapi` to resolve the client IP accurately per its expected integration contract.

## Follow-ups for later stages
- The database is currently handling heavy locking during concurrent uploads because all concurrent `_upload_single` calls belong to a single dependency-injected session. In high-traffic deployments where batch payloads are large, consider utilizing a session factory within the service or background ingestion tasks.

## Files touched
- `app/core/config.py` — added limit config vars.
- `app/core/limiter.py` — created limiter singleton.
- `app/core/__init__.py` — exported limiter.
- `app/main.py` — attached limiter to app instance.
- `app/apis/exception_handlers.py` — added and registered custom 429 handler.
- `app/core/exceptions.py` — added `TooManyFilesError`.
- `app/services/document_service.py` — extracted `_upload_single`, wired lock and expunging, and added `upload_batch`.
- `app/core/enums/document.py` — added `DOCX` enum.
- `app/schemas/document.py` — added batch wrapper/result classes.
- `app/schemas/__init__.py` — exported new batch classes.
- `app/apis/v1/documents.py` — refactored single upload route with limiter and added batch endpoint.
- `migrations/versions/1ebc03d5a124_add_docx_to_document_type.py` — schema version bump for enum addition.
