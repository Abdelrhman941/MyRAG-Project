# Data Flow — Ingestion Pipeline (DFD)

Parent: [../00-index.md](../00-index.md) · Spec: [../sdd.md](../sdd.md)

How a file moves through the system, from upload to searchable vectors.
✅ = implemented

```mermaid
flowchart TB
    U[/"Client: POST /api/v1/documents[/batch]<br/>multipart/form-data"/]

    subgraph Request["Request path (synchronous)"]
        RL["✅ Rate limit check<br/>max 10 files/request · 10 req/hour/IP"]
        VAL["✅ Validate per file<br/>filename present · extension in {pdf,txt,md,docx}<br/>size ≤ MAX_FILE_SIZE_MB (checked while streaming)"]
        TMP["✅ Stream to temp file<br/>compute SHA-256 + size in the same pass<br/>(no full file in memory)"]
        DEDUP{"✅ content_hash<br/>already in DB?"}
        REC["✅ Insert Document row<br/>status=uploaded · UNIQUE(content_hash)"]
        MOV["✅ Move temp → data/uploads/&lt;uuid&gt;&lt;ext&gt;<br/>(on failure: delete DB row)"]
        RESP[/"✅ 201 Created + DocumentResponse<br/>batch: 207-style per-file results"/]
    end

    subgraph Background["Background ingestion (per file, bounded concurrency)"]
        P1["✅ status → processing"]
        PARSE["✅ app/parsers<br/>file → list[ParsedSegment]<br/>pypdf · plain text · markdown-it · docx"]
        CHUNK["✅ app/chunking<br/>ParsedSegment → list[Chunk]<br/>RecursiveCharacterTextSplitter (token-aware)"]
        EMBED["✅ app/embeddings<br/>Chunk texts → dense + sparse vectors<br/>BGE-M3 singleton (CPU, batched)"]
        UPSERT["✅ app/infrastructure/vector_store<br/>upsert into Qdrant collection 'chunks'<br/>payload: document_id · chunk_index · text · file name"]
        P2{"✅ success?"}
        OK["✅ status → ready"]
        FAIL["✅ status → failed<br/>(log event + reason)"]
    end

    DB[("SQLite: documents")]
    FS[("Filesystem: data/uploads")]
    QD[("Qdrant: chunks")]

    U --> RL --> VAL --> TMP --> DEDUP
    DEDUP -->|yes| DUPERR[/"✅ 409 duplicate_document"/]
    DEDUP -->|no| REC --> MOV --> RESP
    REC -.-> DB
    MOV -.-> FS
    MOV ==>|BackgroundTasks| P1 --> PARSE --> CHUNK --> EMBED --> UPSERT --> P2
    UPSERT -.-> QD
    P2 -->|yes| OK -.-> DB
    P2 -->|no| FAIL -.-> DB
```

## Rules encoded in this flow

1. **Dedup by content, not name** — SHA-256 of the bytes; renamed duplicates are rejected. ✅
2. **No orphan state** — temp file deleted on any failure; DB row deleted if the final move fails. ✅
3. **Multi-file ≠ slow** — batch endpoint streams each file independently and runs
   ingestion with an async semaphore (bounded concurrency), so N files don't mean N× latency. ✅
4. **One pipeline pass** — `IngestionService` runs parse→chunk→embed→upsert once per
   document; no stage recomputes another's output.
5. **Failure visibility** — ingestion errors never leak to the upload response (client
   already has its 201); they surface as `status=failed` + structured logs.
