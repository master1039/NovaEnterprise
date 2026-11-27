# Phase 11 — Infrastructure Design Evolution

## Default local wiring

Phase 11 runs inside the Python process. Tests use injected executors and
LangGraph's in-memory checkpointer, so no container or network is required.

```mermaid
flowchart TB
    subgraph PROCESS[Python process]
        GRAPH[Compiled LangGraph]
        RUNTIME[WorkflowRuntime]
        CHECKPOINT[(InMemorySaver)]
        GRAPH --> RUNTIME
        GRAPH --> CHECKPOINT
    end
```

## Retrieval component wiring

```mermaid
flowchart LR
    GRAPH[Collect node] --> RUNTIME[Executor registry]
    RUNTIME --> VECTOR[Vector executor]
    RUNTIME --> SQL[SQL executor]
    RUNTIME --> GRAPHRET[Graph executor]
    RUNTIME --> HYBRID[Hybrid executor]
    VECTOR --> BATCH[RetrievalBatch]
    SQL --> BATCH
    GRAPHRET --> BATCH
    HYBRID --> BATCH
    BATCH --> STATE[ResearchState Evidence]
```

The runtime is an adapter boundary. Phase 12 can inject real tenant-scoped
retrievers; Phase 11 tests inject deterministic local functions.

## Checkpoint and routing flow

```mermaid
sequenceDiagram
    participant API as Future API worker
    participant LG as LangGraph
    participant CP as Checkpointer
    participant RT as Retrieval runtime
    API->>LG: invoke state with thread_id
    LG->>RT: execute typed routes
    RT-->>LG: Evidence batches
    LG->>CP: save state after nodes
    CP-->>API: resumable thread snapshot
```

The local checkpointer lasts only for the process lifetime. A later production
deployment may replace it with a persistent LangGraph checkpointer without
changing the node contracts.

## Bounded correction wiring

```mermaid
flowchart TD
    SETTINGS[NOVA_MAX_CORRECTIVE_ROUNDS] --> DECIDE{Missing and round available?}
    DECIDE -->|yes| RETRY[Retry missing routes only]
    RETRY --> RECHECK[Recheck coverage]
    RECHECK --> DECIDE
    DECIDE -->|no| VERIFY[Continue to verification]
```

The counter lives in validated state and the configured maximum is capped, so
an unavailable dependency cannot create infinite traffic or an agent loop.

## Failure and trust boundary

```mermaid
flowchart LR
    ADAPTER[Retriever or provider] --> SAFE[Redact errors]
    ADAPTER --> DATA[Evidence treated as data]
    DATA --> VERIFY[Claim verification]
    SAFE --> TRACE[Safe workflow trace]
    VERIFY --> CITE[Citation validation]
    TRACE --> OUTPUT[Inspectable result]
    CITE --> OUTPUT
```

Phase 11 creates no SQL, Qdrant, Neo4j, Redis, or external-model connection by
itself. Those dependencies remain behind existing adapters and injected
executors.
