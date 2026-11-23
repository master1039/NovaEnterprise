"""Canonical demo data is complete, connected, and idempotent."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import Document
from backend.app.repositories.enterprise import IncidentRepository, ServiceRepository
from backend.app.services.seed import seed_database

EXPECTED_COUNTS = {
    "teams": 6,
    "employees": 20,
    "services": 8,
    "customers": 10,
    "incidents": 12,
    "decisions": 8,
    "projects": 6,
    "tickets": 15,
    "organizational_memory": 3,
    "documents": 15,
}


def test_seed_counts_relationships_and_idempotency(db_session: Session) -> None:
    first = seed_database(db_session)
    second = seed_database(db_session)
    assert first == EXPECTED_COUNTS
    assert second == EXPECTED_COUNTS

    services = ServiceRepository(db_session, "novaenterprise-demo")
    payments = services.by_name("Payments API")
    assert payments is not None
    assert payments.owner_team_id == "team-payments"

    incidents = IncidentRepository(db_session, "novaenterprise-demo").for_service_between(
        payments.id,
        datetime(2026, 7, 1, tzinfo=UTC),
        datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert [incident.id for incident in incidents] == ["inc-2031", "inc-2034", "inc-2040"]
    impacted = {customer.id for incident in incidents for customer in incident.impacted_customers}
    assert impacted == {"cust-acme", "cust-globex", "cust-initech", "cust-umbrella", "cust-stark"}

    hostile = db_session.scalar(select(Document).where(Document.id.like("%vendor-note%")))
    assert hostile is not None and hostile.is_untrusted is True
    assert db_session.scalar(select(func.count()).select_from(Document)) == 15
