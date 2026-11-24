# Phase 6 — Infrastructure Design Evolution

## What actually runs in Phase 6

The default Phase 6 path stays inside one Python process and one local SQLite
file. No container, database proxy, or new network route is introduced.

```mermaid
flowchart TB
    subgraph HOST[Developer computer]
        APP[Python process]
        VALIDATOR[SQL parser and allowlist]
        SESSION[SQLAlchemy session]
        SQLITE[(Local SQLite database file)]
        APP --> VALIDATOR
        VALIDATOR --> SESSION
        SESSION --> SQLITE
    end
```

## Component wiring and trust boundaries

The query builder owns the fixed SQL shape. The caller supplies ordinary
values. The validator inspects structure, and the executor overwrites the
tenant parameter with the authenticated application tenant before SQLAlchemy
binds values to the database call.

```mermaid
flowchart LR
    VALUES[Service dates limit] --> BUILDER[Typed template]
    BUILDER --> PARSER[SQLGlot AST validation]
    TENANT[Application tenant] --> EXEC[Evidence executor]
    PARSER --> EXEC
    EXEC --> BIND[SQLAlchemy bound parameters]
    BIND --> DB[(Relational database)]
    DB --> ROWS[Bounded rows]
    ROWS --> EVIDENCE[Safe evidence objects]
```

The database receives one `SELECT`. User text is never concatenated into that
statement. Database failures pass back through secret redaction before they can
reach a workflow or log-facing error.

## Local and configured database routing

SQLite is the deterministic default. A configured PostgreSQL-compatible URL can
use the same SQLAlchemy boundary in a later environment. Phase 6 adds neither a
Docker network nor a production deployment claim.

```mermaid
flowchart LR
    APP[Safe SQL retrieval]
    CFG{Configured database URL}
    LOCAL[(SQLite local file)]
    REMOTE[(Optional managed relational database)]
    APP --> CFG
    CFG -->|default local path| LOCAL
    CFG -.->|explicit environment configuration| REMOTE
```

The dashed route exists only when an operator configures it. Credentials remain
in environment configuration and never become query parameters, evidence, or
error details.

## Rejection and failure routing

```mermaid
flowchart TD
    SQL[Candidate query] --> CHECK{Validation passes}
    CHECK -->|no| REJECT[Stop before database]
    CHECK -->|yes| RUN[Execute bound SELECT]
    RUN -->|database error| SAFE[Redacted SQL execution error]
    RUN -->|success| LIMIT[Deterministic bounded rows]
    LIMIT --> NORMALIZE[Evidence normalization]
```

## Operational boundaries

- Allowed tables and columns are explicit in code.
- Schema-qualified tables, comments, semicolons, subqueries, set operations,
  wildcard columns, string literals, unapproved functions, `SELECT INTO`, and
  locking selects are rejected.
- Every referenced table needs a tenant predicate.
- Every query needs a maximum result limit.
- Phase 6 performs no insert, update, delete, schema, attachment, transaction,
  or filesystem SQL operation.
- Connection pooling, replicas, proxies, container networking, database roles,
  and production read-only credentials belong to later delivery phases.
