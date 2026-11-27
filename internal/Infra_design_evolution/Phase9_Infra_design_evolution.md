# Phase 9 — Infrastructure Design Evolution

## Default local wiring

Phase 9 requires no Docker services for development or tests. SQLite stores
durable scopes and the process-local cache stores temporary scopes.

```mermaid
flowchart TB
    subgraph PROCESS[Python application process]
        SERVICE[MemoryService]
        CACHE_ADAPTER[Cache memory adapter]
        SQL_ADAPTER[SQL memory adapter]
        MEMORY_CACHE[(In-memory cache)]
        SERVICE --> CACHE_ADAPTER --> MEMORY_CACHE
        SERVICE --> SQL_ADAPTER
    end
    SQL_ADAPTER --> USERDB[(SQLite scoped_memory for users)]
    SQL_ADAPTER --> ORGDB[(SQLite organizational_memory)]
```

All tests run through this route without network access, credentials, or
containers.

## Request wiring and routing

```mermaid
flowchart LR
    CONTEXT[Tenant, user, session] --> SERVICE[MemoryService]
    OP[Record, recall, clear] --> SERVICE
    SERVICE --> ROUTE{Scope router}
    ROUTE -->|conversation/workflow| CACHE[Cache adapter]
    ROUTE -->|user/organizational| SQL[SQL adapter]
    CACHE --> RESULT[MemoryOperationResult]
    SQL --> RESULT
```

Tenant ownership is applied in both routes. Cache keys additionally encode the
user, session, and scope; SQL statements include tenant, scope, and user
predicates.

## Cache key isolation

```mermaid
flowchart TD
    TENANT[Tenant identifier] --> KEY[Length-delimited cache key]
    USER[User identifier] --> KEY
    SESSION[Session identifier] --> KEY
    SCOPE[Conversation or workflow] --> KEY
    KEY --> VALUE[JSON array of validated memory entries]
    VALUE --> TTL[Expiry refreshed on record]
```

Length-delimited values prevent ambiguous key combinations. Expiry keeps
temporary memory from becoming accidental permanent storage.

## Optional production wiring

```mermaid
flowchart LR
    APP[Same MemoryService] --> CACHE_PROTOCOL[CacheBackend protocol]
    APP --> SQL_ADAPTER[SqlMemoryAdapter]
    CACHE_PROTOCOL -->|local| MEMORY[(In-memory cache)]
    CACHE_PROTOCOL -. optional .-> REDIS[(Redis)]
    SQL_ADAPTER -->|local| SQLITE[(SQLite)]
    SQL_ADAPTER -. optional .-> POSTGRES[(PostgreSQL plus RLS)]
```

The Phase 4 cache protocol already supports Redis. The new durable user-memory
table is included in the Alembic migration chain and PostgreSQL
row-level-security policy list. Organizational memory continues to use the
Phase 2 table and seeded facts. Phase 9 does not deploy those external services.

## Failure boundary

```mermaid
flowchart TD
    REQUEST[Memory operation] --> ADAPTER[Selected adapter]
    ADAPTER -->|available| DATA[Real stored memory]
    ADAPTER -->|unavailable| REDACT[Redact error details]
    REDACT --> DEGRADED[Degraded result with zero fabricated items]
```

An unavailable cache or database never causes the service to silently borrow
data from a different scope or manufacture remembered facts.

