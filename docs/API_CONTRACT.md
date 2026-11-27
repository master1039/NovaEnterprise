# NovaEnterprise API Contract

## Status and scope

This document is the shared HTTP agreement for backend and frontend work.

- **Implemented in Phase 1:** service metadata, liveness, OpenAPI generation,
  centralized validation errors, and safe unexpected-error responses.
- **Implemented internally in Phase 2:** shared domain/read schemas, normalized
  Evidence, and persistence contracts. Phase 2 adds no public HTTP routes.
- **Implemented in Phase 3:** local demo login, bearer-token validation, central
  role enforcement, request correlation, rate limiting, and request auditing.
- **Implemented internally in Phase 4:** provider-neutral LLM, embedding,
  vector, graph, cache, and session boundaries. Phase 4 adds no public routes.
- **Implemented internally in Phase 5:** validated document loading, chunking,
  guardrail-first extraction, and coordinated relational/vector/graph indexing.
  Phase 5 adds a local command but no public HTTP routes.
- **Implemented internally in Phase 6:** AST-validated,
  tenant-scoped, parameterized SQL retrieval normalized into shared Evidence.
  Phase 6 adds no public HTTP routes.
- **Implemented internally in Phase 7:** deterministic
  enterprise graph seeding and typed, parameterized traversals normalized into
  graph Evidence. Phase 7 adds no public HTTP routes.
- **Implemented internally in Phase 8:** tenant-scoped
  semantic and BM25 document retrieval, reciprocal-rank fusion, deterministic
  reranking, and safety-aware document Evidence. Phase 8 adds no public HTTP
  routes.
- **Implemented internally in Phase 9:** four isolated
  memory scopes with short-term cache and durable SQL adapters, provenance, and
  record/recall/clear operations. Phase 9 adds no public HTTP routes.
- **Implemented internally in Phase 10:** typed research
  state, deterministic query analysis, bounded decomposition, and retrieval
  routing plans. Phase 10 adds no public HTTP routes or retrieval execution.
- **Implemented internally on the Phase 11 feature branch:** checkpointed
  LangGraph orchestration, normalized Evidence collection, bounded corrective
  retrieval, claim verification, answer synthesis, and citation validation.
  Phase 11 adds no public HTTP routes.
- **Contracted for later phases:** versioned research, events, documents, graph,
  and enterprise browse APIs. These routes are not implemented yet.

The contract describes public behavior, not internal Python functions. Later
changes to a route, payload, status code, or error shape must update this file,
the backend schema, tests, and frontend type together.

## Conventions

| Item | Contract |
|---|---|
| API base for business routes | `/api/v1` |
| Content type | `application/json` unless a documented upload says otherwise |
| Identifiers | Opaque strings; clients must not parse meaning from them |
| Dates and times | ISO 8601 strings with timezone information |
| Request correlation | Every response carries a validated or generated `X-Request-ID` |
| Authentication | Bearer JWT for protected routes; system routes stay public |
| Unknown fields | Clients ignore unknown response fields for forward compatibility |
| Hidden reasoning | Never returned; expose decisions, evidence, queries, and timings only |

## Error envelope

All handled errors use this top-level shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request could not be validated.",
    "details": []
  }
}
```

- `code` is stable and machine-readable.
- `message` is safe for a user interface.
- `details` is optional and contains structured validation information.
- Unexpected failures return code `internal_error` and never expose stack
  traces, credentials, database details, or model reasoning.

## Implemented Phase 1 endpoints

### `GET /`

Returns public service metadata.

Response `200`:

```json
{
  "name": "NovaEnterprise",
  "status": "available",
  "version": "0.1.0"
}
```

### `GET /health/live`

Confirms only that the API process is alive. It does not check databases or
future external adapters.

Response `200`:

```json
{
  "service": "NovaEnterprise",
  "status": "ok"
}
```

### `GET /openapi.json` and `GET /docs`

FastAPI-generated schema and interactive documentation for implemented routes.
The OpenAPI document also contains the Phase 3 authentication routes below.

## Implemented Phase 3 authentication

### `POST /api/v1/auth/login`

Available only in local and test environments. The deterministic demo accounts
are `viewer`, `analyst`, and `admin`; each uses `demo-<role>` as its local-only
password. A successful response contains a bearer access token, expiry in
seconds, and the user's ID, username, role, and tenant ID.

### `GET /api/v1/auth/me`

Requires a valid bearer token and returns the authenticated user contract.
Tokens validate their signature, algorithm, issuer, audience, issued-at time,
expiry, role, and tenant. Production rejects the default local signing secret.

## Planned research contract

The following section freezes the baseline expected by the future frontend. It
does not claim that the routes exist in Phase 1.

### `POST /api/v1/research`

Starts research without waiting for the full workflow.

Request:

```json
{
  "question": "Which customers were impacted by the Payments API last quarter?"
}
```

Rules:

- `question` is required and contains 5–2000 characters.
- The route persists a session and schedules background work.

Response `202`:

```json
{
  "session_id": "opaque-session-id",
  "status": "running"
}
```

### `GET /api/v1/research/{session_id}`

Returns the latest persisted session state.

```json
{
  "session_id": "opaque-session-id",
  "status": "running",
  "question": "Original question",
  "progress": {
    "current_step": "route_retrieval",
    "completed_steps": 3,
    "total_steps": 8
  },
  "answer": null,
  "evidence": [],
  "citations": [],
  "errors": []
}
```

`status` is one of `running`, `completed`, `failed`, or `partial`. Completed or
partial sessions may contain an answer and citations. Clients must tolerate
additional progress and evidence metadata.

### `GET /api/v1/research/{session_id}/events`

Returns safe, inspectable workflow events in chronological order.

```json
{
  "session_id": "opaque-session-id",
  "events": [
    {
      "sequence": 1,
      "event_type": "node_completed",
      "name": "analyze_query",
      "status": "completed",
      "duration_ms": 14,
      "metadata": {}
    }
  ]
}
```

Events may expose node names, selected strategies, executed read-only queries,
timings, evidence identifiers, and failures. They never expose hidden
chain-of-thought.

## Planned supporting APIs

Exact schemas are added with their implementing phase. The stable route groups
are reserved now to prevent frontend/backend naming drift.

| Route group | Purpose | Planned phase |
|---|---|---:|
| `/api/v1/documents` | Upload, browse, ingest, and approval-gated deletion | 12 |
| `/api/v1/graph` | Browse and expand knowledge-graph nodes | 12 |
| `/api/v1/customers` | Read enterprise customer records | 12 |
| `/api/v1/incidents` | Read incident records | 12 |
| `/api/v1/decisions` | Read decision records | 12 |
| `/api/v1/projects` | Read project records | 12 |
| `/api/v1/tickets` | Read ticket records | 12 |
| `/health/ready` | Report dependency readiness and degradation | 12 |

## Authorization baseline for later phases

| Role | Baseline permissions |
|---|---|
| `viewer` | Browse records, documents, dashboards, and existing research sessions |
| `analyst` | Viewer access plus starting research, uploads, read-only Cypher, and own memory |
| `admin` | Analyst access plus privileged reindex, deletion, and approval decisions |

Servers enforce authorization. Hiding a button in the frontend is never an
authorization control.

## Compatibility rules

1. Additive response fields are backward compatible.
2. Removing or renaming a field requires a versioned contract change.
3. Applied database migrations are not rewritten to simulate compatibility.
4. Every breaking change needs coordinated backend, frontend, and test work.
5. The frontend treats missing optional services as a degraded state, not as
   permission to fabricate data.
