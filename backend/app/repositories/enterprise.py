"""Repositories for enterprise records and canonical incident lookups."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import (
    Customer,
    Decision,
    Employee,
    Incident,
    OrganizationalMemory,
    Project,
    Service,
    Team,
    Ticket,
)
from backend.app.repositories.base import TenantRepository


class TeamRepository(TenantRepository[Team]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Team, tenant_id)


class EmployeeRepository(TenantRepository[Employee]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Employee, tenant_id)


class ServiceRepository(TenantRepository[Service]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Service, tenant_id)

    def by_name(self, name: str) -> Service | None:
        return self.session.scalar(
            select(Service).where(Service.tenant_id == self.tenant_id, Service.name == name)
        )


class CustomerRepository(TenantRepository[Customer]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Customer, tenant_id)


class IncidentRepository(TenantRepository[Incident]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Incident, tenant_id)

    def for_service_between(
        self, service_id: str, started_at: datetime, ended_at: datetime
    ) -> list[Incident]:
        return list(
            self.session.scalars(
                select(Incident)
                .options(selectinload(Incident.impacted_customers))
                .where(
                    Incident.tenant_id == self.tenant_id,
                    Incident.service_id == service_id,
                    Incident.started_at >= started_at,
                    Incident.started_at < ended_at,
                )
                .order_by(Incident.started_at)
            )
        )


class DecisionRepository(TenantRepository[Decision]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Decision, tenant_id)

    def for_service(self, service_id: str) -> list[Decision]:
        return list(
            self.session.scalars(
                select(Decision)
                .where(
                    Decision.tenant_id == self.tenant_id,
                    Decision.service_id == service_id,
                )
                .order_by(Decision.decided_at)
            )
        )


class ProjectRepository(TenantRepository[Project]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Project, tenant_id)


class TicketRepository(TenantRepository[Ticket]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Ticket, tenant_id)


class OrganizationalMemoryRepository(TenantRepository[OrganizationalMemory]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, OrganizationalMemory, tenant_id)
