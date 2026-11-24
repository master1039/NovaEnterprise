"""Safe SQL validation and evidence-normalizing execution tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import Incident, Service, Team
from backend.app.schemas.common import EvidenceSourceType, IncidentSeverity, IncidentStatus
from backend.app.services.seed import seed_database
from rag.sql_retrieval import (
    MAX_SQL_RESULTS,
    SQLExecutionError,
    SQLValidationError,
    build_incidents_for_service_query,
    execute_evidence_query,
    validate_read_only_sql,
)


def _valid_sql(*, limit: int = 10) -> str:
    return f"""
        SELECT i.id, i.title
        FROM incidents AS i
        WHERE i.tenant_id = :tenant_id
        ORDER BY i.started_at, i.id
        LIMIT {limit}
    """


def test_validator_accepts_one_bounded_tenant_scoped_select() -> None:
    result = validate_read_only_sql(_valid_sql())

    assert result.tables == ("incidents",)
    assert result.limit == 10


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id LIMIT 1; DROP TABLE incidents",
        "SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id -- bypass\nLIMIT 1",
        "SELECT i.id FROM incidents i /* bypass */ WHERE i.tenant_id=:tenant_id LIMIT 1",
        "DELETE FROM incidents WHERE tenant_id=:tenant_id",
        "UPDATE incidents SET title='x'",
        "INSERT INTO incidents (id) VALUES ('x')",
        "CREATE TABLE stolen (value TEXT)",
        "PRAGMA table_info(incidents)",
        "ATTACH DATABASE 'other.db' AS other",
        ("SELECT i.id INTO stolen FROM incidents i WHERE i.tenant_id=:tenant_id LIMIT 1"),
        ("SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id LIMIT 1 FOR UPDATE"),
    ],
)
def test_validator_rejects_injection_and_non_select_statements(sql: str) -> None:
    with pytest.raises(SQLValidationError):
        validate_read_only_sql(sql)


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("SELECT x.id FROM unknown_table x WHERE x.tenant_id=:tenant_id LIMIT 1", "table"),
        ("SELECT i.private_note FROM incidents i WHERE i.tenant_id=:tenant_id LIMIT 1", "column"),
        ("SELECT * FROM incidents i WHERE i.tenant_id=:tenant_id LIMIT 1", "wildcard"),
        ("SELECT i.id FROM incidents i LIMIT 1", "tenant"),
        ("SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id", "LIMIT"),
        (
            "SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id "
            f"LIMIT {MAX_SQL_RESULTS + 1}",
            "limit",
        ),
        (
            "SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id "
            "UNION SELECT s.id FROM services s WHERE s.tenant_id=:tenant_id LIMIT 1",
            "set",
        ),
        (
            "SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id "
            "AND i.id IN (SELECT id FROM incidents) LIMIT 1",
            "subquer",
        ),
        (
            "SELECT load_extension(i.id) FROM incidents i WHERE i.tenant_id=:tenant_id LIMIT 1",
            "function",
        ),
        (
            "SELECT i.id FROM main.incidents i WHERE i.tenant_id=:tenant_id LIMIT 1",
            "schema",
        ),
        (
            "SELECT i.id FROM incidents i WHERE i.tenant_id=:tenant_id "
            "AND i.title='interpolated' LIMIT 1",
            "literal",
        ),
        (
            "SELECT random() FROM incidents i WHERE i.tenant_id=:tenant_id LIMIT 1",
            "function",
        ),
    ],
)
def test_validator_rejects_allowlist_and_scope_bypasses(sql: str, message: str) -> None:
    with pytest.raises(SQLValidationError, match=message):
        validate_read_only_sql(sql)


def test_template_keeps_hostile_values_out_of_sql() -> None:
    hostile = "Payments API' OR 1=1; DROP TABLE incidents; --"
    query = build_incidents_for_service_query(
        service_name=hostile,
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        ended_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    assert hostile not in query.sql
    assert query.parameters["service_name"] == hostile
    assert ":service_name" in query.sql
    validate_read_only_sql(query.sql)


def test_executor_returns_canonical_incidents_at_exact_date_boundaries(
    db_session: Session,
) -> None:
    seed_database(db_session)
    query = build_incidents_for_service_query(
        service_name="Payments API",
        started_at=datetime(2026, 7, 14, 9, 20, tzinfo=UTC),
        ended_at=datetime(2026, 9, 21, 18, 0, tzinfo=UTC),
    )

    evidence = execute_evidence_query(db_session, tenant_id="novaenterprise-demo", query=query)

    assert [item.source_id for item in evidence] == ["inc-2031", "inc-2034"]
    assert all(item.source_type is EvidenceSourceType.SQL for item in evidence)
    assert all(item.query == query.sql for item in evidence)
    assert evidence[0].locator == "incidents.id=inc-2031"
    assert evidence[0].metadata["service_name"] == "Payments API"


def test_executor_is_tenant_isolated_and_uses_bound_parameters(db_session: Session) -> None:
    db_session.add(
        Team(
            id="team-other",
            tenant_id="tenant-other",
            name="Other team",
            description="Other tenant",
        )
    )
    db_session.flush()
    db_session.add(
        Service(
            id="svc-other-payments",
            tenant_id="tenant-other",
            name="Payments API",
            description="Other tenant",
            owner_team_id="team-other",
        )
    )
    db_session.add(
        Incident(
            id="inc-other",
            tenant_id="tenant-other",
            service_id="svc-other-payments",
            title="Other tenant incident",
            summary="Must stay isolated",
            root_cause="Test",
            severity=IncidentSeverity.SEV1,
            status=IncidentStatus.OPEN,
            started_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
    )
    db_session.commit()
    query = build_incidents_for_service_query(
        service_name="Payments API",
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        ended_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    result = execute_evidence_query(db_session, tenant_id="tenant-other", query=query)
    hostile = build_incidents_for_service_query(
        service_name="Payments API' OR 1=1 --",
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        ended_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    hostile_result = execute_evidence_query(
        db_session,
        tenant_id="tenant-other",
        query=hostile,
    )

    assert [item.source_id for item in result] == ["inc-other"]
    assert hostile_result == []
    assert db_session.scalar(select(func.count()).select_from(Incident)) == 1


def test_executor_is_deterministic_bounded_and_handles_empty_results(db_session: Session) -> None:
    seed_database(db_session)
    limited = build_incidents_for_service_query(
        service_name="Payments API",
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        ended_at=datetime(2026, 10, 1, tzinfo=UTC),
        limit=2,
    )

    first = execute_evidence_query(db_session, tenant_id="novaenterprise-demo", query=limited)
    second = execute_evidence_query(db_session, tenant_id="novaenterprise-demo", query=limited)
    missing = execute_evidence_query(
        db_session,
        tenant_id="novaenterprise-demo",
        query=build_incidents_for_service_query(
            service_name="Missing Service",
            started_at=datetime(2026, 7, 1, tzinfo=UTC),
            ended_at=datetime(2026, 10, 1, tzinfo=UTC),
        ),
    )

    assert len(first) == 2
    assert [item.id for item in first] == [item.id for item in second]
    assert [item.source_id for item in first] == ["inc-2031", "inc-2034"]
    assert missing == []


def test_template_rejects_invalid_ranges_and_limits() -> None:
    instant = datetime(2026, 7, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="ended_at"):
        build_incidents_for_service_query(
            service_name="Payments API", started_at=instant, ended_at=instant
        )
    with pytest.raises(ValueError, match="limit"):
        build_incidents_for_service_query(
            service_name="Payments API",
            started_at=instant,
            ended_at=datetime(2026, 8, 1, tzinfo=UTC),
            limit=MAX_SQL_RESULTS + 1,
        )


def test_executor_redacts_database_error_details(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    query = build_incidents_for_service_query(
        service_name="Payments API",
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        ended_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    def fail_execute(*_args, **_kwargs):
        raise RuntimeError("password=hunter2")

    monkeypatch.setattr(db_session, "execute", fail_execute)

    with pytest.raises(SQLExecutionError, match=r"\[REDACTED\]") as captured:
        execute_evidence_query(db_session, tenant_id="tenant-a", query=query)
    assert "hunter2" not in str(captured.value)
