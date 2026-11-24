# Phase 6 — Project System Design Evolution

## Starting point

At the beginning of Phase 6, enterprise records and tenant-aware repositories
already existed. There was no retrieval boundary that could safely accept a SQL
query shape and return normalized evidence.

```mermaid
flowchart LR
    Q[Business question] -. no safe SQL path .-> DB[(Enterprise database)]
    DB --> R[Application records]
```

## P6-1 — A structural SQL security gate

The first step introduces an AST-based validator. It accepts only one bounded,
tenant-scoped `SELECT` over explicitly approved tables and columns. Dangerous or
ambiguous structures stop before execution.

```mermaid
flowchart TD
    S[Candidate SQL] --> P[SQLGlot parser]
    P --> A{One SELECT}
    A -->|no| X[Reject]
    A -->|yes| W{Allowlisted structure}
    W -->|no| X
    W -->|yes| T{Every table tenant scoped}
    T -->|no| X
    T -->|yes| L{Bounded LIMIT}
    L -->|no| X
    L -->|yes| V[Validated SQL contract]
```

## P6-2 — Parameterized templates and shared evidence

The second step adds a typed incident query. User-controlled values never enter
the SQL string. SQLAlchemy binds the tenant, service name, and half-open date
range. Returned rows become the shared `Evidence` contract.

```mermaid
flowchart LR
    I[Service and date inputs] --> B[Typed query builder]
    B --> V[SQL validator]
    V --> E[SQLAlchemy executor]
    E --> DB[(SQLite or PostgreSQL)]
    DB --> N[Evidence normalizer]
    N --> O[Stable SQL evidence]
```

The half-open interval is `started_at <= incident time < ended_at`. Adjacent
reporting periods therefore meet at one boundary without counting an incident
twice.

## P6-3 — Proving the boundary

The final subtask verifies both correct answers and rejected attacks. The tests
cover exact date boundaries, canonical Payments API incidents, tenant
isolation, hostile parameter values, empty results, stable evidence IDs,
deterministic ordering, result limits, and secret-redacted failures.

```mermaid
flowchart TB
    TESTS[Deterministic tests]
    TESTS --> GOOD[Approved bounded queries]
    TESTS --> BAD[Writes injections and bypasses]
    GOOD --> PASS[Exact ordered evidence]
    BAD --> REJECT[Validation error before execution]
```

## End-of-phase design

```mermaid
flowchart LR
    ROUTER[Future retrieval router] --> SPEC[Approved SQL query specification]
    SPEC --> GUARD[AST validator and allowlist]
    GUARD --> EXEC[Bound-parameter executor]
    EXEC --> DATA[(Tenant-scoped records)]
    DATA --> EV[Normalized Evidence]
    EV --> WORKFLOW[Future evidence workflow]
```

End-of-phase qualities:

- Read-only by construction, not merely by prompt instruction.
- Tenant scope is validated and injected by the executor.
- Query values remain separate from SQL syntax.
- Results are deterministic, bounded, and citation-ready.
- SQLite tests the same contract that can sit in front of configured relational
  infrastructure later.
