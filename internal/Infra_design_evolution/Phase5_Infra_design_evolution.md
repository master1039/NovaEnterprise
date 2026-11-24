# Phase 5 — Infrastructure Design Evolution

## What is actually running in Phase 5

The default Phase 5 path is one Python process. SQLite is a local file; the
vector and graph adapters are in-memory Python objects. There is no container
network and no remote routing in the default setup.

```mermaid
flowchart TB
    subgraph Host[Developer computer]
        CLI[Python ingestion command]
        FS[Local sample files]
        SQL[(Local SQLite file)]
        MEMV[In-process vector memory]
        MEMG[In-process graph memory]
        FS --> CLI
        CLI --> SQL
        CLI --> MEMV
        CLI --> MEMG
    end
```

In-memory vector and graph data lasts only for the command process. Relational
documents and chunks persist in SQLite. This is intentional for deterministic
development and testing.

## Component wiring

The command constructs settings, a database session, the embedding provider,
and tenant-specific store adapters. It injects them into the pipeline instead
of letting ingestion create hidden network clients.

```mermaid
flowchart LR
    CFG[Environment settings] --> CMD[Command composition root]
    CMD --> SES[SQLAlchemy session]
    CMD --> EMB[Embedding adapter]
    CMD --> VEC[Vector adapter]
    CMD --> GRF[Graph adapter]
    SES --> PIPE[Ingestion pipeline]
    EMB --> PIPE
    VEC --> PIPE
    GRF --> PIPE
```

## Optional external routing

Phase 4 adapters allow later environments to route vector operations to Qdrant
and graph operations to Neo4j. Those services are optional; Phase 5 neither
deploys them nor claims they are available. No Docker or Compose topology is
introduced in this phase.

```mermaid
flowchart LR
    APP[Ingestion process]
    DB[(SQLite or configured SQL database)]
    Q[(Optional Qdrant endpoint)]
    N[(Optional Neo4j endpoint)]
    APP -->|SQLAlchemy connection| DB
    APP -.->|Configured HTTP API| Q
    APP -.->|Configured Bolt connection| N
```

Dashed routes exist only when the operator explicitly selects and configures
the corresponding adapter. The offline test suite never opens those routes.

## Failure routing

Relational storage is the durable source record. Vector and graph work is
attempted independently afterward so one optional adapter cannot be mistaken
for total success.

```mermaid
flowchart TD
    W[Write document and chunks] -->|fails| F[Failed result and rollback]
    W -->|succeeds| V[Attempt vector upsert]
    V --> G[Attempt graph upsert]
    G --> C{Any adapter error}
    C -->|no| OK[Completed]
    C -->|yes| P[Partial with named errors]
```

## Operational boundaries

- File type and size are checked before parsing.
- Only a filename is stored as source metadata; local parent paths are not
  exposed.
- PDF parsing is local through `pypdf`.
- No credentials are needed for default SQLite/memory operation.
- External credentials, networking, deployment, health checks, and retries
  belong to later infrastructure phases.
