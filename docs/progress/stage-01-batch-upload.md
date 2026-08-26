# Stage 01 — Batch Upload + Rate Limiting

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [ ] A client can upload up to 10 files in one request without degrading performance.
- [ ] Upload abuse is prevented by an IP-based rate limit.

## Scope (In)
- `POST /api/v1/documents/batch` accepting `Annotated[list[UploadFile], File(...)]`.
- Per-file outcome reporting: each file yields either a `DocumentResponse` or a structured error (code + message). One bad file never fails the batch.
- `slowapi` limiter on both upload endpoints: **10 requests/hour per IP**.
- Request-level guard: **more than 10 files → 400** before any processing.
- Bounded concurrency: files processed with an `asyncio.Semaphore` (limit from Settings, default 4).
- Add `docx` to `DocumentType` (enum + migration) — parsing comes in Stage 02, upload accepts it now.

## Out of Scope
- ❌ Parsing/chunking/embedding (Stage 02–03)
- ❌ Background ingestion wiring (Stage 03)
- ❌ Any auth or per-user quotas
- ❌ Frontend

## Inputs
- `multipart/form-data` with 1–10 files.
- Settings additions: `MAX_FILES_PER_REQUEST=10`, `UPLOAD_RATE_LIMIT="10/hour"`, `UPLOAD_CONCURRENCY=4`.

## Outputs
- `201` → `{ "results": [ {"filename", "ok": true, "document": DocumentResponse} | {"filename", "ok": false, "error": {"code", "message"}} ] }`
- `429` with the standard error shape when the rate limit is hit.

## Business Rules
- Per-file dedup (content hash) applies exactly as in single upload — duplicates are per-file failures, not batch failures.
- Size and type validation per file, while streaming (existing logic reused — DRY: extract shared per-file logic, do not copy-paste it).
- `docx` uploads are accepted and stored; their `status` stays `uploaded` until Stage 03.

## Dependencies
- Existing `DocumentService`, `DocumentStorage`, exception handlers.
- New package: `slowapi`.
- Alembic migration for the `document_type` enum extension.

## Error Cases
- >10 files → `400 too_many_files` (standard shape).
- Rate limit → `429 rate_limit_exceeded` (already in `HTTP_STATUS_ERROR_CODES`).
- Per-file: `missing_filename` / `unsupported_document_type` / `file_too_large` / `duplicate_document` reported in that file's result entry.
- Storage failure on one file → that file errors; others continue.

## Implementation Steps
- [ ] Add Settings fields (`MAX_FILES_PER_REQUEST`, `UPLOAD_RATE_LIMIT`, `UPLOAD_CONCURRENCY`).
- [ ] Extract the per-file upload flow in `DocumentService` into a reusable private method (single source — used by both endpoints).
- [ ] Extend `DocumentType` with DOCX + Alembic migration.
- [ ] Add batch endpoint with semaphore-bounded `asyncio.gather` (return_exceptions pattern mapped to per-file results).
- [ ] Add batch response schemas to `app/schemas/`.
- [ ] Wire `slowapi` (limiter on app state, decorator on both upload routes).
- [ ] Run verification commands from AGENTS.md §14.

## Manual Verification
- [ ] Upload 3 mixed valid files in one request → 3 ok results, files on disk as `<uuid><ext>`, 3 DB rows.
- [ ] Upload the same bytes twice under different names in one batch → first ok, second `duplicate_document`.
- [ ] Upload 11 files → `400`.
- [ ] Hit the endpoint 11 times within an hour from one IP → `429`.
- [ ] Upload one 60 MB file (with default 50 MB limit) → per-file `file_too_large`, others ok.

## Done When
- [ ] All manual verification steps pass with recorded output.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass.
- [ ] `stage-01-summary.md` written; roadmap boxes ticked. STOP.
