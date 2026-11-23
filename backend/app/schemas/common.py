"""Shared enums and normalized evidence returned by every retrieval path."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRole(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class CustomerTier(StrEnum):
    ENTERPRISE = "enterprise"
    MID_MARKET = "mid-market"
    SMB = "smb"


class IncidentSeverity(StrEnum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"


class IncidentStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class DecisionStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ResearchStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class EvidenceSourceType(StrEnum):
    DOCUMENT = "document"
    SQL = "sql"
    GRAPH = "graph"


class Evidence(BaseModel):
    """Store-neutral evidence with a stable identity and resolvable location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    source_type: EvidenceSourceType
    source_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    content: str = Field(min_length=1)
    title: str | None = None
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    query: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("id", "source_id", "locator", "content")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value
