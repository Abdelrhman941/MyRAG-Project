# Stage 02 — Parsing + Chunking

Parent: [roadmap.md](roadmap.md) · Rules: [../../AGENTS.md](../../AGENTS.md) · SST: [../sdd.md](../sdd.md)

## Goal
- [x] Any stored document can be converted into embedding-ready `Chunk` objects.

## Scope (In)
- `app/models/`: `ParsedSegment` and `Chunk` domain objects (dataclasses or Pydantic — pick one, document why).
- `app/parsers/` — one parser per format, single public entry `parse(path, doc_type) -> list[ParsedSegment]`:
  - PDF → `pypdf` (per-page segments)
  - TXT → plain read with encoding fallback (utf-8 → latin-1)
  - MD → `markdown-it-py` (plain-text extraction)
  - DOCX → `python-docx` (paragraphs)
- `app/chunking/` — `langchain-text-splitters` `RecursiveCharacterTextSplitter` (token-aware), single public entry `chunk(segments, document_id) -> list[Chunk]`.
- Chunk parameters in Settings: `CHUNK_SIZE_TOKENS=512`, `CHUNK_OVERLAP_TOKENS=64`.

## Out of Scope
- ❌ Embeddings, Qdrant, ingestion orchestration (Stage 03)
- ❌ OCR, table extraction, image handling
- ❌ A second chunking strategy
- ❌ Endpoint changes

## Inputs
- Files stored at `data/uploads/<uuid><ext>` with a `Document` row.
- `document_id` + `document_type` from the DB row.

## Outputs
- `parse`: ordered `ParsedSegment` list (text + page where known).
- `chunk`: ordered `Chunk` list (text, document_id, chunk_index).

## Business Rules
- Empty parse result (e.g., scanned PDF with no text layer) is **not** an exception — returns `[]`; the caller decides (Stage 03 marks the document `failed` with a reason).
- Segment order must be preserved: chunk_index increases monotonically per document.
- Text normalization (whitespace collapse) happens in parsers, once — not in chunking.

## Dependencies
- New packages: `pypdf`, `markdown-it-py`, `python-docx`, `langchain-text-splitters`, `tiktoken` (for token-aware splitting).
- Reads files only through `FileStoragePort` — never raw paths outside infrastructure.

## Error Cases
- Corrupted/encrypted PDF → `ParsingError` (new `AppError` subclass, 422 `parsing_failed`) with document_id in details.
- Unknown encoding that survives the fallback → same `ParsingError`.
- A single bad segment must not discard the rest of the document — skip + log warning.

## Implementation Steps
- [x] Add `ParsedSegment`, `Chunk` to `app/models/`.
- [x] Add `ParsingError` to `app/core/exceptions.py`.
- [x] Implement the 4 parsers behind the single `parse()` entry point.
- [x] Implement `chunk()` with the token-aware splitter, parameters from Settings.
- [x] Run verification commands.

## Manual Verification
- [x] Parse + chunk a real PDF, TXT, MD, and DOCX; print segment/chunk counts and the first chunk's text for each — eyeball that text is clean and ordered.
- [x] A scanned-image PDF returns `[]` without raising.
- [x] Chunk sizes respect the token settings (sample-check with `tiktoken`).

## Done When
- [x] Manual verification passes with recorded output.
- [x] Lint/format pass.
- [x] `stage-02-summary.md` written; roadmap boxes ticked. STOP.
