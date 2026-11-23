# NovaEnterprise API Contract

## Status and scope

This document is the shared HTTP agreement for backend and frontend work.

- **Implemented in Phase 1:** service metadata, liveness, OpenAPI generation,
  centralized validation errors, and safe unexpected-error responses.
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
| Request correlation | `X-Request-ID` after Phase 3 introduces middleware |
| Authentication | Bearer token after Phase 3; absent from Phase 1 routes |
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
Phase 1 OpenAPI contains only `/` and `/health/live` as application routes.

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
