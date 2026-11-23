"""Idempotent deterministic seed loader for the NovaEnterprise demo tenant."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal, engine
from backend.app.models import (
    Base,
    Customer,
    Decision,
    Document,
    Employee,
    Incident,
    OrganizationalMemory,
    Project,
    Service,
    Team,
    Ticket,
    incident_customers,
)
from backend.app.schemas.domain import (
    CustomerSeed,
    DecisionSeed,
    EmployeeSeed,
    IncidentSeed,
    OrganizationalMemorySeed,
    ProjectSeed,
    ServiceSeed,
    TeamSeed,
    TicketSeed,
)

DEFAULT_SAMPLE_ROOT = Path(__file__).resolve().parents[3] / "sample_data"


def _load_list[SchemaT: BaseModel](path: Path, schema: type[SchemaT]) -> list[SchemaT]:
    return TypeAdapter(list[schema]).validate_python(json.loads(path.read_text(encoding="utf-8")))


def _values(item: BaseModel, *, tenant_id: str, exclude: set[str] | None = None) -> dict:
    return {"tenant_id": tenant_id, **item.model_dump(exclude=exclude or set())}


def seed_database(
    session: Session,
    *,
    sample_root: Path = DEFAULT_SAMPLE_ROOT,
    tenant_id: str = "novaenterprise-demo",
) -> dict[str, int]:
    """Load fixed IDs with merge semantics, so rerunning never creates duplicates."""

    teams = _load_list(sample_root / "teams.json", TeamSeed)
    employees = _load_list(sample_root / "employees.json", EmployeeSeed)
    services = _load_list(sample_root / "services.json", ServiceSeed)
    customers = _load_list(sample_root / "customers.json", CustomerSeed)
    incidents = _load_list(sample_root / "incidents.json", IncidentSeed)
    decisions = _load_list(sample_root / "decisions.json", DecisionSeed)
    projects = _load_list(sample_root / "projects.json", ProjectSeed)
    tickets = _load_list(sample_root / "tickets.json", TicketSeed)
    memories = _load_list(sample_root / "organizational_memory.json", OrganizationalMemorySeed)

    for schema_items, model in (
        (teams, Team),
        (employees, Employee),
        (services, Service),
        (customers, Customer),
        (projects, Project),
        (tickets, Ticket),
        (memories, OrganizationalMemory),
    ):
        for item in schema_items:
            session.merge(model(**_values(item, tenant_id=tenant_id)))
        session.flush()

    for item in incidents:
        values = _values(item, tenant_id=tenant_id, exclude={"impacted_customer_ids"})
        session.merge(Incident(**values))
        session.flush()
        customers_by_id = {
            customer_id: session.get(Customer, customer_id)
            for customer_id in item.impacted_customer_ids
        }
        if any(customer is None for customer in customers_by_id.values()):
            raise ValueError(f"incident {item.id} references an unknown customer")
        session.execute(
            delete(incident_customers).where(
                incident_customers.c.tenant_id == tenant_id,
                incident_customers.c.incident_id == item.id,
            )
        )
        session.execute(
            insert(incident_customers),
            [
                {
                    "tenant_id": tenant_id,
                    "incident_id": item.id,
                    "customer_id": customer_id,
                }
                for customer_id in item.impacted_customer_ids
            ],
        )
    session.flush()

    for item in decisions:
        session.merge(Decision(**_values(item, tenant_id=tenant_id)))

    document_paths = sorted((sample_root / "documents").glob("*.md"))
    for path in document_paths:
        content = path.read_text(encoding="utf-8")
        stem = path.stem
        session.merge(
            Document(
                id=f"doc-{stem}",
                tenant_id=tenant_id,
                title=content.splitlines()[0].lstrip("# ").strip() or stem,
                source_path=f"documents/{path.name}",
                document_type=stem.split("-", 1)[0],
                content=content,
                content_sha256=hashlib.sha256(content.encode()).hexdigest(),
                is_untrusted="vendor-note" in stem,
            )
        )
    session.commit()

    models = {
        "teams": Team,
        "employees": Employee,
        "services": Service,
        "customers": Customer,
        "incidents": Incident,
        "decisions": Decision,
        "projects": Project,
        "tickets": Ticket,
        "organizational_memory": OrganizationalMemory,
        "documents": Document,
    }
    return {
        name: int(
            session.scalar(
                select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
            )
            or 0
        )
        for name, model in models.items()
    }


def main() -> None:
    settings = get_settings()
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        counts = seed_database(session, tenant_id=settings.default_tenant_id)
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
