# NovaEnterprise

NovaEnterprise is an enterprise knowledge and decision-intelligence platform.
The repository currently implements the Phase 1 runtime foundation: a
repeatable Python workspace, a thin FastAPI shell, structured JSON logging,
safe error responses, offline tests, and written API/frontend contracts.

The retrieval, persistence, agent, memory, frontend, and container capabilities
described in `docs/` are later-phase targets and are not implemented yet.

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

The test harness blocks external network access. Phase 1 checks require no API
key, database, container, or cloud service.

## Project guidance

- `TASK.md` contains the dependency-ordered development tracker.
- `AGENTS.md` contains repository commands and conventions.
- `docs/00-problem.md`, `docs/01-prd.md`, and `docs/02-hld.md` describe the
  business problem, requirements, and target architecture.
- `docs/API_CONTRACT.md` and `docs/FRONTEND_ASSUMPTIONS.md` distinguish current
  Phase 1 behavior from later promised interfaces.
