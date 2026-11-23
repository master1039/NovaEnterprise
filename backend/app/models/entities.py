"""Relational entities shared by later retrieval and workflow phases."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Table,
    Text,
    and_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TenantMixin, TimestampMixin
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

incident_customers = Table(
    "incident_customers",
    Base.metadata,
    Column("tenant_id", String(64), nullable=False, index=True),
    Column("incident_id", ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column("customer_id", ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True),
)


class Team(TenantMixin, TimestampMixin, Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Employee(TenantMixin, TimestampMixin, Base):
    __tablename__ = "employees"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    team: Mapped[Team] = relationship()


class Service(TenantMixin, TimestampMixin, Base):
    __tablename__ = "services"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    owner_team: Mapped[Team] = relationship()


class Customer(TenantMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tier: Mapped[CustomerTier] = mapped_column(Enum(CustomerTier, native_enum=False))


class Incident(TenantMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity, native_enum=False))
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus, native_enum=False))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    service: Mapped[Service] = relationship()
    impacted_customers: Mapped[list[Customer]] = relationship(
        secondary=incident_customers,
        primaryjoin=lambda: and_(
            Incident.id == incident_customers.c.incident_id,
            Incident.tenant_id == incident_customers.c.tenant_id,
        ),
        secondaryjoin=lambda: and_(
            Customer.id == incident_customers.c.customer_id,
            Customer.tenant_id == incident_customers.c.tenant_id,
        ),
        viewonly=True,
    )


class Decision(TenantMixin, TimestampMixin, Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), index=True)
    service_id: Mapped[str | None] = mapped_column(ForeignKey("services.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DecisionStatus] = mapped_column(Enum(DecisionStatus, native_enum=False))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Project(TenantMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus, native_enum=False))


class Ticket(TenantMixin, TimestampMixin, Base):
    __tablename__ = "tickets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    assigned_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), index=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus, native_enum=False))
    priority: Mapped[TicketPriority] = mapped_column(Enum(TicketPriority, native_enum=False))


class Document(TenantMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_untrusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DocumentChunk(TenantMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class OrganizationalMemory(TenantMixin, TimestampMixin, Base):
    __tablename__ = "organizational_memory"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    key: Mapped[str] = mapped_column(String(160), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(240), nullable=False)


class ResearchSession(TenantMixin, TimestampMixin, Base):
    __tablename__ = "research_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ResearchStatus] = mapped_column(Enum(ResearchStatus, native_enum=False))
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)


class WorkflowEvent(TenantMixin, Base):
    __tablename__ = "workflow_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(TenantMixin, Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(96))
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
