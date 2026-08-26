# API & Database Interactions

Parent: [../00-index.md](../00-index.md) · Spec: [../sdd.md](../sdd.md)

✅ = implemented · ⏳ = planned

## Sequence: Batch Upload

```mermaid
sequenceDiagram
    actor C as Client (Next.js)
    participant API as FastAPI apis/documents
    participant RL as Rate limiter (slowapi)
    participant SVC as DocumentService
    participant DB as SQLite
    participant FS as FileStoragePort
    participant BG as BackgroundTasks → IngestionService
    participant QD as VectorStorePort (Qdrant)

    C->>API: POST /api/v1/documents/batch (≤10 files)
    API->>RL: check IP quota (10/hour)
    RL--xC: 429 rate_limit_exceeded (if exceeded)
    loop each file (bounded concurrency)
        API->>SVC: upload_document(file)
        SVC->>FS: stream → temp (SHA-256 + size check)
        SVC->>DB: INSERT (content_hash UNIQUE)
        DB--xSVC: IntegrityError → 409 duplicate_document
        SVC->>FS: move temp → <uuid><ext>
        SVC-->>API: Document
    end
    API-->>C: 201 per-file results
    API->>BG: schedule ingestion (async semaphore)
    loop each uploaded document
        BG->>DB: status → processing
        BG->>BG: parse → chunk → embed (BGE-M3)
        BG->>QD: upsert chunks
        BG->>DB: status → ready | failed
    end
```

## Sequence: Chat Message (RAG)

```mermaid
sequenceDiagram
    actor C as Client (Next.js)
    participant API as FastAPI apis/chat
    participant CS as ChatService
    participant SR as SessionRepositoryPort (SQLite)
    participant EMB as embeddings (BGE-M3)
    participant QD as VectorStorePort (Qdrant)
    participant GEN as generation (prompt)
    participant LLM as LLMProviderPort (external API)

    C->>API: POST /sessions/{id}/messages { question }
    API->>CS: answer(session_id, question)
    CS->>SR: load session (last N msgs + summary)
    CS->>EMB: embed(question)
    CS->>QD: hybrid query → top-k chunks
    CS->>GEN: assemble prompt (budgeted)
    CS->>LLM: /chat/completions
    LLM--xCS: timeout/5xx → 502 llm_provider_error
    LLM-->>CS: answer text
    CS->>SR: persist user + assistant messages
    opt every K turns
        CS->>LLM: summarize transcript (background)
        CS->>SR: update session summary
    end
    CS-->>API: { answer, sources }
    API-->>C: 200
```

## Endpoint ↔ DB/Store matrix

| Endpoint | SQLite | Filesystem | Qdrant | LLM API |
|---|---|---|---|---|
| `POST /documents` ✅ | insert document | write file | — | — |
| `POST /documents/batch` ✅ | insert ≤10 docs | write ≤10 files | (async) upsert | — |
| `GET /documents` ⏳ | select | — | — | — |
| `DELETE /documents/{id}` ⏳ | delete row | delete file | delete by document_id | — |
| `POST /chat/sessions` ✅ | insert session | — | — | — |
| `GET /chat/sessions` ✅ | select | — | — | — |
| `GET /sessions/{id}/messages` ✅ | select | — | — | — |
| `POST /sessions/{id}/messages` ✅ | read + insert | — | hybrid query | 1 call (+1 background summary) |

## Performance notes

- Upload response time is independent of ingestion cost — ingestion is backgrounded.
- Multi-file upload: per-file streaming + async semaphore; throughput bounded by disk
  and the embedding batch, not by file count linearly.
- Chat latency = 1 local embedding (~100–300 ms CPU) + 1 Qdrant query (~ms) +
  1 external LLM call (dominant).
