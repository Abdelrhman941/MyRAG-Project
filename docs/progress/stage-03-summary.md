# Stage 03 Summary: Embeddings, Qdrant & Background Ingestion

## What Was Done

1.  **Dependencies & Environment:**
    *   Added `flagembedding`, `transformers`, and `sentence-transformers` to `pyproject.toml`, resolving strict versioning conflicts (pinned to `1.2.10`, `4.39.3`, and `3.1.1` respectively) to guarantee CPU stability and avoid tokenization bugs with dict vs list inputs.
    *   Fought through extensive NTFS/WSL cross-filesystem locking issues to successfully install Torch 2.4.0+cpu and the required embedding libraries via `uv`.
    *   Created `docker-compose.yml` defining the `qdrant` container (`v1.11.0`) with standard persistent volumes and ports.

2.  **Architecture & Ports:**
    *   Implemented `VectorStorePort` in `app/infrastructure/ports.py`.
    *   Formalized the `FileStoragePort` to ensure absolute decoupling for the document storage adapter.
    *   Updated `dependencies.py` to wire `VectorStorePort` to `QdrantVectorStore`.

3.  **Embeddings (BGE-M3):**
    *   Created `app/embeddings/model.py` containing a thread-safe, lazy singleton wrapper natively using `BGEM3FlagModel` to encode both dense and sparse vectors natively.
    *   Removed hacky monkeypatches and cleanly pinned models using `huggingface_hub.snapshot_download` against a fixed revision SHA.

4.  **Vector Store (Qdrant):**
    *   Created `QdrantVectorStore` adapter in `app/infrastructure/vector_store/qdrant.py`.
    *   Implemented deterministic point generation: `point_id = uuid5(NAMESPACE_DNS, f"{document_id}:{chunk_index}")`. This guarantees idempotency (re-ingesting a document safely overwrites old chunks without duplicating).
    *   Supported hybrid payloads: inserts both `dense` (Cosine, 1024-dim) and `sparse` named vectors into the `chunks` collection.

5.  **Service Orchestration (IngestionService):**
    *   Created `app/services/ingestion_service.py` to coordinate the full background ingestion lifecycle: Storage Read → Parse → Chunk → Embed (via `asyncio.to_thread` for the CPU-bound `encode_batch`) → Qdrant Upsert.
    *   Transitions `DocumentStatus` safely from `UPLOADED` → `PROCESSING` → `READY` (or `FAILED` with appropriate string reasons and logging).
    *   Fixed failure paths to safely execute `delete_by_document` and properly handle detached objects during rollbacks.

6.  **API Layer:**
    *   Updated `app/apis/v1/documents.py`. Both single `/documents` and `/documents/batch` upload endpoints now add `run_ingestion_background()` to FastAPI's `BackgroundTasks`.
    *   The background task appropriately spins up its own standalone database session since the request-scoped session is closed before background execution begins.

## What Was Not Done (Deferred)

*   **Reranking:** Deferred to a later stage as per the guidelines.

## Next Steps

*   Update the roadmap checkboxes to complete Stage 03.
*   Proceed to Stage 04: Hybrid Retrieval.
