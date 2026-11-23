"""Pydantic contracts for deterministic seed data and later API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import (
    CustomerTier,
    DecisionStatus,
    IncidentSeverity,
    IncidentStatus,
    ProjectStatus,
    ResearchStatus,
    TicketPriority,
    TicketStatus,
)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class TeamSeed(DomainModel):
    id: str
    name: str
    description: str = ""


class EmployeeSeed(DomainModel):
    id: str
    name: str
    title: str
    email: str
    team_id: str


class ServiceSeed(DomainModel):
    id: str
    name: str
    description: str = ""
    owner_team_id: str


class CustomerSeed(DomainModel):
    id: str
    name: str
    tier: CustomerTier


class IncidentSeed(DomainModel):
    id: str
    service_id: str
    title: str
    summary: str
    root_cause: str
    severity: IncidentSeverity
    status: IncidentStatus
    started_at: datetime
    resolved_at: datetime | None = None
    impacted_customer_ids: list[str] = Field(default_factory=list)


class DecisionSeed(DomainModel):
    id: str
    incident_id: str | None = None
    service_id: str | None = None
    title: str
    summary: str
    status: DecisionStatus
    decided_at: datetime


class ProjectSeed(DomainModel):
    id: str
    name: str
    description: str = ""
    owner_team_id: str
    status: ProjectStatus


class TicketSeed(DomainModel):
    id: str
    title: str
    description: str = ""
    customer_id: str | None = None
    project_id: str | None = None
    assigned_team_id: str | None = None
    status: TicketStatus
    priority: TicketPriority


class OrganizationalMemorySeed(DomainModel):
    id: str
    key: str
    value: str
    source: str


class TeamRead(TeamSeed):
    tenant_id: str


class EmployeeRead(EmployeeSeed):
    tenant_id: str


class ServiceRead(ServiceSeed):
    tenant_id: str


class CustomerRead(CustomerSeed):
    tenant_id: str


class IncidentRead(IncidentSeed):
    tenant_id: str


class DecisionRead(DecisionSeed):
    tenant_id: str


class ProjectRead(ProjectSeed):
    tenant_id: str


class TicketRead(TicketSeed):
    tenant_id: str


class OrganizationalMemoryRead(OrganizationalMemorySeed):
    tenant_id: str


class DocumentRead(DomainModel):
    id: str
    tenant_id: str
    title: str
    source_path: str
    document_type: str
    content_sha256: str
    is_untrusted: bool
    created_at: datetime
    updated_at: datetime


class ResearchSessionRead(DomainModel):
    id: str
    tenant_id: str
    user_id: str
    question: str
    status: ResearchStatus
    state_json: dict
    answer: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowEventRead(DomainModel):
    id: str
    tenant_id: str
    session_id: str
    sequence: int
    event_type: str
    name: str
    status: str
    duration_ms: float | None = None
    metadata_json: dict
    created_at: datetime


class AuditLogRead(DomainModel):
    id: str
    tenant_id: str
    actor_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details_json: dict
    created_at: datetime
