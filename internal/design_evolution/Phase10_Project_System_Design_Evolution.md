# Phase 10 — Project System Design Evolution

## Starting point

Earlier phases supplied retrieval engines, but callers still had to choose one.

```mermaid
flowchart LR
    Q[Business question] --> GAP[No shared planning layer]
    GAP -. manual choice .-> SQL[SQL retrieval]
    GAP -. manual choice .-> GRAPH[Graph retrieval]
    GAP -. manual choice .-> DOC[Document retrieval]
```

## P10-1 — Typed state and node contracts

```mermaid
flowchart LR
    INPUT[Validated question] --> STATE[ResearchState]
    STATE --> ANALYSIS[QueryAnalysis]
    STATE --> SUBS[SubQuestion list]
    STATE --> PLAN[RetrievalRoute list]
    STATE --> AUDIT[Decision and error codes]
```

One immutable state shape prevents nodes from passing informal dictionaries.
The declared node sequence makes progress inspectable without exposing hidden
reasoning.

## P10-2 — Analysis and complexity

```mermaid
flowchart TD
    Q[Question as data] --> RULES[Deterministic analysis]
    Q --> OPTIONAL[Optional validated LLM hint]
    OPTIONAL --> CHECK[Must occur in original question]
    CHECK --> MERGE[Validated entity and time hints]
    RULES --> RESULT[Intent, entity, time, complexity]
    MERGE --> RESULT
    OPTIONAL -->|invalid or unavailable| RULES
```

Deterministic rules stay authoritative. Relative time expressions remain
unresolved rather than silently using the machine clock.

## P10-3 — Bounded decomposition

```mermaid
flowchart LR
    COMPLEX[Complex question] --> SPLIT[Deterministic decomposition]
    LIMIT[NOVA_MAX_SUBQUESTIONS] --> SPLIT
    SPLIT --> SQ1[sq1]
    SPLIT --> SQ2[sq2]
    SPLIT --> SQN[Up to configured maximum]
    SPLIT --> NOTE[Truncation decision when bounded]
```

The default maximum is four and validation permits only one through eight.
Duplicate sub-questions are removed while order stays stable.

## P10-4 — Retrieval routing

```mermaid
flowchart TD
    SUB[Typed sub-question] --> ROUTER[Deterministic router]
    ROUTER -->|semantic document lookup| VECTOR[Vector]
    ROUTER -->|structured records| SQL[SQL]
    ROUTER -->|relationships| GRAPH[Graph]
    ROUTER -->|narrative plus exact terms| HYBRID[Hybrid]
    VECTOR --> PLAN[Typed retrieval plan]
    SQL --> PLAN
    GRAPH --> PLAN
    HYBRID --> PLAN
```

Routing creates plans only. Existing retrievers remain separate and execute in
the later evidence workflow.

## End-of-phase design

```mermaid
flowchart LR
    QUESTION[Question] --> ANALYZE[Analyze]
    ANALYZE --> ASSESS[Assess complexity]
    ASSESS --> DECOMPOSE[Bounded decomposition]
    DECOMPOSE --> ROUTE[Route each sub-question]
    ROUTE --> STATE[Inspectable ResearchState]
    STATE --> FUTURE[Phase 11 evidence workflow]
```

Phase 10 ends with a deterministic and provider-neutral planning boundary that
can be persisted and displayed before any retrieval tool is called.
