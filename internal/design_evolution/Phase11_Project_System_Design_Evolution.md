# Phase 11 — Project System Design Evolution

## Starting point

Phase 10 could plan retrieval but did not execute or combine results.

```mermaid
flowchart LR
    PLAN[Phase 10 retrieval plan] --> GAP[No evidence workflow]
    GAP -. future .-> ANSWER[Answer with citations]
```

## P11-1 — Evidence collection

```mermaid
flowchart LR
    ROUTES[Typed routes] --> EXEC[Injected executors]
    EXEC --> SQL[SQL Evidence]
    EXEC --> GRAPH[Graph Evidence]
    EXEC --> DOC[Document Evidence]
    SQL --> MERGE[Normalize and deduplicate]
    GRAPH --> MERGE
    DOC --> MERGE
    MERGE --> MAP[Evidence mapped to sub-questions]
```

Failures stay attached to the affected sub-question, while successful paths
continue. Deduplication uses stable source identity and preserves coverage
provenance through the sub-question mapping.

## P11-2 — Missing evidence and bounded correction

```mermaid
flowchart TD
    CHECK{Every route has Evidence?}
    CHECK -->|yes| VERIFY[Verify claims]
    CHECK -->|no and rounds remain| RETRY[Corrective retrieval]
    RETRY --> CHECK
    CHECK -->|no rounds remain| VERIFY
```

`NOVA_MAX_CORRECTIVE_ROUNDS` defaults to one and is bounded from zero through
three. The conditional graph edge therefore cannot become an unbounded loop.

## P11-3 — Claim verification

```mermaid
flowchart LR
    CANDIDATE[Candidate claim] --> LINKS{Evidence IDs resolve?}
    LINKS -->|no| UNSUPPORTED[Unsupported]
    LINKS -->|yes| SAFE{Evidence safe and content supports claim?}
    SAFE -->|no| UNSUPPORTED
    SAFE -->|yes| VERIFIED[Verified claim]
```

The deterministic verifier is intentionally conservative. It excludes hostile
content and rejects claims containing substantive terms absent from the linked
evidence.

## P11-4 — Answer and citations

```mermaid
flowchart LR
    CLAIMS[Verified claims only] --> SYNTH[Synthesize answer]
    EVIDENCE[Stable Evidence IDs] --> CITE[Build citation map]
    CITE --> SYNTH
    SYNTH --> VALIDATE[Validate every marker]
    VALIDATE --> RESULT[Answer plus invalid and unused lists]
```

If no verified claim exists, synthesis returns an explicit insufficient-
evidence message with no citation instead of guessing.

## P11-5 — End-of-phase LangGraph

```mermaid
flowchart TD
    START --> ANALYZE[Analyze query]
    ANALYZE --> ASSESS[Assess complexity]
    ASSESS --> DECOMPOSE[Decompose]
    DECOMPOSE --> ROUTE[Route retrieval]
    ROUTE --> COLLECT[Collect Evidence]
    COLLECT --> MISSING[Check missing]
    MISSING -->|bounded retry| CORRECT[Corrective retrieval]
    CORRECT --> MISSING
    MISSING -->|continue| VERIFY[Verify evidence]
    VERIFY --> ANSWER[Synthesize answer]
    ANSWER --> CITATIONS[Verify citations]
    CITATIONS --> END
    CHECKPOINT[(Thread checkpoint)] -. state after each node .-> MISSING
```

The completed graph is explicit, checkpointed, deterministic with local
executors, and inspectable without exposing hidden reasoning.
