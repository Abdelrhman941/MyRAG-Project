# Data Schema — ERD & Vector Payload

Parent: [../00-index.md](../00-index.md) · Spec: [../sdd.md](../sdd.md)

✅ = implemented (migration exists) · ⏳ = planned · 🔒 = deferred

## SQLite — Entity Relationship

```mermaid
erDiagram
    DOCUMENTS ||--o{ CHAT_MESSAGES : "referenced by (source citations)"
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains

    DOCUMENTS {
        uuid id PK "✅"
        string original_file_name "✅ max 255"
        string content_hash UK "✅ SHA-256 hex · UNIQUE"
        enum document_type "✅ pdf · txt · md · docx"
        enum status "✅ uploaded · processing · ready · failed"
        datetime created_at "✅ tz-aware"
    }

    CHAT_SESSIONS {
        uuid id PK "⏳"
        string title "⏳ auto from first question"
        text summary "⏳ nullable · rolling long-term memory"
        datetime created_at "⏳"
        datetime updated_at "⏳"
    }

    CHAT_MESSAGES {
        uuid id PK "⏳"
        uuid session_id FK "⏳ → chat_sessions.id · indexed · cascade delete"
        enum role "⏳ user · assistant"
        text content "⏳"
        datetime created_at "⏳ · indexed"
    }
```

**Constraint notes**
- `documents.content_hash` UNIQUE is enforced at the DB level — dedup correctness
  does not depend on application code alone. ✅
- `chat_messages.session_id` gets an index; deleting a session cascades to its messages.
- Vectors are **not** stored in SQLite. Chunks live in Qdrant; the link is
  `document_id` + `chunk_index` in the payload.

## Qdrant — Collection `chunks` ✅

```mermaid
flowchart LR
    subgraph Point["Qdrant point (one per Chunk)"]
        ID["id: uuid5(document_id + chunk_index)"]
        DV["dense vector: float[1024]<br/>BGE-M3"]
        SV["sparse vector: BGE-M3 lexical weights"]
        PL["payload:<br/>document_id · chunk_index · text<br/>original_file_name · created_at"]
    end
```

- Distance: cosine (dense); sparse via Qdrant sparse vectors.
- Hybrid: one Query API call with prefetch (dense + sparse) → **RRF fusion** — done
  inside Qdrant, never in Python.
- Deleting a document = delete points where `payload.document_id = <id>`.

## Qdrant — Collection `chat_memory` 🔒 deferred

Embedded past Q&A pairs for cross-session semantic recall. Exists only from the
semantic-memory stage onward.

## Domain value objects (`app/models`, in-memory only)

| Object | Fields | Producer → Consumer |
|---|---|---|
| `ParsedSegment` | text, page?, section? | parsers → chunking |
| `Chunk` | text, document_id, chunk_index | chunking → embeddings → vector store |
| `RetrievalResult` | chunk, score | retrieval → generation |
| `ChatMessage` | role, content, created_at | memory → generation |
