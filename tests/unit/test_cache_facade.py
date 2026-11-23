"""Cache and session state work offline and swap cleanly to Redis."""

import sys

from backend.app.core.cache import InMemoryCache, RedisCache, SessionCache, get_cache
from backend.app.core.config import Settings


def test_memory_cache_ttl_delete_and_client_isolation() -> None:
    now = [100.0]
    cache = InMemoryCache(clock=lambda: now[0])
    cache.set("a", b"value", ttl_seconds=10)
    assert cache.get("a") == b"value"
    now[0] = 111.0
    assert cache.get("a") is None
    assert cache.delete("missing") is False


def test_session_cache_namespaces_serializes_and_expires() -> None:
    now = [0.0]
    backend = InMemoryCache(clock=lambda: now[0])
    tenant_a = SessionCache(backend, tenant_id="tenant-a", ttl_seconds=30)
    tenant_b = SessionCache(backend, tenant_id="tenant-b", ttl_seconds=30)
    tenant_a.save("session-1", {"status": "running", "step": 2})

    assert tenant_a.load("session-1") == {"status": "running", "step": 2}
    assert tenant_b.load("session-1") is None
    now[0] = 31.0
    assert tenant_a.load("session-1") is None


def test_session_namespace_cannot_collide_when_ids_contain_colons() -> None:
    backend = InMemoryCache()
    SessionCache(backend, tenant_id="a").save("b:c", {"owner": "tenant-a"})
    SessionCache(backend, tenant_id="a:b").save("c", {"owner": "tenant-a-b"})

    assert SessionCache(backend, tenant_id="a").load("b:c") == {"owner": "tenant-a"}
    assert SessionCache(backend, tenant_id="a:b").load("c") == {"owner": "tenant-a-b"}


class StubRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.set_calls: list[dict] = []

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, *, ex=None):
        self.values[key] = value
        self.set_calls.append({"key": key, "value": value, "ex": ex})

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)


def test_redis_adapter_uses_injected_client() -> None:
    client = StubRedisClient()
    cache = RedisCache(client=client)
    cache.set("key", b"value", ttl_seconds=15)
    assert cache.get("key") == b"value"
    assert client.set_calls[0]["ex"] == 15
    assert cache.delete("key") is True


def test_cache_factory_defaults_offline_and_requires_redis_dependency(monkeypatch) -> None:
    assert isinstance(get_cache(Settings(cache_backend="memory")), InMemoryCache)
    assert isinstance(
        get_cache(Settings(cache_backend="redis"), client=StubRedisClient()), RedisCache
    )
    monkeypatch.setitem(sys.modules, "redis", None)
    try:
        get_cache(Settings(cache_backend="redis"))
    except RuntimeError as exc:
        assert "redis" in str(exc)
    else:
        raise AssertionError("missing Redis dependency was not reported")
