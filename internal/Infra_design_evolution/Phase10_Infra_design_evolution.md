# Phase 10 — Infrastructure Design Evolution

## Default local wiring

Phase 10 adds no container or network dependency. All planning nodes run inside
the Python process using deterministic rules.

```mermaid
flowchart TB
    subgraph PROCESS[Python application process]
        STATE[ResearchState]
        ANALYZE[Analyze node]
        ASSESS[Complexity node]
        DECOMP[Decompose node]
        ROUTE[Routing node]
        STATE --> ANALYZE --> ASSESS --> DECOMP --> ROUTE
    end
```

## Component wiring

```mermaid
flowchart LR
    SETTINGS[Settings: maximum sub-questions] --> DECOMP[Decompose]
    RULES[Deterministic rules] --> ANALYZE[Analyze]
    RULES --> ASSESS[Assess]
    RULES --> ROUTE[Route]
    ANALYZE --> STATE[Typed state]
    ASSESS --> STATE
    DECOMP --> STATE
    ROUTE --> STATE
```

Configuration controls only the safe bound. It does not change tenant data or
connect directly to retrieval stores.

## Optional provider route

```mermaid
flowchart TD
    QUESTION[Question encoded as data] --> ANALYZE[Analyze node]
    ANALYZE --> LOCAL[Deterministic result]
    ANALYZE -. optional hint .-> LLM[Configured LLM adapter]
    LLM --> VALIDATE[JSON schema and source-text validation]
    VALIDATE -->|valid| LOCAL
    VALIDATE -->|invalid| FALLBACK[Safe local fallback]
    LLM -->|failure| FALLBACK
```

The default fake provider returns no accepted hint, so offline behavior remains
deterministic. A real provider is optional and cannot introduce an entity or
time phrase absent from the original question.

## Future retrieval handoff

```mermaid
flowchart LR
    ROUTER[Phase 10 routing plan] --> SQL[Phase 6 SQL]
    ROUTER --> GRAPH[Phase 7 graph]
    ROUTER --> VECTOR[Phase 8 semantic documents]
    ROUTER --> HYBRID[Phase 8 hybrid documents]
    SQL -. executed later .-> EVIDENCE[Phase 11 evidence collection]
    GRAPH -. executed later .-> EVIDENCE
    VECTOR -. executed later .-> EVIDENCE
    HYBRID -. executed later .-> EVIDENCE
```

No database, Qdrant, or Neo4j call occurs during planning. The handoff is a
small typed plan, keeping infrastructure failures out of query classification.

## Failure and safety boundary

```mermaid
flowchart TD
    INPUT[Question] --> GUARD[Prompt-injection inspection]
    GUARD --> FLAGS[Inspectable safety decision]
    INPUT --> BOUNDS[Length and decomposition bounds]
    FLAGS --> PLAN[Deterministic plan]
    BOUNDS --> PLAN
    ERROR[Provider error] --> REDACT[Secret redaction]
    REDACT --> PLAN
```

Phase 10 reports safe error metadata and continues with local rules. It neither
executes instructions embedded in the question nor opens a network connection
in the default test path.
