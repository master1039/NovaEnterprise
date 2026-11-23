"""Create the frozen Phase 2 relational schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in _tables():
        table.create(op.get_bind())


def downgrade() -> None:
    for table in reversed(_tables()):
        table.drop(op.get_bind())


def _tenant_timestamps() -> tuple[sa.Column, ...]:
    return (
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def _tenant_only() -> tuple[sa.Column, ...]:
    return (sa.Column("tenant_id", sa.String(64), nullable=False, index=True),)


def _tables() -> Sequence[sa.Table]:
    """Return a migration-local schema snapshot independent of application models."""

    metadata = sa.MetaData()
    teams = sa.Table(
        "teams",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        *_tenant_timestamps(),
    )
    customers = sa.Table(
        "customers",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("tier", sa.String(10), nullable=False),
        *_tenant_timestamps(),
    )
    documents = sa.Table(
        "documents",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("is_untrusted", sa.Boolean(), nullable=False),
        *_tenant_timestamps(),
    )
    organizational_memory = sa.Table(
        "organizational_memory",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(240), nullable=False),
        *_tenant_timestamps(),
    )
    research_sessions = sa.Table(
        "research_sessions",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("answer", sa.Text()),
        *_tenant_timestamps(),
    )
    audit_logs = sa.Table(
        "audit_logs",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("actor_id", sa.String(64), index=True),
        sa.Column("action", sa.String(120), nullable=False, index=True),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(96)),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_tenant_only(),
    )
    employees = sa.Table(
        "employees",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("team_id", sa.ForeignKey("teams.id"), nullable=False, index=True),
        *_tenant_timestamps(),
        sa.UniqueConstraint("email", name="uq_employees_email"),
    )
    services = sa.Table(
        "services",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_team_id", sa.ForeignKey("teams.id"), nullable=False, index=True),
        *_tenant_timestamps(),
    )
    projects = sa.Table(
        "projects",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_team_id", sa.ForeignKey("teams.id"), nullable=False, index=True),
        sa.Column("status", sa.String(9), nullable=False),
        *_tenant_timestamps(),
    )
    document_chunks = sa.Table(
        "document_chunks",
        metadata,
        sa.Column("id", sa.String(96), primary_key=True),
        sa.Column(
            "document_id",
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        *_tenant_timestamps(),
    )
    workflow_events = sa.Table(
        "workflow_events",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "session_id",
            sa.ForeignKey("research_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("duration_ms", sa.Float()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_tenant_only(),
    )
    incidents = sa.Table(
        "incidents",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("service_id", sa.ForeignKey("services.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(4), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *_tenant_timestamps(),
    )
    tickets = sa.Table(
        "tickets",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.ForeignKey("customers.id"), index=True),
        sa.Column("project_id", sa.ForeignKey("projects.id"), index=True),
        sa.Column("assigned_team_id", sa.ForeignKey("teams.id"), index=True),
        sa.Column("status", sa.String(11), nullable=False),
        sa.Column("priority", sa.String(6), nullable=False),
        *_tenant_timestamps(),
    )
    incident_customers = sa.Table(
        "incident_customers",
        metadata,
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column(
            "incident_id",
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "customer_id",
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    decisions = sa.Table(
        "decisions",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.ForeignKey("incidents.id"), index=True),
        sa.Column("service_id", sa.ForeignKey("services.id"), index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, index=True),
        *_tenant_timestamps(),
    )
    return (
        teams,
        customers,
        documents,
        organizational_memory,
        research_sessions,
        audit_logs,
        employees,
        services,
        projects,
        document_chunks,
        workflow_events,
        incidents,
        tickets,
        incident_customers,
        decisions,
    )
