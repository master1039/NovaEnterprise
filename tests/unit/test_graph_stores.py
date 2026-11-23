"""Graph stores use typed tenant-scoped operations and injected drivers."""

import sys
from types import ModuleType

import pytest

from backend.app.core.config import Settings
from rag.graph_store import (
    GraphEdge,
    GraphNode,
    InMemoryGraphStore,
    Neo4jGraphStore,
    get_graph_store,
)


def test_memory_graph_store_traverses_direction_and_tenant_scope() -> None:
    store = InMemoryGraphStore("tenant-a")
    store.upsert_nodes(
        [
            GraphNode("incident-1", "tenant-a", "Incident", {"title": "Outage"}),
            GraphNode("customer-1", "tenant-a", "Customer", {"name": "Acme"}),
        ]
    )
    store.upsert_edges([GraphEdge("impact-1", "tenant-a", "incident-1", "customer-1", "IMPACTED")])

    assert [node.id for node in store.neighbors("incident-1", relationship="IMPACTED")] == [
        "customer-1"
    ]
    assert store.neighbors("customer-1", direction="outgoing") == []
    assert [node.id for node in store.neighbors("customer-1", direction="incoming")] == [
        "incident-1"
    ]
    with pytest.raises(ValueError, match="tenant"):
        store.upsert_nodes([GraphNode("bad", "tenant-b", "Customer", {})])


def test_memory_graph_store_rejects_edges_with_missing_nodes() -> None:
    store = InMemoryGraphStore("tenant-a")
    with pytest.raises(ValueError, match="nodes"):
        store.upsert_edges([GraphEdge("edge", "tenant-a", "missing", "also-missing", "LINKS")])


class StubNeo4jDriver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute_query(self, query, *, parameters_, database_):
        self.calls.append((query, parameters_))
        if "RETURN target" in query:
            return (
                [
                    {
                        "target": {"id": "customer-1", "name": "Acme", "tenant_id": "tenant-a"},
                        "labels": ["Customer"],
                    }
                ],
                None,
                None,
            )
        return ([], None, None)


def test_neo4j_adapter_parameterizes_tenant_and_values() -> None:
    driver = StubNeo4jDriver()
    store = Neo4jGraphStore("tenant-a", driver=driver, database="neo4j")
    store.upsert_nodes([GraphNode("incident-1", "tenant-a", "Incident", {"title": "Outage"})])
    neighbors = store.neighbors("incident-1", relationship="IMPACTED")

    assert neighbors[0].id == "customer-1"
    assert all(call[1]["tenant_id"] == "tenant-a" for call in driver.calls)
    assert "$properties" in driver.calls[0][0]

    with pytest.raises(ValueError, match="reserved"):
        store.upsert_nodes([GraphNode("bad", "tenant-a", "Customer", {"tenant_id": "tenant-b"})])


def test_graph_factory_defaults_offline_and_requires_neo4j_dependency(monkeypatch) -> None:
    assert isinstance(
        get_graph_store(Settings(graph_store="memory"), "tenant-a"), InMemoryGraphStore
    )
    assert isinstance(
        get_graph_store(Settings(graph_store="neo4j"), "tenant-a", driver=StubNeo4jDriver()),
        Neo4jGraphStore,
    )
    monkeypatch.setitem(sys.modules, "neo4j", None)
    with pytest.raises(RuntimeError, match="neo4j"):
        get_graph_store(Settings(graph_store="neo4j"), "tenant-a")


def test_graph_factory_passes_configured_authentication(monkeypatch) -> None:
    calls: list[tuple[str, tuple[str, str] | None]] = []

    class StubGraphDatabase:
        @staticmethod
        def driver(uri, *, auth=None):
            calls.append((uri, auth))
            return StubNeo4jDriver()

    module = ModuleType("neo4j")
    module.GraphDatabase = StubGraphDatabase
    monkeypatch.setitem(sys.modules, "neo4j", module)

    store = get_graph_store(
        Settings(
            graph_store="neo4j",
            neo4j_username="neo4j",
            neo4j_password="secret",
        ),
        "tenant-a",
    )

    assert isinstance(store, Neo4jGraphStore)
    assert calls == [("bolt://localhost:7687", ("neo4j", "secret"))]
