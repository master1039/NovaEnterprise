# Phase 7 — Project System Design Evolution

## Starting point

Phase 4 supplied generic graph adapters, but the application did not yet know
how enterprise records should become a business graph or which traversals were
safe to expose.

```mermaid
flowchart LR
    R[Relational records] -. no mapping .-> G[Generic graph store]
```

## P7-1 — Typed enterprise graph

```mermaid
flowchart LR
    DB[(Tenant records)] --> MAP[Validated graph mapper]
    MAP --> T[Team]
    MAP --> S[Service]
    MAP --> I[Incident]
    MAP --> C[Customer]
    MAP --> D[Decision]
    S -->|OWNED_BY| T
    I -->|AFFECTED| S
    I -->|IMPACTED| C
    D -->|ADDRESSES| I
```

Stable node and edge IDs plus upserts make repeated seeding idempotent. Missing
references stop the mapping instead of producing imaginary nodes.

## P7-2 — Typed read-only traversals

```mermaid
flowchart TD
    Q[Traversal request] --> TYPE[Enum relationship and direction]
    TYPE --> SPEC[Parameterized Cypher specification]
    SPEC --> STORE[GraphStore traversal]
    STORE --> NORMALIZE[Graph Evidence]
```

The Cypher shape is fixed. Tenant, node, service, date, and limit values remain
parameters. Customer-impact traversal uses a half-open date range, ownership is
one bounded hop, and expansion accepts only allowlisted relationships.

## P7-3 — Safety and degradation proof

```mermaid
flowchart LR
    TESTS[Offline tests] --> MEMORY[In-memory graph]
    TESTS --> ATTACK[Hostile IDs and invalid traversal types]
    TESTS --> FAILURE[Unavailable adapter]
    MEMORY --> EVIDENCE[Ordered stable evidence]
    ATTACK --> REJECT[Rejected or empty]
    FAILURE --> DEGRADED[Degraded result]
```

## End-of-phase design

```mermaid
flowchart LR
    ROUTER[Future retrieval router] --> GRAPH[Typed Graph Retrieval Service]
    GRAPH --> MEM[(In-memory graph)]
    GRAPH -. optional adapter .-> NEO[(Neo4j)]
    GRAPH --> EV[Shared Evidence]
    EV --> WF[Future evidence workflow]
```

Phase 7 ends with deterministic graph construction, tenant-safe traversal,
parameterized query visibility, shared evidence, and explicit degradation.
