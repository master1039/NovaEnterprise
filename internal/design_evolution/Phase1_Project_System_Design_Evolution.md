# Phase 1 Project System Design Evolution

## Purpose

This document shows how NovaEnterprise evolved during Phase 1, from a single
console script to a verified FastAPI foundation. It describes implemented code;
later business capabilities remain future work.

## Beginning of Phase 1 — the original scaffold

The repository started with project metadata, design documents, and a `main.py`
that printed one greeting.

```mermaid
flowchart LR
    Developer[Developer] -->|python main.py| Python[Python process]
    Python --> Main[main function]
    Main --> Greeting[Console greeting]
    Design[Problem, PRD, and HLD] -.describe future system.-> Developer
```

This baseline proved that Python ran, but it had no web boundary, central
configuration, structured logging, error policy, automated test harness, or API
contract.

## P1-1 — repeatable workspace

P1-1 established a reproducible way to build and operate the project.

```mermaid
flowchart TB
    Contributor[Contributor] --> Setup[Make setup or pip install]
    Project[pyproject.toml] --> Setup
    Lock[uv.lock] --> Setup
    Requirements[requirements.txt] --> Setup
    Setup --> Venv[Local .venv]
    EnvTemplate[.env.example] --> LocalEnv[Untracked .env]
    Make[Makefile] --> Run[Run]
    Make --> Test[Test]
    Make --> Quality[Lint and format check]
    Venv --> Run
    Venv --> Test
    Venv --> Quality
```

Key decisions:

- `pyproject.toml` is the authoritative dependency and tool configuration.
- `uv.lock` makes resolution reproducible.
- `.env.example` contains names and safe defaults, never real secrets.
- Make targets and documented PowerShell alternatives provide the same workflow.
- The mistyped package scaffold was corrected to `src/novaenterprise/__init__.py`.

P1-1 was implemented first because every other Phase 1 task depends on the same
environment and commands.

## P1-2 — backend runtime shell

P1-2 introduced a thin FastAPI application without pulling later business logic
into the foundation.

```mermaid
flowchart TB
    Env[NOVA environment variables] --> Settings[Typed Settings]
    Settings --> Factory[create_app]
    Factory --> FastAPI[FastAPI instance]
    Factory --> Logger[JSON logging]
    Factory --> Handlers[Exception handlers]
    Factory --> Router[System router]
    Router --> Root[GET /]
    Router --> Live[GET /health/live]
    FastAPI --> OpenAPI[OpenAPI and docs]
```

The application factory is the central composition root. Configuration, logging,
errors, and route registration meet there, while each concern remains in its own
module.

### Request behavior

```mermaid
sequenceDiagram
    participant C as Client
    participant F as FastAPI
    participant R as Route
    participant E as Error handler
    participant L as JSON logger
    C->>F: Request
    F->>R: Route and validate
    alt success
        R-->>C: Typed JSON
    else expected failure
        R->>E: ApplicationError
        E->>L: Safe context
        E-->>C: Public error envelope
    else unexpected failure
        R->>E: Exception
        E->>L: Full internal exception
        E-->>C: Generic internal_error
    end
```

The public response is safe and stable; sensitive diagnostic detail stays in the
server log.

## P1-3 — deterministic verification

P1-3 made the foundation testable without cloud dependencies.

```mermaid
flowchart LR
    Command[pytest command] --> Runner[Pytest]
    Fixture[Deterministic environment] --> Runner
    NetworkGuard[External-network guard] --> Runner
    Runner --> Factory[Fresh app instance]
    Factory --> Client[In-process TestClient]
    Client --> Assertions[12 behavior checks]
    Ruff[Ruff lint and format] --> Quality[Quality gate]
    Assertions --> Quality
```

The tests cover:

- central settings and validation;
- service metadata and liveness;
- the exact Phase 1 OpenAPI route set;
- public application, validation, and unexpected-error behavior; and
- JSON log structure and idempotent logging setup.

The test fixture blocks external network access. The suite needs no API key,
database, Docker service, or running web server.

## P1-4 — contract-first collaboration

P1-4 created a written boundary for later frontend and backend development.

```mermaid
flowchart LR
    Requirements[PRD and HLD] --> API[API contract]
    API --> Backend[Later backend routes]
    API --> Frontend[Later typed client]
    Assumptions[Frontend assumptions] --> Frontend
    Assumptions --> API
    Tests[Future contract tests] -.verify.-> Backend
    Tests -.verify.-> Frontend
```

The API contract separates implemented Phase 1 endpoints from planned research
and browse endpoints. The frontend assumptions define polling, roles, citations,
errors, accessibility, and degraded behavior without pretending a frontend
already exists.

## End-of-Phase-1 architecture

```mermaid
flowchart TB
    subgraph Development[Repeatable development environment]
        Metadata[pyproject and lock]
        Commands[Make and PowerShell commands]
        Env[Safe environment template]
    end

    subgraph Runtime[FastAPI runtime shell]
        Factory[Application factory]
        Settings[Central settings]
        Routes[System routes]
        Logs[JSON logging]
        Errors[Safe errors]
    end

    subgraph Verification[Offline quality gate]
        Tests[12 pytest tests]
        Lint[Ruff lint]
        Format[Ruff format check]
    end

    subgraph Contracts[Collaboration boundary]
        API[API contract]
        Frontend[Frontend assumptions]
    end

    Metadata --> Commands
    Env --> Settings
    Commands --> Factory
    Settings --> Factory
    Factory --> Routes
    Factory --> Logs
    Factory --> Errors
    Tests --> Factory
    Lint --> Runtime
    Format --> Runtime
    API -.guides later APIs.-> Runtime
    Frontend -.guides later UI.-> API
```

## Dependency improvements achieved

| Design choice | Dependency problem avoided |
|---|---|
| Workspace before runtime/tests | Competing dependency and command definitions |
| Application factory | Tests or environments manually assembling different apps |
| Central typed settings | Modules reading and interpreting environment variables differently |
| Standard-library JSON logger | Feature modules inventing incompatible log formats |
| Shared error envelope | Each route exposing different or unsafe failures |
| Offline test fixture | Tests requiring paid APIs or unavailable infrastructure |
| Contract-first boundary | Frontend and backend guessing incompatible payloads |

## Deliberate boundaries

Phase 1 contains no database, authentication, retrieval, memory, agent workflow,
frontend, Docker image, or deployment. Those remain isolated in later phases so
the runtime foundation stays small, reviewable, and reusable.

## Completion evidence

Phase 1 completion is supported by:

- all P1-1 through P1-4 artifacts present;
- 12 passing offline tests;
- Ruff lint and format checks passing;
- Python compilation passing;
- `uv.lock` matching `pyproject.toml`; and
- current routes and planned interfaces clearly separated in documentation.
