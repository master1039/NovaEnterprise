# Phase 7 — Infrastructure Design Evolution

## Default local wiring

Phase 7 introduces no new container or network requirement. Tests and local
development use an in-process graph store populated from isolated SQLite data.

```mermaid
flowchart TB
    subgraph HOST[Developer computer]
        APP[Python process]
        SQL[(SQLite)]
        MAP[Graph mapper]
        MEM[In-memory graph]
        RET[Graph retrieval service]
        SQL --> MAP --> MEM --> RET
    end
```

## Component routing

```mermaid
flowchart LR
    TENANT[Application tenant] --> SEED[Validated seed mapping]
    SEED --> STORE[Injected GraphStore]
    INPUT[Typed traversal input] --> QUERY[Parameterized Cypher spec]
    QUERY --> RETRIEVE[Traversal service]
    STORE --> RETRIEVE --> EVIDENCE[Graph Evidence]
```

Tenant identity is present on every node and edge. The retrieval service also
rejects any cross-tenant node returned by an adapter.

## Optional Neo4j routing

```mermaid
flowchart LR
    APP[Same application contracts]
    CONFIG{Graph-store setting}
    MEMORY[(Process memory)]
    NEO[(Optional Neo4j endpoint)]
    APP --> CONFIG
    CONFIG -->|default| MEMORY
    CONFIG -.->|explicit Bolt configuration| NEO
```

The dashed route exists only when configured. Phase 7 does not deploy Neo4j,
Docker networking, credentials, retries, or production health infrastructure.

## Failure routing

```mermaid
flowchart TD
    REQUEST[Typed traversal] --> STORE[Graph adapter]
    STORE -->|success| RESULT[Bounded evidence]
    STORE -->|failure| REDACT[Secret-redacted error]
    REDACT --> DEGRADED[Degraded result with no fabricated evidence]
```

This boundary allows a later multi-source workflow to continue with SQL or
document evidence even when graph retrieval is temporarily unavailable.
