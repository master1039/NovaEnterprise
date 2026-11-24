# Phase 5 — Project System Design Evolution

## Starting point

At the beginning of Phase 5, documents could be seeded into relational storage,
but there was no reusable path from a file to chunks, embeddings, or graph data.

```mermaid
flowchart LR
    F[Sample files] --> S[Seed service]
    S --> D[(Documents table)]
    V[Vector-store contract]
    G[Graph-store contract]
```

## P5-1 — Validated loading and chunking

The first step creates a single safe entrance for Markdown, text, and PDF. Size,
encoding, type, and extracted content are validated before deterministic chunks
are created with source, page, position, and stable identity metadata.

```mermaid
flowchart LR
    F[MD TXT PDF] --> L[Validated loader]
    L --> N[Normalized document]
    N --> C[Deterministic chunker]
    C --> M[Chunks plus source metadata]
```

## P5-2 — Guardrail-first knowledge extraction

Each chunk is treated as untrusted before extraction. The system flags hostile
phrases, redacts recognizable secrets, and uses fixed rules to identify known
enterprise entities. It never asks document text what action to perform.

```mermaid
flowchart TD
    C[Untrusted chunk] --> I[Injection inspection]
    I --> R[Secret redaction]
    R --> E[Deterministic entity extraction]
    E --> N[Typed entity nodes]
    E --> X[MENTIONS relationships]
    I --> F[Hostile flags and reasons]
```

## P5-3 — Coordinated multi-store indexing

One tenant-scoped coordinator writes the durable record first, then updates the
replaceable vector and graph adapters. Stable IDs and upserts make reruns safe.
An existing Phase 2 document with the same tenant and source is reused rather
than duplicated. Adapter errors produce an explicit partial result.

```mermaid
flowchart LR
    C[Safe chunks] --> P[Ingestion pipeline]
    P --> DB[(Documents and chunks)]
    P --> EM[Embedding provider]
    EM --> VS[(Vector store)]
    P --> EX[Entity results]
    EX --> GS[(Graph store)]
    DB --> O[Completed partial or failed result]
    VS --> O
    GS --> O
```

## P5-4 — Repeatable operator workflow

The final step wraps the pipeline in a module command. Dry-run mode validates
and reports without writing. Normal mode uses configured adapters, which default
to deterministic local implementations.

```mermaid
sequenceDiagram
    actor Operator
    participant CLI as Ingest command
    participant Loader
    participant Pipeline
    participant Stores
    Operator->>CLI: run or dry-run
    CLI->>Loader: load canonical files
    Loader-->>CLI: normalized documents
    alt dry-run
        CLI-->>Operator: validation report
    else write
        CLI->>Pipeline: index each document
        Pipeline->>Stores: upsert scoped records
        Stores-->>Pipeline: success or adapter error
        Pipeline-->>Operator: completed partial or failed
    end
```

## End-of-phase design qualities

- Deterministic and offline by default.
- Tenant identity is part of every persisted/indexed identifier.
- Unsafe text remains inert data and carries an audit-friendly flag.
- Repeated execution does not multiply records.
- External vector/graph adapters can replace memory implementations without
  changing the ingestion workflow.
