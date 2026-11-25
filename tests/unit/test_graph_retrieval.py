"""Typed graph seeding and safe retrieval tests."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from backend.app.services.seed import seed_database
from rag.graph_retrieval import (
    GraphDirection,
    GraphEntityLabel,
    GraphRelationship,
    GraphRetrievalService,
    GraphSeedError,
    seed_enterprise_graph,
)
from rag.graph_store import GraphNode, InMemoryGraphStore


def _seed(db_session: Session):
    seed_database(db_session)
    store = InMemoryGraphStore("novaenterprise-demo")
    result = seed_enterprise_graph(db_session, tenant_id="novaenterprise-demo", store=store)
    return store, result


def test_seed_mapping_is_typed_idempotent_and_tenant_scoped(db_session: Session) -> None:
    store, first = _seed(db_session)
    second = seed_enterprise_graph(db_session, tenant_id="novaenterprise-demo", store=store)
    other_store = InMemoryGraphStore("tenant-other")
    other = seed_enterprise_graph(db_session, tenant_id="tenant-other", store=other_store)

    assert first == second
    assert first.node_count == 44
    assert first.edge_count > 40
    assert {node.label for node in store._nodes.values()} == {
        label.value for label in GraphEntityLabel
    }
    assert all(node.tenant_id == "novaenterprise-demo" for node in store._nodes.values())
    assert len(store._nodes) == first.node_count
    assert len(store._edges) == first.edge_count
    assert other.node_count == 0
    assert other.edge_count == 0
    assert other_store._nodes == {}
    assert other_store._edges == {}


def test_seed_mapping_rejects_missing_association_reference(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_database(db_session)
    original_execute = db_session.execute

    def execute_with_missing_reference(statement, *args, **kwargs):
        if "FROM incident_customers" in str(statement):
            return [("inc-2031", "missing-customer")]
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db_session, "execute", execute_with_missing_reference)

    with pytest.raises(GraphSeedError, match="missing customer"):
        seed_enterprise_graph(
            db_session,
            tenant_id="novaenterprise-demo",
            store=InMemoryGraphStore("novaenterprise-demo"),
        )


def test_customer_impact_is_bounded_ordered_and_stable(db_session: Session) -> None:
    store, _ = _seed(db_session)
    service = GraphRetrievalService(store=store, tenant_id="novaenterprise-demo")

    first = service.impacted_customers(
        service_id="svc-payments",
        started_at=datetime(2026, 7, 14, 9, 20, tzinfo=UTC),
        ended_at=datetime(2026, 9, 21, 18, 0, tzinfo=UTC),
        limit=10,
    )
    second = service.impacted_customers(
        service_id="svc-payments",
        started_at=datetime(2026, 7, 14, 9, 20, tzinfo=UTC),
        ended_at=datetime(2026, 9, 21, 18, 0, tzinfo=UTC),
        limit=10,
    )
    limited = service.impacted_customers(
        service_id="svc-payments",
        started_at=datetime(2026, 7, 14, 9, 20, tzinfo=UTC),
        ended_at=datetime(2026, 9, 21, 18, 0, tzinfo=UTC),
        limit=2,
    )

    assert first.status == "completed"
    assert [item.source_id for item in first.evidence] == [
        "cust-acme",
        "cust-globex",
        "cust-initech",
        "cust-umbrella",
    ]
    assert [item.id for item in first.evidence] == [item.id for item in second.evidence]
    assert [item.source_id for item in limited.evidence] == ["cust-acme", "cust-globex"]
    assert "$service_id" in first.query.cypher
    assert "svc-payments" not in first.query.cypher
    assert first.query.parameters["service_id"] == "svc-payments"


def test_ownership_and_expansion_expose_parameterized_cypher(db_session: Session) -> None:
    store, _ = _seed(db_session)
    service = GraphRetrievalService(store=store, tenant_id="novaenterprise-demo")

    owner = service.owning_team(service_id="svc-payments")
    expanded = service.expand_node(
        node_id="svc-payments",
        relationship=GraphRelationship.OWNED_BY,
        direction=GraphDirection.OUTGOING,
        limit=5,
    )

    assert [item.source_id for item in owner.evidence] == ["team-payments"]
    assert [item.source_id for item in expanded.evidence] == ["team-payments"]
    assert "$node_id" in expanded.query.cypher
    assert "svc-payments" not in expanded.query.cypher
    assert "OWNED_BY" in expanded.query.cypher


def test_empty_hostile_parameter_and_invalid_ranges_are_safe(db_session: Session) -> None:
    store, _ = _seed(db_session)
    service = GraphRetrievalService(store=store, tenant_id="novaenterprise-demo")
    hostile = "svc-payments' MATCH (n) DETACH DELETE n //"

    result = service.owning_team(service_id=hostile)

    assert result.evidence == ()
    assert hostile not in result.query.cypher
    with pytest.raises(ValueError, match="ended_at"):
        service.impacted_customers(
            service_id="svc-payments",
            started_at=datetime(2026, 7, 1, tzinfo=UTC),
            ended_at=datetime(2026, 7, 1, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="timezone"):
        service.impacted_customers(
            service_id="svc-payments",
            started_at=datetime(2026, 7, 1),
            ended_at=datetime(2026, 8, 1),
        )
    with pytest.raises(ValueError, match="limit"):
        service.expand_node(
            node_id="svc-payments",
            relationship=GraphRelationship.OWNED_BY,
            direction=GraphDirection.OUTGOING,
            limit=0,
        )
    with pytest.raises(ValueError, match="relationship"):
        service.expand_node(
            node_id="svc-payments",
            relationship="MATCH_DELETE",  # type: ignore[arg-type]
            direction=GraphDirection.OUTGOING,
        )
    with pytest.raises(ValueError, match="direction"):
        service.expand_node(
            node_id="svc-payments",
            relationship=GraphRelationship.OWNED_BY,
            direction="sideways",  # type: ignore[arg-type]
        )


class _FailingStore:
    def neighbors(self, *_args, **_kwargs):
        raise RuntimeError("password=hunter2")


def test_graph_failure_degrades_and_redacts_secrets() -> None:
    result = GraphRetrievalService(store=_FailingStore(), tenant_id="tenant-a").owning_team(
        service_id="svc-payments"
    )

    assert result.status == "degraded"
    assert result.evidence == ()
    assert "hunter2" not in result.errors[0]
    assert "[REDACTED]" in result.errors[0]


class _CrossTenantStore:
    def neighbors(self, *_args, **_kwargs):
        return [
            GraphNode(
                id="team-other",
                tenant_id="tenant-other",
                label="Team",
                properties={"name": "Other"},
            )
        ]


def test_graph_result_rejects_cross_tenant_nodes() -> None:
    result = GraphRetrievalService(store=_CrossTenantStore(), tenant_id="tenant-a").owning_team(
        service_id="svc-payments"
    )

    assert result.status == "degraded"
    assert result.evidence == ()
    assert "cross-tenant" in result.errors[0]
