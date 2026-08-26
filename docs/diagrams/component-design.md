# Component Design — Ports & Adapters

Parent: [../00-index.md](../00-index.md) · Spec: [../sdd.md](../sdd.md)

Every external system sits behind a **Port** (`typing.Protocol` in
`app/infrastructure/ports.py`). Services depend on ports only. **Factories** in
`app/dependencies.py` pick the adapter from `Settings`. Swapping an adapter touches
the adapter + factory only — never a service.

## Ports and Adapters

```mermaid
flowchart LR
    subgraph Services["app/services"]
        DS[DocumentService]
        IS[IngestionService]
        RS[RetrievalService]
        CS[ChatService]
    end

    subgraph Ports["app/infrastructure/ports.py — typing.Protocol"]
        FSP[FileStoragePort<br/>save · read · delete · move_from]
        VSP[VectorStorePort<br/>ensure_collection · upsert_chunks<br/>query · delete_by_document]
        LLP[LLMProviderPort<br/>generate messages → answer]
        SRP[SessionRepositoryPort<br/>create/get/list sessions<br/>add/list messages · update summary]
    end

    subgraph Adapters["app/infrastructure — concrete adapters"]
        LFS["file_storage/<br/>LocalDocumentStorage ✅"]
        QVS["vector_store/<br/>QdrantVectorStore ⏳"]
        OAI["llm_provider/<br/>OpenAICompatibleLLM ⏳"]
        SQL["session_store/<br/>SqliteSessionRepository ⏳"]
    end

    subgraph Factory["app/dependencies.py — factories"]
        F1[get_storage ✅]
        F2[get_vector_store ⏳]
        F3[get_llm_provider ⏳]
        F4[get_session_repository ⏳]
    end

    DS --> FSP
    IS --> FSP & VSP
    RS --> VSP
    CS --> VSP & LLP & SRP

    FSP -.->|implemented by| LFS
    VSP -.->|implemented by| QVS
    LLP -.->|implemented by| OAI
    SRP -.->|implemented by| SQL

    F1 --> LFS
    F2 --> QVS
    F3 --> OAI
    F4 --> SQL
```

## Swap table

| Port | Now | Later | Cost to swap |
|---|---|---|---|
| `FileStoragePort` | Local filesystem ✅ | S3/MinIO | new adapter + factory branch |
| `VectorStorePort` | Qdrant | any vector DB | new adapter + factory branch |
| `LLMProviderPort` | OpenAI-compatible API | any provider | new adapter + factory branch |
| `SessionRepositoryPort` | SQLite | PostgreSQL | new adapter + factory branch |

## Module Communication

- **In-process modules** (`parsers`, `chunking`, `embeddings`, `memory`, `retrieval`,
  `generation`): direct typed calls exchanging domain objects from `app/models`
  (`ParsedSegment`, `Chunk`, `RetrievalResult`, `ChatMessage`). No DTO ceremony.
- **Client ↔ Backend:** HTTP/JSON; uploads are `multipart/form-data`.
- **Backend ↔ Qdrant:** `qdrant-client` (gRPC/HTTP); hybrid fusion via Qdrant's
  native Query API — **never** reimplemented in Python.
- **Backend ↔ LLM:** `httpx.AsyncClient` against an OpenAI-compatible
  `/chat/completions` endpoint; API key from `Settings`, never in code.
- **Background work:** FastAPI `BackgroundTasks` for ingestion (MVP). No Celery/Redis.

## Modularity Rules

- A service never imports an adapter class — only ports and factories.
- `embeddings` exposes one singleton accessor (`get_embedding_model()`); nothing else
  may import `sentence_transformers` directly.
- Each pipeline package has exactly one public entry point used by services.
