# Stage 02 Summary — Parsing + Chunking

Date: 2026-08-26

## What was built
- Created `ParsedSegment` and `Chunk` domain models using standard Python dataclasses with `slots=True` to minimize overhead.
- Implemented `ParsingError` (422) in `app/core/exceptions.py`.
- Added chunk size configuration `CHUNK_SIZE_TOKENS=512` and `CHUNK_OVERLAP_TOKENS=64` to `app/core/config.py`.
- Created format-specific parsers in `app/parsers/` (`pdf`, `txt`, `md`, `docx`) that read bytes directly, with a unified `parse(content, doc_type, document_id)` entrypoint in `core.py`.
- Implemented an internal utility module `app/parsers/utils.py` for shared decoding and text normalization, eliminating cyclic dependencies between `core.py` and format parsers.
- Markdown parsing explicitly decodes, parses semantically (preserving structure like headings/lists via `MarkdownIt`), and then normalizes text without destroying structural line breaks.
- Implemented text chunking in `app/chunking/core.py` using `RecursiveCharacterTextSplitter.from_tiktoken_encoder`.

## Decisions made
- We decided to use standard Python `@dataclass(slots=True)` instead of `Pydantic` for `Chunk` and `ParsedSegment`. These structures act purely as intermediate, non-HTTP payload payloads during ingestion, so minimizing memory footprint and overhead for thousands of items is better than Pydantic's full validation.
- Extracted shared decoding and normalization logic into `app/parsers/utils.py` to prevent cyclic module coupling back to `core.py` and clarify internal parser dependency flow.
- We opted for the `DocumentStorage` returning `bytes` (as originally implemented in Stage 01 via `aiofiles`), so `io.BytesIO` was injected cleanly into format-specific libraries (`pypdf`, `python-docx`) without re-fetching from disk.
- Included `document_id` inside the `ParsingError` payload details for clearer tracing during batch responses downstream.

## Deviations from spec
- The spec mentioned `parse(path, doc_type)` but also mandated reading "only through `FileStoragePort`". Since the existing `FileStoragePort.read()` yields bytes rather than an absolute path (avoiding direct filesystem leaks), we updated the function signature to take `content: bytes` and `document_id` instead.

## Verification evidence
```
uv run --with ruff ruff check .
All checks passed!

uv run --with ruff ruff format --check .
All checks passed!

--- Testing MD Structure ---
Markdown Extracted Text:
[Preserved structure with blank lines between headings, paragraphs, and lists]

--- Testing >512 Token Chunking ---
Generated 27 chunks.
Chunk 0 tokens: 512
...
Chunk 25 tokens: 512
Chunk 26 tokens: 352
Chunk verification passed!

--- Testing Corrupted PDF ---
invalid pdf header: b'This '
EOF marker not found
Parsing failed for document ...: Failed to read PDF file
Successfully caught ParsingError: Failed to parse the document.

--- Testing Scanned/Empty PDF ---
Scanned PDF generated 0 chunks.
Scanned PDF verification passed!
```

## Out-of-scope items flagged
- The `stage-02` components are currently stand-alone and purely operational. We did not write BackgroundTasks or attempt to link them to endpoints. Stage 03 will orchestrate these steps natively.
- `DocumentService` currently relies on concrete `DocumentStorage` rather than a dedicated `Port`. This architectural debt is recognized but deliberately deferred to avoid expanding the scope of Stage 02's corrective pass.

## Follow-ups for later stages
- Ensure the Stage 03 pipeline fetches `content = await storage.read()` efficiently, possibly considering memory limits if a single worker ingests massive PDFs. `pypdf` supports `BytesIO` natively without leaks, but holding massive buffers in memory limits maximum concurrency.

## Files touched
- `pyproject.toml` — added parsing/chunking libraries.
- `app/models/ingestion.py` — created `ParsedSegment` and `Chunk`.
- `app/models/__init__.py` — exported ingestion objects.
- `app/core/exceptions.py` — added `ParsingError`.
- `app/core/config.py` — added `CHUNK_SIZE_TOKENS` and `CHUNK_OVERLAP_TOKENS`.
- `app/parsers/__init__.py`, `core.py`, `utils.py`, `pdf.py`, `txt.py`, `md.py`, `docx.py` — implemented parsers pipeline and decoupled utils.
- `app/chunking/__init__.py`, `core.py` — implemented chunker pipeline.
