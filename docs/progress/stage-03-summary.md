# Stage 03 Summary: Embeddings, Qdrant & Background Ingestion

## What Was Done

1.  **Dependencies & Environment:**
    *   Added `sentence-transformers` and `qdrant-client` to `pyproject.toml`.
    *   Fought through extensive NTFS/WSL cross-filesystem locking issues to successfully install Torch 2.4.0+cpu and the required embedding libraries via `uv`.
    *   Created `docker-compose.yml` defining the `qdrant` container (`v1.11.0`) with standard persistent volumes and ports.

2.  **Architecture & Ports:**
    *   Implemented `VectorStorePort` in `app/infrastructure/ports.py`.
    *   Formalized the `FileStoragePort` to ensure absolute decoupling for the document storage adapter.
    *   Updated `dependencies.py` to wire `VectorStorePort` to `QdrantVectorStore`.

3.  **Embeddings (BGE-M3):**
    *   Created `app/embeddings/model.py` containing a thread-safe, lazy singleton wrapper around `SentenceTransformer("BAAI/bge-m3")`.
    *   Implemented custom extraction logic within `EmbeddingModel._encode_sparse_batch()` to directly access the BGE-M3 `sparse_linear` layer (applied over the XLM-RoBERTa hidden states) to produce accurate SPLADE-style sparse lexical weight vectors.
    *   Added a fallback mechanism to use embedding-norm weights if the specific model revision doesn't expose the custom `sparse_linear` attribute.

4.  **Vector Store (Qdrant):**
    *   Created `QdrantVectorStore` adapter in `app/infrastructure/vector_store/qdrant.py`.
    *   Implemented deterministic point generation: `point_id = uuid5(NAMESPACE_DNS, f"{document_id}:{chunk_index}")`. This guarantees idempotency (re-ingesting a document safely overwrites old chunks without duplicating).
    *   Supported hybrid payloads: inserts both `dense` (Cosine, 1024-dim) and `sparse` named vectors into the `chunks` collection.

5.  **Service Orchestration (IngestionService):**
    *   Created `app/services/ingestion_service.py` to coordinate the full background ingestion lifecycle: Storage Read → Parse → Chunk → Embed (via `asyncio.to_thread` for the CPU-bound `encode_batch`) → Qdrant Upsert.
    *   Transitions `DocumentStatus` safely from `UPLOADED` → `PROCESSING` → `READY` (or `FAILED` with appropriate string reasons and logging).

6.  **API Layer:**
    *   Updated `app/apis/v1/documents.py`. Both single `/documents` and `/documents/batch` upload endpoints now add `run_ingestion_background()` to FastAPI's `BackgroundTasks`.
    *   The background task appropriately spins up its own standalone database session since the request-scoped session is closed before background execution begins.

## What Was Not Done (Deferred)

*   **Reranking:** Deferred to a later stage as per the guidelines.
*   **Querying/Retrieval:** The `query` method in `QdrantVectorStore` is stubbed out and raises `NotImplementedError`, deferred to Stage 04 (Retrieval).
*   **Docker Execution:** Local Docker Desktop is unavailable in this specific WSL environment, so `docker-compose up` was skipped for verification.

## Next Steps

*   Update the roadmap checkboxes to complete Stage 03.
*   Proceed to Stage 04: Hybrid Retrieval.

## Corrective Pass (Post-Implementation)
- Fixed **BGE-M3 double forward pass**: Consolidated dense pooling and `sparse_linear` extraction into a single forward pass over the HF transformer to prevent duplicate compute and optimize memory.
- **Removed Sparse Fallback**: Removed the `hidden.norm` heuristic. If `sparse_linear` is unavailable on the model, we now fail hard, preventing silent performance degradation for hybrid retrieval.
- **Cleaned Up Error Handling**: Split embedding errors from Qdrant networking errors in `IngestionService` and ensured that `delete_by_document` runs on failure to wipe out any stale/partial points before entering the `FAILED` state.
- **Fixed Qdrant Race Condition**: Caught potential `UnexpectedResponse` exceptions in `ensure_collection` when multiple background threads try to create the `chunks` collection simultaneously.
- **Fixed Ports Layer**: `IngestionService` and `DocumentService` now depend fully on `FileStoragePort` (after adding `move_from` to the Protocol) instead of the concrete `DocumentStorage`, preserving the Ports & Adapters integrity.
- **Max Length Alignment**: Configured `max_length=8192` explicitly in the BGE-M3 tokenizer so chunk texts up to 512 tokens (via `tiktoken`) are never silently truncated by the model's inner limits.
