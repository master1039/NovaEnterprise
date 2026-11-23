"""Typed tenant-scoped graph contract with memory and Neo4j adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

from backend.app.core.config import Settings, get_settings

_SAFE_GRAPH_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
Direction = Literal["outgoing", "incoming", "both"]


@dataclass(frozen=True)
class GraphNode:
    id: str
    tenant_id: str
    label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class GraphEdge:
    id: str
    tenant_id: str
    source_id: str
    target_id: str
    relationship: str
    properties: dict[str, Any] | None = None


@runtime_checkable
class GraphStore(Protocol):
    def upsert_nodes(self, nodes: list[GraphNode]) -> None: ...

    def upsert_edges(self, edges: list[GraphEdge]) -> None: ...

    def neighbors(
        self,
        node_id: str,
        *,
        relationship: str | None = None,
        direction: Direction = "outgoing",
    ) -> list[GraphNode]: ...


class InMemoryGraphStore:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}

    def upsert_nodes(self, nodes: list[GraphNode]) -> None:
        for node in nodes:
            if node.tenant_id != self.tenant_id:
                raise ValueError("node tenant does not match graph store tenant")
            _validate_graph_name(node.label, "label")
            _clean_properties(node.properties)
            self._nodes[node.id] = node

    def upsert_edges(self, edges: list[GraphEdge]) -> None:
        for edge in edges:
            if edge.tenant_id != self.tenant_id:
                raise ValueError("edge tenant does not match graph store tenant")
            if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
                raise ValueError("edge source and target nodes must exist")
            _validate_graph_name(edge.relationship, "relationship")
            _clean_properties(edge.properties or {})
            self._edges[edge.id] = edge

    def neighbors(
        self,
        node_id: str,
        *,
        relationship: str | None = None,
        direction: Direction = "outgoing",
    ) -> list[GraphNode]:
        if direction not in {"outgoing", "incoming", "both"}:
            raise ValueError("direction must be outgoing, incoming, or both")
        if relationship is not None:
            _validate_graph_name(relationship, "relationship")
        neighbor_ids: set[str] = set()
        for edge in self._edges.values():
            if relationship is not None and edge.relationship != relationship:
                continue
            if direction in {"outgoing", "both"} and edge.source_id == node_id:
                neighbor_ids.add(edge.target_id)
            if direction in {"incoming", "both"} and edge.target_id == node_id:
                neighbor_ids.add(edge.source_id)
        return [self._nodes[node] for node in sorted(neighbor_ids)]


class Neo4jGraphStore:
    def __init__(self, tenant_id: str, *, driver: Any, database: str = "neo4j") -> None:
        self.tenant_id = tenant_id
        self.driver = driver
        self.database = database

    def _execute(self, query: str, **parameters: Any):
        return self.driver.execute_query(query, parameters_=parameters, database_=self.database)[0]

    def upsert_nodes(self, nodes: list[GraphNode]) -> None:
        for node in nodes:
            if node.tenant_id != self.tenant_id:
                raise ValueError("node tenant does not match graph store tenant")
            label = _validate_graph_name(node.label, "label")
            query = (
                f"MERGE (node:{label} {{id: $id, tenant_id: $tenant_id}}) SET node += $properties"
            )
            self._execute(
                query,
                id=node.id,
                tenant_id=self.tenant_id,
                properties=_clean_properties(node.properties),
            )

    def upsert_edges(self, edges: list[GraphEdge]) -> None:
        for edge in edges:
            if edge.tenant_id != self.tenant_id:
                raise ValueError("edge tenant does not match graph store tenant")
            relation = _validate_graph_name(edge.relationship, "relationship")
            query = (
                "MATCH (source {id: $source_id, tenant_id: $tenant_id}) "
                "MATCH (target {id: $target_id, tenant_id: $tenant_id}) "
                f"MERGE (source)-[edge:{relation} "
                "{id: $edge_id, tenant_id: $tenant_id}]->(target) "
                "SET edge += $properties"
            )
            self._execute(
                query,
                source_id=edge.source_id,
                target_id=edge.target_id,
                edge_id=edge.id,
                tenant_id=self.tenant_id,
                properties=_clean_properties(edge.properties or {}),
            )

    def neighbors(
        self,
        node_id: str,
        *,
        relationship: str | None = None,
        direction: Direction = "outgoing",
    ) -> list[GraphNode]:
        if direction not in {"outgoing", "incoming", "both"}:
            raise ValueError("direction must be outgoing, incoming, or both")
        relation = f":{_validate_graph_name(relationship, 'relationship')}" if relationship else ""
        arrows = {
            "outgoing": ("-", "->"),
            "incoming": ("<-", "-"),
            "both": ("-", "-"),
        }[direction]
        query = (
            "MATCH (source {id: $node_id, tenant_id: $tenant_id})"
            f"{arrows[0]}[edge{relation}]{arrows[1]}"
            "(target {tenant_id: $tenant_id}) "
            "RETURN target, labels(target) AS labels ORDER BY target.id"
        )
        rows = self._execute(query, node_id=node_id, tenant_id=self.tenant_id)
        nodes = []
        for row in rows:
            values = dict(row["target"])
            target_id = values.pop("id")
            values.pop("tenant_id", None)
            nodes.append(
                GraphNode(
                    id=target_id,
                    tenant_id=self.tenant_id,
                    label=row["labels"][0] if row["labels"] else "Node",
                    properties=values,
                )
            )
        return nodes


def _validate_graph_name(value: str, kind: str) -> str:
    if not _SAFE_GRAPH_NAME.fullmatch(value):
        raise ValueError(f"{kind} must contain only safe graph identifier characters")
    return value


def _clean_properties(properties: dict[str, Any]) -> dict[str, Any]:
    reserved = {"id", "tenant_id"}.intersection(properties)
    if reserved:
        raise ValueError(f"graph properties cannot replace reserved fields: {sorted(reserved)}")
    return dict(properties)


def get_graph_store(
    settings: Settings | None,
    tenant_id: str,
    *,
    driver: Any | None = None,
) -> GraphStore:
    resolved = settings or get_settings()
    if resolved.graph_store == "memory":
        return InMemoryGraphStore(tenant_id)
    if driver is None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("Neo4j requires the optional 'neo4j' package") from exc
        auth = (
            (resolved.neo4j_username, resolved.neo4j_password)
            if resolved.neo4j_username and resolved.neo4j_password
            else None
        )
        driver = GraphDatabase.driver(resolved.neo4j_uri, auth=auth)
    return Neo4jGraphStore(tenant_id, driver=driver, database=resolved.neo4j_database)
