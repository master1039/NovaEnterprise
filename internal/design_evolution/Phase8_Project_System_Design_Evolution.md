# Phase 8 — Project System Design Evolution

## Starting point

Phase 5 already split documents into safe chunks and stored them in the
relational database and vector store. At the start of Phase 8, the application
had storage but no unified way to retrieve and rank those chunks.

```mermaid
flowchart LR
    INGEST[Phase 5 ingestion] --> DB[(Document chunks)]
    INGEST --> VECTOR[(Chunk vectors)]
    DB -. no document retriever yet .-> FUTURE[Future workflow]
    VECTOR -. no document retriever yet .-> FUTURE
```

## P8-1 — Two complementary retrieval paths

```mermaid
flowchart TD
    Q[User question] --> EMBED[Embedding provider]
    EMBED --> SEM[Semantic vector search]
    Q --> TOKEN[Safe tokenization]
    TOKEN --> BM25[Tenant-scoped BM25]
    SEM --> SMETA[Semantic candidates with source metadata]
    BM25 --> BMETA[Lexical candidates with database metadata]
```

Semantic search recognizes similar meaning. BM25 rewards discriminating word
matches using document frequency and length normalization. Both paths are
bounded and deterministic with the default in-memory providers.

## P8-2 — Fusion, reranking, and evidence

```mermaid
flowchart LR
    S[Semantic ranking] --> RRF[Reciprocal-rank fusion]
    B[BM25 ranking] --> RRF
    RRF --> DEDUP[Deduplicate by stable chunk ID]
    DEDUP --> RERANK[Deterministic overlap rerank]
    RERANK --> CUT[Score cutoff and result limit]
    CUT --> EV[Shared document Evidence]
```

Reciprocal-rank fusion combines positions rather than incompatible raw score
scales. A chunk found by both methods gains support, while stable chunk IDs
prevent duplicate citations. The final score stays in the shared zero-to-one
Evidence range.

## P8-3 — Isolation, hostile content, and failure proof

```mermaid
flowchart TD
    TESTS[Offline Phase 8 tests] --> REL[Relevance and stable ordering]
    TESTS --> TENANT[Tenant isolation]
    TESTS --> HOSTILE[Hostile document text]
    TESTS --> FAIL[Vector adapter failure]
    HOSTILE --> WRAP[Redact and mark as untrusted data]
    FAIL --> PARTIAL[BM25 evidence plus partial status]
```

Tests prove relevance, deduplication, stable evidence identity, bounds, source
metadata, isolation, secret redaction, and truthful adapter degradation without
network access.

## End-of-phase design

```mermaid
flowchart LR
    ROUTER[Future retrieval router] --> HYBRID[HybridRetriever]
    HYBRID --> EMB[EmbeddingModel]
    HYBRID --> VS[VectorStore]
    HYBRID --> SQL[(Tenant document chunks)]
    HYBRID --> FUSE[Fusion and safety boundary]
    FUSE --> EVIDENCE[Shared Evidence]
    EVIDENCE --> WORKFLOW[Future answer workflow]
```

Phase 8 ends with one provider-neutral service that can find document evidence
through meaning and keywords, explain which channels found each passage, and
degrade safely without fabricating results.
