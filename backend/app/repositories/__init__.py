"""Tenant-scoped repository interfaces for all relational access."""

from backend.app.repositories.audit import AuditLogRepository
from backend.app.repositories.base import TenantRepository
from backend.app.repositories.documents import DocumentRepository
from backend.app.repositories.enterprise import (
    CustomerRepository,
    DecisionRepository,
    EmployeeRepository,
    IncidentRepository,
    OrganizationalMemoryRepository,
    ProjectRepository,
    ServiceRepository,
    TeamRepository,
    TicketRepository,
)
from backend.app.repositories.research import ResearchSessionRepository, WorkflowEventRepository

__all__ = [
    "AuditLogRepository",
    "CustomerRepository",
    "DecisionRepository",
    "DocumentRepository",
    "EmployeeRepository",
    "IncidentRepository",
    "OrganizationalMemoryRepository",
    "ProjectRepository",
    "ResearchSessionRepository",
    "ServiceRepository",
    "TeamRepository",
    "TenantRepository",
    "TicketRepository",
    "WorkflowEventRepository",
]
