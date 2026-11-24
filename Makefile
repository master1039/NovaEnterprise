PYTHON ?= python
VENV_DIR ?= .venv

ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
else
VENV_PYTHON := $(VENV_DIR)/bin/python
endif

.PHONY: setup run test lint format format-check check db-upgrade db-downgrade seed ingest ingest-dry-run clean

setup:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"

run:
	$(VENV_PYTHON) -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8001

test:
	$(VENV_PYTHON) -m pytest

lint:
	$(VENV_PYTHON) -m ruff check .

format:
	$(VENV_PYTHON) -m ruff format .

format-check:
	$(VENV_PYTHON) -m ruff format --check .

check: lint format-check test

db-upgrade:
	$(VENV_PYTHON) -m alembic upgrade head

db-downgrade:
	$(VENV_PYTHON) -m alembic downgrade base

seed: db-upgrade
	$(VENV_PYTHON) -m backend.app.services.seed

ingest: db-upgrade
	$(VENV_PYTHON) -m backend.app.ingestion.command

ingest-dry-run:
	$(VENV_PYTHON) -m backend.app.ingestion.command --dry-run

clean:
	$(PYTHON) -c "import pathlib,shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	$(PYTHON) -c "import pathlib,shutil; [shutil.rmtree(pathlib.Path(p), ignore_errors=True) for p in ('.pytest_cache','.ruff_cache','htmlcov')]"
