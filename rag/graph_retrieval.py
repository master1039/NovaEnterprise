"""Tenant-scoped enterprise graph seeding and typed read-only traversals."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.guardrails import redact_secrets
from backend.app.models import Customer, Decision, Incident, Service, Team, incident_customers
from backend.app.schemas.common import Evidence, EvidenceSourceType
from rag.graph_store import GraphEdge, GraphNode, GraphStore

MAX_GRAPH_RESULTS = 100
GraphStatus = Literal["completed", "degraded"]


class GraphEntityLabel(StrEnum):
    TEAM = "Team"
    SERVICE = "Service"
    CUSTOMER = "Customer"
    INCIDENT = "Incident"
    DECISION = "Decision"


class GraphRelationship(StrEnum):
    OWNED_BY = "OWNED_BY"
    AFFECTED = "AFFECTED"
    IMPACTED = "IMPACTED"
    ADDRESSES = "ADDRESSES"
    RELATES_TO = "RELATES_TO"


class GraphDirection(StrEnum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


class GraphSeedError(ValueError):
    """Raised when relational data cannot form a referentially valid graph."""


@dataclass(frozen=True)
class GraphSeedResult:
    node_count: int
    edge_count: int


@dataclass(frozen=True)
class GraphQuery:
    name: str
    cypher: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class GraphRetrievalResult:
    status: GraphStatus
    query: GraphQuery
    evidence: tuple[Evidence, ...]
    errors: tuple[str, ...] = ()


def _edge_id(relationship: GraphRelationship, source_id: str, target_id: str) -> str:
    digest = hashlib.sha256(f"{relationship.value}\0{source_id}\0{target_id}".encode()).hexdigest()[
        :24
    ]
    return f"edge-{digest}"


def _safe_properties(**values: Any) -> dict[str, Any]:
    return {
        key: redact_secrets(value) if isinstance(value, str) else value
        for key, value in values.items()
        if value is not None
    }


def seed_enterprise_graph(
    session: Session,
    *,
    tenant_id: str,
    store: GraphStore,
) -> GraphSeedResult:
    """Map tenant-owned relational records to deterministic typed graph records."""

    if not tenant_id.strip():
        raise ValueError("tenant_id must not be blank")
    teams = list(session.scalars(select(Team).where(Team.tenant_id == tenant_id).order_by(Team.id)))
    services = list(
        session.scalars(select(Service).where(Service.tenant_id == tenant_id).order_by(Service.id))
    )
    customers = list(
        session.scalars(
            select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.id)
        )
    )
    incidents = list(
        session.scalars(
            select(Incident).where(Incident.tenant_id == tenant_id).order_by(Incident.id)
        )
    )
    decisions = list(
        session.scalars(
            select(Decision).where(Decision.tenant_id == tenant_id).order_by(Decision.id)
        )
    )
    impact_rows = list(
        session.execute(
            select(
                incident_customers.c.incident_id,
                incident_customers.c.customer_id,
            )
            .where(incident_customers.c.tenant_id == tenant_id)
            .order_by(incident_customers.c.incident_id, incident_customers.c.customer_id)
        )
    )

    team_ids = {item.id for item in teams}
    service_ids = {item.id for item in services}
    customer_ids = {item.id for item in customers}
    incident_ids = {item.id for item in incidents}
    for service in services:
        if service.owner_team_id not in team_ids:
            raise GraphSeedError(f"service {service.id} references a missing team")
    for incident in incidents:
        if incident.service_id not in service_ids:
            raise GraphSeedError(f"incident {incident.id} references a missing service")
    for incident_id, customer_id in impact_rows:
        if incident_id not in incident_ids:
            raise GraphSeedError(f"impact references a missing incident: {incident_id}")
        if customer_id not in customer_ids:
            raise GraphSeedError(f"impact references a missing customer: {customer_id}")
    for decision in decisions:
        if decision.incident_id and decision.incident_id not in incident_ids:
            raise GraphSeedError(f"decision {decision.id} references a missing incident")
        if decision.service_id and decision.service_id not in service_ids:
            raise GraphSeedError(f"decision {decision.id} references a missing service")

    nodes = [
        *[
            GraphNode(
                id=item.id,
                tenant_id=tenant_id,
                label=GraphEntityLabel.TEAM.value,
                properties=_safe_properties(name=item.name, description=item.description),
            )
            for item in teams
        ],
        *[
            GraphNode(
                id=item.id,
                tenant_id=tenant_id,
                label=GraphEntityLabel.SERVICE.value,
                properties=_safe_properties(name=item.name, description=item.description),
            )
            for item in services
        ],
        *[
            GraphNode(
                id=item.id,
                tenant_id=tenant_id,
                label=GraphEntityLabel.CUSTOMER.value,
                properties=_safe_properties(name=item.name, tier=item.tier.value),
            )
            for item in customers
        ],
        *[
            GraphNode(
                id=item.id,
                tenant_id=tenant_id,
                label=GraphEntityLabel.INCIDENT.value,
                properties=_safe_properties(
                    title=item.title,
                    severity=item.severity.value,
                    status=item.status.value,
                    started_at=item.started_at.isoformat(),
                    resolved_at=item.resolved_at.isoformat() if item.resolved_at else None,
                ),
            )
            for item in incidents
        ],
        *[
            GraphNode(
                id=item.id,
                tenant_id=tenant_id,
                label=GraphEntityLabel.DECISION.value,
                properties=_safe_properties(
                    title=item.title,
                    status=item.status.value,
                    decided_at=item.decided_at.isoformat(),
                ),
            )
            for item in decisions
        ],
    ]
    edges: list[GraphEdge] = []

    def add_edge(source_id: str, target_id: str, relationship: GraphRelationship) -> None:
        edges.append(
            GraphEdge(
                id=_edge_id(relationship, source_id, target_id),
                tenant_id=tenant_id,
                source_id=source_id,
                target_id=target_id,
                relationship=relationship.value,
            )
        )

    for service in services:
        add_edge(service.id, service.owner_team_id, GraphRelationship.OWNED_BY)
    for incident in incidents:
        add_edge(incident.id, incident.service_id, GraphRelationship.AFFECTED)
    for incident_id, customer_id in impact_rows:
        add_edge(incident_id, customer_id, GraphRelationship.IMPACTED)
    for decision in decisions:
        if decision.incident_id:
            add_edge(decision.id, decision.incident_id, GraphRelationship.ADDRESSES)
        if decision.service_id:
            add_edge(decision.id, decision.service_id, GraphRelationship.RELATES_TO)

    store.upsert_nodes(nodes)
    store.upsert_edges(edges)
    return GraphSeedResult(node_count=len(nodes), edge_count=len(edges))


class GraphRetrievalService:
    def __init__(self, *, store: GraphStore, tenant_id: str) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id must not be blank")
        self.store = store
        self.tenant_id = tenant_id

    def impacted_customers(
        self,
        *,
        service_id: str,
        started_at: datetime,
        ended_at: datetime,
        limit: int = 25,
    ) -> GraphRetrievalResult:
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            raise ValueError("started_at must include timezone information")
        if ended_at.tzinfo is None or ended_at.utcoffset() is None:
            raise ValueError("ended_at must include timezone information")
        if ended_at <= started_at:
            raise ValueError("ended_at must be later than started_at")
        _validate_limit(limit)
        query = GraphQuery(
            name="customers_impacted_by_service",
            cypher=(
                "MATCH (service:Service {id: $service_id, tenant_id: $tenant_id})"
                "<-[:AFFECTED {tenant_id: $tenant_id}]-(incident:Incident "
                "{tenant_id: $tenant_id})-[:IMPACTED {tenant_id: $tenant_id}]->"
                "(customer:Customer {tenant_id: $tenant_id}) "
                "WHERE incident.started_at >= $started_at AND incident.started_at < $ended_at "
                "RETURN DISTINCT customer ORDER BY customer.id LIMIT $limit"
            ),
            parameters={
                "service_id": service_id,
                "tenant_id": self.tenant_id,
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "limit": limit,
            },
        )

        def retrieve() -> list[tuple[GraphNode, dict[str, Any]]]:
            incidents = self.store.neighbors(
                service_id,
                relationship=GraphRelationship.AFFECTED.value,
                direction=GraphDirection.INCOMING.value,
            )
            customer_incidents: dict[str, tuple[GraphNode, list[str]]] = {}
            for incident in incidents:
                if incident.label != GraphEntityLabel.INCIDENT.value:
                    continue
                occurred = datetime.fromisoformat(str(incident.properties["started_at"]))
                if occurred.tzinfo is None:
                    occurred = occurred.replace(tzinfo=UTC)
                if not started_at <= occurred < ended_at:
                    continue
                customers = self.store.neighbors(
                    incident.id,
                    relationship=GraphRelationship.IMPACTED.value,
                    direction=GraphDirection.OUTGOING.value,
                )
                for customer in customers:
                    if customer.label != GraphEntityLabel.CUSTOMER.value:
                        continue
                    existing = customer_incidents.setdefault(customer.id, (customer, []))
                    existing[1].append(incident.id)
            return [
                (node, {"incident_ids": sorted(incident_ids), "service_id": service_id})
                for node, incident_ids in sorted(
                    customer_incidents.values(), key=lambda value: value[0].id
                )
            ][:limit]

        return self._run(query, retrieve)

    def owning_team(self, *, service_id: str) -> GraphRetrievalResult:
        query = GraphQuery(
            name="team_owning_service",
            cypher=(
                "MATCH (service:Service {id: $service_id, tenant_id: $tenant_id})"
                "-[:OWNED_BY {tenant_id: $tenant_id}]->"
                "(team:Team {tenant_id: $tenant_id}) "
                "RETURN team ORDER BY team.id LIMIT 1"
            ),
            parameters={"service_id": service_id, "tenant_id": self.tenant_id},
        )

        def retrieve() -> list[tuple[GraphNode, dict[str, Any]]]:
            nodes = self.store.neighbors(
                service_id,
                relationship=GraphRelationship.OWNED_BY.value,
                direction=GraphDirection.OUTGOING.value,
            )
            return [
                (node, {"service_id": service_id})
                for node in nodes
                if node.label == GraphEntityLabel.TEAM.value
            ][:1]

        return self._run(query, retrieve)

    def expand_node(
        self,
        *,
        node_id: str,
        relationship: GraphRelationship,
        direction: GraphDirection,
        limit: int = 25,
    ) -> GraphRetrievalResult:
        if not isinstance(relationship, GraphRelationship):
            raise ValueError("relationship must be an allowlisted GraphRelationship")
        if not isinstance(direction, GraphDirection):
            raise ValueError("direction must be an allowlisted GraphDirection")
        _validate_limit(limit)
        arrows = {
            GraphDirection.OUTGOING: ("-", "->"),
            GraphDirection.INCOMING: ("<-", "-"),
            GraphDirection.BOTH: ("-", "-"),
        }[direction]
        cypher = (
            "MATCH (source {id: $node_id, tenant_id: $tenant_id})"
            f"{arrows[0]}[edge:{relationship.value} "
            "{tenant_id: $tenant_id}]"
            f"{arrows[1]}(target {{tenant_id: $tenant_id}}) "
            "RETURN target, labels(target) AS labels ORDER BY target.id LIMIT $limit"
        )
        query = GraphQuery(
            name="expand_node",
            cypher=cypher,
            parameters={"node_id": node_id, "tenant_id": self.tenant_id, "limit": limit},
        )

        def retrieve() -> list[tuple[GraphNode, dict[str, Any]]]:
            nodes = self.store.neighbors(
                node_id,
                relationship=relationship.value,
                direction=direction.value,
            )
            return [
                (
                    node,
                    {"source_node_id": node_id, "relationship": relationship.value},
                )
                for node in nodes[:limit]
            ]

        return self._run(query, retrieve)

    def _run(
        self,
        query: GraphQuery,
        retrieve: Callable[[], list[tuple[GraphNode, dict[str, Any]]]],
    ) -> GraphRetrievalResult:
        try:
            rows = retrieve()
            if any(node.tenant_id != self.tenant_id for node, _metadata in rows):
                raise ValueError("graph traversal returned a cross-tenant node")
            evidence = tuple(self._evidence(query, node, metadata) for node, metadata in rows)
            return GraphRetrievalResult(status="completed", query=query, evidence=evidence)
        except Exception as exc:
            return GraphRetrievalResult(
                status="degraded",
                query=query,
                evidence=(),
                errors=(f"graph: {redact_secrets(str(exc))}",),
            )

    def _evidence(self, query: GraphQuery, node: GraphNode, metadata: dict[str, Any]) -> Evidence:
        digest = hashlib.sha256(f"{self.tenant_id}\0{query.name}\0{node.id}".encode()).hexdigest()[
            :24
        ]
        name = redact_secrets(
            str(node.properties.get("name") or node.properties.get("title") or node.id)
        )
        return Evidence(
            id=f"evidence-graph-{digest}",
            source_type=EvidenceSourceType.GRAPH,
            source_id=node.id,
            locator=f"graph:{node.label}:{node.id}",
            title=name,
            content=f"{node.label} {node.id}: {name}",
            query=query.cypher,
            metadata={"label": node.label, **metadata},
        )


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= MAX_GRAPH_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_GRAPH_RESULTS}")


__all__ = [
    "GraphDirection",
    "GraphEntityLabel",
    "GraphQuery",
    "GraphRelationship",
    "GraphRetrievalResult",
    "GraphRetrievalService",
    "GraphSeedError",
    "GraphSeedResult",
    "MAX_GRAPH_RESULTS",
    "seed_enterprise_graph",
]
