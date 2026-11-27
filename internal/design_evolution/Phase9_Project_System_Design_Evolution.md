# Phase 9 — Project System Design Evolution

## Starting point

Phase 4 supplied a cache contract and Phase 2 supplied organizational facts,
but the application did not yet have one service for four isolated scopes.

```mermaid
flowchart LR
    APP[Future research workflow] --> CACHE[Generic cache]
    APP --> ORG[(Seeded organization facts)]
    CACHE -. no scoped memory contract .-> GAP[Memory gap]
    ORG -. organization only .-> GAP
```

## P9-1 — Explicit memory contracts

The first step names the scopes and makes their required ownership part of the
validated contract.

```mermaid
flowchart TD
    ENTRY[MemoryEntry] --> TENANT[Tenant required]
    ENTRY --> SCOPE{Memory scope}
    SCOPE --> C[Conversation: user and session]
    SCOPE --> U[User: user only]
    SCOPE --> O[Organizational: tenant only]
    SCOPE --> W[Workflow: user and session]
    ENTRY --> PROV[Source and metadata provenance]
```

Invalid combinations are rejected before reaching an adapter. For example,
organizational memory cannot carry a user or session owner.

## P9-2 — Separate short-term and durable adapters

```mermaid
flowchart LR
    SERVICE[MemoryService] --> SHORT{Temporary scope?}
    SHORT -->|conversation or workflow| CACHE[CacheMemoryAdapter]
    SHORT -->|user or organizational| SQL[SqlMemoryAdapter]
    CACHE --> EXPIRING[(Expiring cache)]
    SQL --> USERDB[(Scoped user memory table)]
    SQL --> ORGDB[(Existing organization facts)]
```

The service chooses storage from the scope. Callers never need to know whether
the local implementation is in-memory/SQLite or the optional Redis/PostgreSQL
production pairing.

## P9-3 — Safe operations and isolation proofs

```mermaid
flowchart TD
    CALL[Record, recall, or clear] --> VALIDATE[Validate scope and context]
    VALIDATE --> REDACT[Redact secrets recursively]
    REDACT --> ADAPTER[Call the correct adapter]
    ADAPTER -->|success| RESULT[Bounded deterministic result]
    ADAPTER -->|failure| DEGRADED[Degraded result, no invented items]
    TESTS[Offline tests] --> VALIDATE
    TESTS --> RESULT
    TESTS --> DEGRADED
```

Tests cover tenant, user, session, and scope isolation; stable upserts; bounded
recall; provenance; exact clearing; secret redaction; and adapter failure.

## End-of-phase design

```mermaid
flowchart LR
    WORKFLOW[Future agent workflow] --> MEMORY[MemoryService]
    MEMORY --> CONV[Conversation]
    MEMORY --> USER[User]
    MEMORY --> ORG[Organizational]
    MEMORY --> FLOW[Workflow]
    CONV --> CACHE[(Short-term cache)]
    FLOW --> CACHE
    USER --> DB[(Durable SQL)]
    ORG --> DB
    MEMORY --> OUT[Typed result with provenance and status]
```

The final boundary is deliberately independent from retrieval. Memory can help
shape a workflow, but evidence remains the source for factual claims.

