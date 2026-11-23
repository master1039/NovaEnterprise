"""Vector stores preserve tenant scope across memory and Qdrant adapters."""

import sys
from types import SimpleNamespace

import pytest

from backend.app.core.config import Settings
from rag.vector_store import (
    InMemoryVectorStore,
    QdrantVectorStore,
    VectorRecord,
    get_vector_store,
)


def _record(record_id: str, tenant_id: str, vector: list[float], topic: str) -> VectorRecord:
    return VectorRecord(
        id=record_id,
        tenant_id=tenant_id,
        vector=vector,
        content=f"content-{record_id}",
        metadata={"topic": topic},
    )


def test_memory_vector_store_ranks_filters_and_isolates_tenants() -> None:
    store = InMemoryVectorStore("tenant-a")
    store.upsert(
        [
            _record("one", "tenant-a", [1.0, 0.0], "payments"),
            _record("two", "tenant-a", [0.0, 1.0], "identity"),
        ]
    )

    assert [match.id for match in store.search([0.9, 0.1], limit=2)] == ["one", "two"]
    assert [match.id for match in store.search([1.0, 0.0], filters={"topic": "payments"})] == [
        "one"
    ]
    with pytest.raises(ValueError, match="tenant"):
        store.upsert([_record("bad", "tenant-b", [1.0, 0.0], "payments")])


def test_memory_vector_store_validates_dimensions_and_deletes() -> None:
    store = InMemoryVectorStore("tenant-a")
    store.upsert([_record("one", "tenant-a", [1.0, 0.0], "payments")])
    with pytest.raises(ValueError, match="dimension"):
        store.search([1.0])
    assert store.delete(["one"]) == 1
    assert store.search([1.0, 0.0]) == []


class StubQdrantClient:
    def __init__(self) -> None:
        self.upserts: list[dict] = []
        self.queries: list[dict] = []
        self.deletes: list[dict] = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def query_points(self, **kwargs):
        self.queries.append(kwargs)
        point = SimpleNamespace(
            id="one",
            score=0.9,
            payload={
                "record_id": "one",
                "tenant_id": "tenant-a",
                "content": "content-one",
                "topic": "payments",
            },
        )
        return SimpleNamespace(points=[point])

    def delete(self, **kwargs):
        self.deletes.append(kwargs)


class StubQdrantValue:
    def __init__(self, **values):
        self.__dict__.update(values)


class StubQdrantModels:
    PointStruct = StubQdrantValue
    FieldCondition = StubQdrantValue
    MatchValue = StubQdrantValue
    Filter = StubQdrantValue
    PointIdsList = StubQdrantValue


def test_qdrant_adapter_uses_injected_client_and_tenant_filters() -> None:
    client = StubQdrantClient()
    store = QdrantVectorStore("tenant-a", client=client, collection_name="documents")
    store.upsert([_record("one", "tenant-a", [1.0, 0.0], "payments")])
    matches = store.search([1.0, 0.0], filters={"topic": "payments"})
    store.delete(["one"])

    assert matches[0].id == "one"
    assert client.upserts[0]["collection_name"] == "documents"
    assert client.queries[0]["query_filter"]["must"][0]["match"]["value"] == "tenant-a"
    assert client.deletes[0]["points_selector"]


def test_qdrant_factory_uses_typed_sdk_request_shapes_when_available() -> None:
    client = StubQdrantClient()
    store = get_vector_store(
        Settings(vector_store="qdrant"),
        "tenant-a",
        client=client,
        models=StubQdrantModels,
    )
    store.upsert([_record("one", "tenant-a", [1.0, 0.0], "payments")])
    store.search([1.0, 0.0])
    store.delete(["one"])

    assert isinstance(client.upserts[0]["points"][0], StubQdrantValue)
    assert isinstance(client.queries[0]["query_filter"], StubQdrantValue)
    assert isinstance(client.deletes[0]["points_selector"], StubQdrantValue)


def test_vector_factory_defaults_offline_and_requires_qdrant_dependency(monkeypatch) -> None:
    assert isinstance(
        get_vector_store(Settings(vector_store="memory"), "tenant-a"), InMemoryVectorStore
    )
    assert isinstance(
        get_vector_store(Settings(vector_store="qdrant"), "tenant-a", client=StubQdrantClient()),
        QdrantVectorStore,
    )
    monkeypatch.setitem(sys.modules, "qdrant_client", None)
    with pytest.raises(RuntimeError, match="qdrant-client"):
        get_vector_store(Settings(vector_store="qdrant"), "tenant-a")
