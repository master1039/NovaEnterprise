"""Shared offline fixtures for the Phase 1 test harness."""

from __future__ import annotations

import socket
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def deterministic_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Give every test known settings and reject accidental network access."""

    monkeypatch.setenv("NOVA_APP_ENV", "test")
    monkeypatch.setenv("NOVA_DEBUG", "false")
    monkeypatch.setenv("NOVA_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("NOVA_API_PREFIX", "/api/v1")

    original_connect = socket.socket.connect

    def guard_connect(instance: socket.socket, address: object) -> object:
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1", "localhost"}:
            return original_connect(instance, address)
        raise RuntimeError("External network access is disabled in the test suite")

    def deny_create_connection(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("External network access is disabled in the test suite")

    monkeypatch.setattr(socket, "create_connection", deny_create_connection)
    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Return an in-process client; no server or network socket is required."""

    app = create_app(get_settings())
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
