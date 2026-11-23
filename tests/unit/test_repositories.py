"""Repositories enforce tenant scope and keep SQL out of services."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from backend.app.models import (
    AuditLog,
    Customer,
    Employee,
    OrganizationalMemory,
    Project,
    ResearchSession,
    Ticket,
    WorkflowEvent,
)
from backend.app.repositories.audit import AuditLogRepository
from backend.app.repositories.base import TenantRepository
from backend.app.repositories.enterprise import (
    EmployeeRepository,
    OrganizationalMemoryRepository,
    ProjectRepository,
    TicketRepository,
)
from backend.app.repositories.research import ResearchSessionRepository, WorkflowEventRepository
from backend.app.schemas.common import CustomerTier, ResearchStatus


def test_generic_repository_isolates_tenants(db_session: Session) -> None:
    tenant_a = TenantRepository(db_session, Customer, "tenant-a")
    tenant_b = TenantRepository(db_session, Customer, "tenant-b")
    tenant_a.add(Customer(id="customer-a", tenant_id="tenant-a", name="A", tier=CustomerTier.SMB))
    tenant_b.add(Customer(id="customer-b", tenant_id="tenant-b", name="B", tier=CustomerTier.SMB))
    db_session.commit()

    assert [customer.id for customer in tenant_a.list()] == ["customer-a"]
    assert tenant_a.get("customer-b") is None
    with pytest.raises(ValueError):
        tenant_a.add(Customer(id="wrong", tenant_id="tenant-b", name="X", tier=CustomerTier.SMB))


def test_research_events_and_audit_queries(db_session: Session) -> None:
    sessions = ResearchSessionRepository(db_session, "tenant-a")
    events = WorkflowEventRepository(db_session, "tenant-a")
    audits = AuditLogRepository(db_session, "tenant-a")
    sessions.add(
        ResearchSession(
            id="session-1",
            tenant_id="tenant-a",
            user_id="user-1",
            question="Question?",
            status=ResearchStatus.RUNNING,
            state_json={},
        )
    )
    now = datetime.now(UTC)
    events.add(
        WorkflowEvent(
            id="event-1",
            tenant_id="tenant-a",
            session_id="session-1",
            sequence=events.next_sequence("session-1"),
            event_type="node_completed",
            name="analyze_query",
            status="completed",
            metadata_json={},
            created_at=now,
        )
    )
    audits.add(
        AuditLog(
            id="audit-1",
            tenant_id="tenant-a",
            actor_id="user-1",
            action="research.created",
            resource_type="research_session",
            resource_id="session-1",
            details_json={},
            created_at=now,
        )
    )
    db_session.commit()

    assert events.next_sequence("session-1") == 2
    assert [event.id for event in events.for_session("session-1")] == ["event-1"]
    assert [record.id for record in audits.for_resource("research_session", "session-1")] == [
        "audit-1"
    ]


@pytest.mark.parametrize(
    ("repository_type", "model_type"),
    [
        (EmployeeRepository, Employee),
        (ProjectRepository, Project),
        (TicketRepository, Ticket),
        (OrganizationalMemoryRepository, OrganizationalMemory),
    ],
)
def test_every_enterprise_record_has_a_tenant_repository(
    db_session: Session, repository_type: type, model_type: type
) -> None:
    repository = repository_type(db_session, "tenant-a")
    assert repository.model is model_type
    assert repository.tenant_id == "tenant-a"
