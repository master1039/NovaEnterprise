"""Replaceable byte cache and tenant-scoped JSON session facade."""

from __future__ import annotations

import json
from collections.abc import Callable
from threading import Lock
from time import monotonic
from typing import Any, Protocol, runtime_checkable

from backend.app.core.config import Settings, get_settings


@runtime_checkable
class CacheBackend(Protocol):
    def get(self, key: str) -> bytes | None: ...

    def set(self, key: str, value: bytes, *, ttl_seconds: int | None = None) -> None: ...

    def delete(self, key: str) -> bool: ...


class InMemoryCache:
    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._values: dict[str, tuple[bytes, float | None]] = {}
        self._lock = Lock()

    def get(self, key: str) -> bytes | None:
        with self._lock:
            stored = self._values.get(key)
            if stored is None:
                return None
            value, expires_at = stored
            if expires_at is not None and expires_at <= self._clock():
                del self._values[key]
                return None
            return value

    def set(self, key: str, value: bytes, *, ttl_seconds: int | None = None) -> None:
        if ttl_seconds is not None and ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        expires_at = self._clock() + ttl_seconds if ttl_seconds is not None else None
        with self._lock:
            self._values[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._values.pop(key, None) is not None


class RedisCache:
    def __init__(self, *, client: Any) -> None:
        self.client = client

    def get(self, key: str) -> bytes | None:
        value = self.client.get(key)
        if value is None or isinstance(value, bytes):
            return value
        return str(value).encode()

    def set(self, key: str, value: bytes, *, ttl_seconds: int | None = None) -> None:
        self.client.set(key, value, ex=ttl_seconds)

    def delete(self, key: str) -> bool:
        return bool(self.client.delete(key))


class SessionCache:
    def __init__(self, backend: CacheBackend, *, tenant_id: str, ttl_seconds: int = 3600) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id must not be blank")
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        self.backend = backend
        self.tenant_id = tenant_id
        self.ttl_seconds = ttl_seconds

    def _key(self, session_id: str) -> str:
        if not session_id.strip():
            raise ValueError("session_id must not be blank")
        return f"session:{len(self.tenant_id)}:{self.tenant_id}:{session_id}"

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
        self.backend.set(self._key(session_id), encoded, ttl_seconds=self.ttl_seconds)

    def load(self, session_id: str) -> dict[str, Any] | None:
        encoded = self.backend.get(self._key(session_id))
        if encoded is None:
            return None
        state = json.loads(encoded)
        if not isinstance(state, dict):
            raise ValueError("cached session state must be a JSON object")
        return state

    def delete(self, session_id: str) -> bool:
        return self.backend.delete(self._key(session_id))


def get_cache(settings: Settings | None = None, *, client: Any | None = None) -> CacheBackend:
    resolved = settings or get_settings()
    if resolved.cache_backend == "memory":
        return InMemoryCache()
    if client is None:
        try:
            from redis import Redis
        except ImportError as exc:
            raise RuntimeError("redis cache requires the optional 'redis' package") from exc
        client = Redis.from_url(resolved.redis_url)
    return RedisCache(client=client)
