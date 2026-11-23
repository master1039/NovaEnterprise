# NovaEnterprise

NovaEnterprise is an enterprise knowledge and decision-intelligence platform.
The repository currently implements the Phase 1 runtime foundation and the
Phase 2 shared-schema and persistence foundation: a repeatable Python workspace,
a thin FastAPI shell, shared domain and Evidence contracts, tenant-aware
SQLAlchemy models and repositories, migrations, RLS policy SQL, deterministic
sample data, structured logging, safe errors, and offline tests.

Retrieval, agents, memory services, new business APIs, the frontend, and
containers described in `docs/` remain later-phase targets.

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

## Project guidance

- `TASK.md` contains the dependency-ordered development tracker.
- `AGENTS.md` contains repository commands and conventions.
- `docs/00-problem.md`, `docs/01-prd.md`, and `docs/02-hld.md` describe the
  business problem, requirements, and target architecture.
- `docs/API_CONTRACT.md` and `docs/FRONTEND_ASSUMPTIONS.md` distinguish current
  implemented HTTP behavior from later promised interfaces.
