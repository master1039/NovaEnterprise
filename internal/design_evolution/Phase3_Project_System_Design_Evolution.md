# Phase 3 Project System Design Evolution

## Starting point

Phase 2 ended with shared schemas, repositories, migrations, and canonical
data. The HTTP shell was still public and had no caller identity or uniform
request controls.

```mermaid
flowchart LR
    Client --> FastAPI
    FastAPI --> PublicRoutes[Root and liveness]
    FastAPI --> Persistence[Phase 2 persistence]
```

## P3-1: central identity boundary

The first evolution introduced an authenticated-user contract, signed access
tokens, and hierarchical role enforcement.

```mermaid
flowchart TB
    Header[Authorization header] --> JWT[HS256 verification]
    JWT --> Claims[Issuer, audience, time, user, role, tenant]
    Claims --> User[AuthenticatedUser]
    User --> Requirement[require_role]
    Requirement --> Route[Protected route]
```

The important design choice is dependency injection: routes declare the
minimum role, while one security module validates every token and permission.
This prevents security behavior from drifting between endpoints.

## P3-2: local identity provider

The second step added an offline login adapter and a self-inspection endpoint.

```mermaid
sequenceDiagram
    participant U as User
    participant Login as Demo login
    participant Signer as Token signer
    participant Me as Authenticated endpoint
    U->>Login: Local role credentials
    Login->>Signer: Valid user and configured tenant
    Signer-->>U: Signed token and safe user
    U->>Me: Bearer token
    Me-->>U: Verified user contract
```

Demo identity is enabled only for local and test environments. Production must
provide a non-demo secret of at least 32 characters. The token format remains a
standard JWT contract that a later identity provider can replace.

## P3-3: cross-cutting request controls

Request controls became middleware because correlation, limiting, and auditing
must apply consistently rather than depend on each route remembering them.

```mermaid
flowchart LR
    Client --> Context[RequestContextMiddleware]
    Context --> Audit[AuditMiddleware]
    Audit --> Limit[RateLimitMiddleware]
    Limit --> Router[FastAPI router]
    Router --> Limit
    Limit --> Audit
    Audit --> Context
    Context --> Response[Correlated response]
```

Starlette runs the last-added middleware first, so application construction
adds the layers in reverse execution order. Request context is outermost, audit
observes both accepted and rate-limited outcomes, and the limiter protects the
route. The centralized 500 handler also copies the stored request ID because
unexpected errors are finalized outside normal user middleware.

Phase 3 implementations are bounded local adapters:

- the fixed-window limiter is thread-safe and keyed by client address;
- the audit trail is thread-safe and retains only a configured maximum; and
- structured audit logs omit bodies, query parameters, credentials, and tokens.

## P3-4: content trust and human control

The final step protects two different boundaries: information entering an AI
workflow and destructive actions leaving it.

```mermaid
flowchart TB
    subgraph InputBoundary[Untrusted information boundary]
        Content --> Inspect
        Inspect --> Escape
        Inspect --> Reasons
        Escape --> WrappedData
    end
    subgraph ActionBoundary[Destructive action boundary]
        Request --> Pending
        Pending --> AdminDecision
        AdminDecision --> ExactMatch
        ExactMatch --> OneUse
    end
```

Guardrails scan suspicious phrases, HTML-escape content, and add an explicit
data-only instruction. Secret redaction handles bearer credentials, passwords,
API keys, AWS-style access keys, and private-key blocks before text is logged.

Approvals are tenant-scoped state machines. The action and resource must match
at consumption time, and consumption is atomic under a lock. The Phase 3 store
is in memory because no destructive public API exists yet; later persistence
can implement the same service contract.

## End-of-phase design

```mermaid
flowchart TB
    Client --> SecurityCorridor
    subgraph SecurityCorridor[Phase 3 request corridor]
        RequestID[Request identity]
        Audit[Bounded audit]
        Rate[Rate limit]
        Auth[JWT and roles]
    end
    SecurityCorridor --> Existing[Phase 1 and 2 application]
    External[Untrusted evidence] --> Guardrails[Inspect, escape, flag]
    Guardrails --> FutureResearch[Future research workflow]
    FutureMutation[Future destructive API] --> Approval[Admin approval and one-use consumption]
```

The dependency direction remains one-way: API routes use core security;
middleware surrounds the API; guardrails are lower-level utilities; and the
approval service contains no HTTP logic.

## Verification evidence

Phase 3 is covered by deterministic offline tests for token round trips,
signature and expiry failure, production-secret rejection, login, central RBAC,
custom prefixes and tenants, request IDs on successes and failures, rate-limit
responses, middleware audit ordering, bounded auditing, injection detection,
wrapper escaping, secret redaction, cross-tenant approvals, exact resource
matching, and replay prevention.

The final offline repository suite passed 48 tests, with Ruff lint and format
checks clean. The Phase 3 security modules were also exercised through the real
FastAPI middleware and exception stack rather than only as isolated functions.

The Phase 3 tracker rows remain Pending until the feature pull request merges.
