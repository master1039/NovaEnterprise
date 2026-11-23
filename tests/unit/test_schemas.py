"""Phase 2 domain contracts reject ambiguity before persistence."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.app.schemas.common import Evidence, EvidenceSourceType
from backend.app.schemas.domain import (
    AuditLogRead,
    DocumentRead,
    IncidentSeed,
    ResearchSessionRead,
    WorkflowEventRead,
)


def test_evidence_normalizes_all_retrieval_sources() -> None:
    evidence = Evidence(
        id="ev-sql-inc-2031",
        source_type=EvidenceSourceType.SQL,
        source_id="inc-2031",
        locator="incidents.id=inc-2031",
        content="Payments API outage",
        score=1.0,
        metadata={"service_id": "svc-payments"},
    )
    assert evidence.source_type == EvidenceSourceType.SQL
    assert evidence.metadata["service_id"] == "svc-payments"


def test_evidence_rejects_blank_locator_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Evidence(
            id="ev-1",
            source_type="document",
            source_id="doc-1",
            locator=" ",
            content="content",
            unsupported=True,
        )


def test_incident_seed_validates_enums_and_timestamps() -> None:
    incident = IncidentSeed(
        id="inc-1",
        service_id="svc-1",
        title="Example",
        summary="Summary",
        root_cause="Cause",
        severity="sev1",
        status="resolved",
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        impacted_customer_ids=["cust-1"],
    )
    assert incident.severity.value == "sev1"
    assert incident.impacted_customer_ids == ["cust-1"]


def test_persistence_read_schemas_are_public_contracts() -> None:
    for schema in (DocumentRead, ResearchSessionRead, WorkflowEventRead, AuditLogRead):
        assert schema.model_config["from_attributes"] is True
        assert schema.model_config["extra"] == "forbid"
