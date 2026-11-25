# NovaEnterprise

NovaEnterprise is an enterprise knowledge and decision-intelligence platform.
The repository currently implements seven merged phases plus the Phase 8
feature branch: a repeatable Python/FastAPI runtime; shared schemas and tenant-aware
persistence; an
identity/security boundary with local demo authentication, central roles,
request correlation, bounded rate limiting and auditing, content guardrails,
secret redaction, and destructive-action approvals; and provider/storage
abstractions with deterministic LLM and embedding providers, tenant-scoped
memory vector and graph stores, and a local cache/session facade. Phase 5 adds
validated Markdown, text, and PDF loading; deterministic chunking; guarded
entity extraction; and repeatable relational/vector/graph indexing.

Phase 6 adds safe relational retrieval: an
SQLGlot AST validator, strict table/column allowlists, mandatory tenant filters,
parameterized incident templates, bounded deterministic execution, and
normalization into shared SQL evidence.

Phase 7 maps relational enterprise records into a typed,
tenant-scoped graph and adds parameterized customer-impact, service-ownership,
and bounded expansion traversals that return shared graph Evidence.

The Phase 8 feature branch adds tenant-scoped hybrid document retrieval. It
combines semantic vector search with deterministic BM25, uses reciprocal-rank
fusion and reranking, removes duplicate chunks, preserves citation metadata,
and returns truthful partial or degraded outcomes when adapters fail.

Qdrant, Neo4j, Redis, and real AI providers are optional adapters and are not
required by the offline test path. Retrieval workflows, agents, business APIs,
the frontend, and containers described in `docs/` remain later-phase targets.

## Provider defaults

The safe local configuration is `LLM_PROVIDER=fake`,
`EMBEDDING_PROVIDER=fake`, `VECTOR_STORE=memory`, `GRAPH_STORE=memory`, and
`CACHE_BACKEND=memory`. These implementations are deterministic and require no
network, API key, or external service. Real providers are selected through
settings and constructed only with their optional SDK/client configuration.

## Requirements

- Python 3.12+
- GNU Make is optional; equivalent PowerShell commands are shown below.

## Setup

With Make:

```powershell
make setup
Copy-Item .env.example .env
```

PowerShell alternative:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Run the API

```powershell
make run
```

PowerShell alternative:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8001
```

Implemented endpoints:

- `GET /` — service metadata
- `GET /health/live` — process liveness only
- `GET /docs` — generated OpenAPI documentation
- `POST /api/v1/auth/login` — local/test demo login
- `GET /api/v1/auth/me` — authenticated user details

## Create and seed the local database

```powershell
make db-upgrade
make seed
```

PowerShell alternative:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.app.services.seed
```

The default database is `data/enterprise.db`. Re-running the seed command
updates the same stable records without duplicating them.

## Validate or ingest sample documents

Inspect the canonical documents without writing any store:

```powershell
.\.venv\Scripts\python.exe -m backend.app.ingestion.command --dry-run
```

Run repeatable ingestion with the safe SQLite and in-memory adapter defaults:

```powershell
.\.venv\Scripts\python.exe -m backend.app.ingestion.command
```

With Make, use `make ingest-dry-run` or `make ingest`. PDF extraction uses
`pypdf`; the offline path needs no credentials, network, containers, Qdrant, or
Neo4j. External adapters remain optional settings.

## Verify

```powershell
make check
```

PowerShell alternative:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest
```

The test harness blocks external network access and uses isolated SQLite
databases. Checks require no API key, container, cloud service, or running
database server.

Phase 6 SQL retrieval is exercised by `tests/unit/test_sql_retrieval.py`. Phase
7 graph retrieval is covered by `tests/unit/test_graph_retrieval.py`, and Phase
8 hybrid retrieval by `tests/unit/test_hybrid_retrieval.py`. All use offline
adapters and never execute destructive SQL.

## Project guidance

- `TASK.md` contains the dependency-ordered development tracker.
- `AGENTS.md` contains repository commands and conventions.
- `docs/00-problem.md`, `docs/01-prd.md`, and `docs/02-hld.md` describe the
  business problem, requirements, and target architecture.
- `docs/API_CONTRACT.md` and `docs/FRONTEND_ASSUMPTIONS.md` distinguish current
  implemented HTTP behavior from later promised interfaces.
