# Phase 3 Infrastructure Design Evolution

## Scope

Phase 3 changes component wiring inside the FastAPI process. It creates no
Docker image, Compose service, network, port, Redis server, or external identity
provider. The only listening process remains Uvicorn on the configured local
address, normally port 8001.

## Beginning topology

```mermaid
flowchart LR
    Browser[Client] -->|HTTP 8001| API[FastAPI process]
    API --> SQLite[(Local SQLite file)]
    API --> Stdout[JSON logs]
```

Phase 2 persistence was available, but inbound traffic had no identity or
traffic-control corridor.

## Authentication wiring

Demo login and token verification run in the same Python process.

```mermaid
flowchart LR
    Client -->|POST configured-prefix/auth/login| Router[Auth router]
    Router --> Demo[Local demo accounts]
    Router --> Sign[HMAC SHA-256 signer]
    Sign -->|Bearer JWT| Client
    Client -->|Authorization header| Verify[JWT verifier]
    Verify --> Role[Central role dependency]
    Role --> Protected[Protected route]
```

No password database or authentication network call is used. Demo credentials
are deliberately disabled in staging and production. Production identity is a
future adapter, not a hidden Phase 3 service.

## Middleware routing

```mermaid
sequenceDiagram
    participant C as Client
    participant X as Request context
    participant A as Audit trail
    participant R as Rate limiter
    participant F as FastAPI
    C->>X: Request
    X->>A: Attach trusted request ID
    A->>R: Begin safe audit timing
    alt client window is full
        R-->>A: 429 plus Retry-After
    else request allowed
        R->>F: Dispatch route
        F-->>R: Response or safe error
        R-->>A: Result
    end
    A-->>X: Store and log safe metadata
    X-->>C: X-Request-ID response
```

The limiter and audit trail are local memory components protected by locks.
They work across threads in one process but are not shared between multiple
workers or machines. The audit trail retains only the configured number of most
recent records.

## Content and action wiring

Guardrails and approvals are library components, not network services.

```mermaid
flowchart TB
    FutureIngest[Future ingestion service] --> Guard[Guardrail functions]
    Guard --> Flag[Inspection result]
    Guard --> Wrapped[Escaped data wrapper]
    Logs[Potential log text] --> Scrub[Secret redactor]
    Scrub --> Output[Safer output]
    FutureDelete[Future deletion service] --> Approval[Approval service]
    Approval --> Memory[(Process memory)]
```

Phase 3 prepares these boundaries before later ingestion and deletion endpoints
exist. This avoids coupling their security behavior to a future UI or storage
provider.

## Configuration routing

```mermaid
flowchart LR
    Env[Local environment] --> Settings[Pydantic settings]
    Settings --> Prefix[API prefix]
    Settings --> JWT[JWT issuer, audience, secret, TTL]
    Settings --> Limit[Requests per minute]
    Settings --> Audit[Maximum audit records]
    Settings --> Tenant[Default demo tenant]
```

Secrets stay in environment settings. `.env` is ignored; `.env.example` contains
only an explicitly local demo value and instructions to replace it.

## End-of-phase local topology

```mermaid
flowchart TB
    subgraph Machine[Developer machine]
        Client
        subgraph Process[Uvicorn and FastAPI process]
            Context[Request ID]
            Audit[Bounded audit memory]
            Rate[Fixed-window rate memory]
            Auth[Demo auth and JWT]
            Routes[API routes]
            Guardrails
            Approvals[Approval memory]
        end
        SQLite[(SQLite)]
        Logs[JSON stdout]
    end
    Client --> Context --> Audit --> Rate --> Routes
    Routes --> Auth
    Routes --> SQLite
    Audit --> Logs
    Guardrails -.used by later ingestion.-> Routes
    Approvals -.used by later destructive APIs.-> Routes
```

## Docker and production evolution

Phase 3 has no Docker networking. A later multi-instance design must replace
process-local coordination with shared services:

```mermaid
flowchart LR
    Gateway[Future gateway] --> API1[Backend instance 1]
    Gateway --> API2[Backend instance 2]
    API1 --> Redis[(Future shared Redis limiter)]
    API2 --> Redis
    API1 --> Postgres[(Future durable audit and approvals)]
    API2 --> Postgres
    Identity[Future identity provider] --> API1
    Identity --> API2
```

Redis, PostgreSQL persistence, external identity, proxy trust rules, key
rotation, and container wiring remain later delivery work. Phase 3 supplies
testable interfaces and honest local behavior without claiming those services
already run.

## Operational summary

One request enters one process, receives a safe correlation ID, is checked
against a local traffic window, is audited using limited non-secret metadata,
and then reaches authentication and the route. Untrusted information and
destructive actions have separate safety boundaries. This topology is enough
for deterministic offline development and a clear stepping stone to shared
production infrastructure.

The final verification exercised successful, unauthorized, forbidden,
rate-limited, and unexpected-error responses and confirmed that all of them
carry the expected safe error or request-correlation behavior.
