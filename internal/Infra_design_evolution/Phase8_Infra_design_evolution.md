# Phase 8 — Infrastructure Design Evolution

## Default local wiring

Phase 8 adds no required container. The complete offline path runs inside one
Python process with SQLite, deterministic fake embeddings, and the in-memory
vector store.

```mermaid
flowchart TB
    subgraph HOST[Developer computer]
        APP[Python process]
        RET[HybridRetriever]
        EMB[Fake embedding model]
        MEM[In-memory vector store]
        SQL[(SQLite document chunks)]
        APP --> RET
        RET --> EMB
        RET --> MEM
        RET --> SQL
    end
```

There is no network traffic in this configuration, and the test harness blocks
external connections.

## Component wiring and request routing

```mermaid
flowchart LR
    TENANT[Tenant context] --> RET[Hybrid retriever]
    QUERY[Question] --> RET
    RET -->|embed query| MODEL[EmbeddingModel]
    MODEL -->|query vector| STORE[VectorStore]
    RET -->|tenant-filtered SELECT| DB[(DocumentChunk and Document)]
    STORE --> SEM[Semantic candidates]
    DB --> LEX[BM25 candidates]
    SEM --> FUSE[Fusion and rerank]
    LEX --> FUSE
    FUSE --> OUT[Bounded Evidence]
```

The injected vector store is created for one tenant, and the relational query
also contains an explicit tenant filter. Source filename, page, and chunk
metadata travel with the candidate into its final evidence locator.

## Optional production adapter route

```mermaid
flowchart LR
    APP[Same HybridRetriever contract] --> CONFIG{Configured adapters}
    CONFIG -->|default| FAKE[Fake embeddings]
    CONFIG -->|default| MEMORY[(In-memory vectors)]
    CONFIG -.->|explicit client| REAL[External embedding provider]
    CONFIG -.->|explicit URL and client| QDRANT[(Qdrant)]
    APP --> SQL[(PostgreSQL or SQLite chunks)]
```

The dashed routes are optional adapter choices already established in Phase 4.
Phase 8 does not deploy Qdrant, an embedding service, Docker networking, retry
workers, or production credentials.

## Degraded routing

```mermaid
flowchart TD
    REQUEST[Hybrid request] --> VECTOR[Semantic route]
    REQUEST --> BM25[Relational BM25 route]
    VECTOR -->|success| FUSION[Fusion]
    BM25 -->|success| FUSION
    VECTOR -->|failure| REDACT[Redact adapter error]
    REDACT --> PARTIAL[Partial result]
    BM25 --> PARTIAL
    VECTOR -->|failure| BOTH{Did BM25 also fail?}
    BM25 -->|failure| BOTH
    BOTH -->|yes| DEGRADED[Degraded with no fabricated evidence]
```

One working retrieval route can still provide evidence with a `partial` status.
If neither route works, the result is `degraded`. Error text is secret-redacted
before it crosses the retrieval boundary.

## Security boundary

```mermaid
flowchart LR
    SOURCE[Stored chunk] --> REDACT[Secret redaction]
    REDACT --> FLAG{Guardrail flagged?}
    FLAG -->|no| DATA[Untrusted evidence data]
    FLAG -->|yes| WRAP[Explicit untrusted-content wrapper]
    DATA --> CITATION[Citation-ready Evidence]
    WRAP --> CITATION
```

Retrieved text never becomes code, SQL, routing configuration, or an agent
instruction. The safety metadata stays attached for later workflow decisions.
