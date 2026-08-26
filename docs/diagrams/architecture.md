# System Architecture

Parent: [../00-index.md](../00-index.md) · Spec: [../sdd.md](../sdd.md)

## Layered Architecture

```mermaid
flowchart TB
    subgraph Client["Client"]
        UI["Next.js (App Router)<br/>TailwindCSS + shadcn/ui<br/>base template: 21st.dev ai-chat"]
    end

    subgraph Backend["FastAPI Backend"]
        direction TB
        MW["RequestLoggingMiddleware<br/>request-id + timing"]
        API["app/apis — routing (thin)<br/>documents · chat · system"]
        SCH["app/schemas — Pydantic API contracts"]
        SVC["app/services — use-cases<br/>DocumentService · IngestionService<br/>RetrievalService · ChatService"]
        subgraph Pipe["In-process pipeline packages"]
            PARS["app/parsers<br/>pypdf · markdown-it · docx"]
            CHK["app/chunking<br/>langchain-text-splitters"]
            EMB["app/embeddings<br/>BGE-M3 singleton (CPU)"]
            RET["app/retrieval<br/>hybrid query + fusion"]
            GEN["app/generation<br/>prompt assembly + parsing"]
            MEM["app/memory<br/>short-term window + rolling summary"]
        end
        MOD["app/models — ORM + domain objects<br/>ParsedSegment · Chunk · RetrievalResult · ChatMessage"]
        INFRA["app/infrastructure — adapters<br/>ports.py: FileStoragePort · VectorStorePort<br/>LLMProviderPort · SessionRepositoryPort"]
        CORE["app/core — config · enums · exceptions · logging"]
    end

    subgraph External["External systems"]
        DB[("SQLite<br/>documents · sessions · messages")]
        FS[("Filesystem<br/>data/uploads/&lt;uuid&gt;&lt;ext&gt;")]
        QD[("Qdrant<br/>collection: chunks (dense+sparse)")]
        LLM[["External LLM API<br/>(OpenAI-compatible, httpx)"]]
    end

    UI -->|HTTP/JSON multipart| MW --> API
    API --> SCH --> SVC
    SVC --> Pipe
    SVC --> MOD
    Pipe --> MOD
    SVC --> INFRA
    INFRA --> DB & FS & QD & LLM
    CORE -.->|imported by all| API
```

## Hardware Budget (16 GB RAM, no GPU inference)

| Component | RAM footprint | Notes |
|---|---|---|
| FastAPI + SQLAlchemy | ~150 MB | async, negligible |
| BGE-M3 (sentence-transformers) | ~2–3 GB | lazy singleton, loaded once |
| Reranker v2-m3 (deferred) | ~2 GB | only when its stage arrives |
| Qdrant (Docker) | ~200–500 MB | on-disk storage |
| LLM | 0 | external API |
| **Headroom** | **> 9 GB free** | safe |

## Dependency Direction (strict)

```
apis → schemas → services → pipeline packages → models
                   │
                   └→ infrastructure (ports) → core
core imports nothing from other layers
```

Violating this direction is a defect — flag it, don't do it.
