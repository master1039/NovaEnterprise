"""AST-validated, tenant-scoped SQL templates and evidence execution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import sqlglot
from sqlalchemy import DateTime, String, bindparam, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlglot import exp
from sqlglot.errors import ParseError

from backend.app.core.guardrails import redact_secrets
from backend.app.schemas.common import Evidence, EvidenceSourceType

MAX_SQL_RESULTS = 100

_ALLOWED_COLUMNS: dict[str, frozenset[str]] = {
    "teams": frozenset({"id", "tenant_id", "name", "description"}),
    "services": frozenset({"id", "tenant_id", "name", "description", "owner_team_id"}),
    "customers": frozenset({"id", "tenant_id", "name", "tier"}),
    "incidents": frozenset(
        {
            "id",
            "tenant_id",
            "service_id",
            "title",
            "summary",
            "root_cause",
            "severity",
            "status",
            "started_at",
            "resolved_at",
        }
    ),
    "incident_customers": frozenset({"tenant_id", "incident_id", "customer_id"}),
    "decisions": frozenset(
        {
            "id",
            "tenant_id",
            "incident_id",
            "service_id",
            "title",
            "summary",
            "status",
            "decided_at",
        }
    ),
    "projects": frozenset({"id", "tenant_id", "name", "description", "owner_team_id", "status"}),
    "tickets": frozenset(
        {
            "id",
            "tenant_id",
            "title",
            "description",
            "customer_id",
            "project_id",
            "assigned_team_id",
            "status",
            "priority",
        }
    ),
}
_ALLOWED_FUNCTIONS = frozenset({"AVG", "COALESCE", "COUNT", "MAX", "MIN", "SUM"})
_COMMENT_MARKERS = ("--", "/*", "*/", "#")


class SQLValidationError(ValueError):
    """Raised when SQL falls outside the deliberately narrow read-only contract."""


class SQLExecutionError(RuntimeError):
    """Raised when an approved query cannot be executed safely."""


@dataclass(frozen=True)
class SQLValidationResult:
    tables: tuple[str, ...]
    limit: int
    parameters: tuple[str, ...]


@dataclass(frozen=True)
class SQLQuerySpec:
    name: str
    sql: str
    parameters: dict[str, Any]


def validate_read_only_sql(sql: str) -> SQLValidationResult:
    """Validate one bounded, tenant-scoped SELECT using SQLGlot's SQLite AST."""

    if not sql or not sql.strip():
        raise SQLValidationError("SQL must not be blank")
    lowered = sql.casefold()
    if ";" in sql:
        raise SQLValidationError("SQL must contain exactly one statement without semicolons")
    if any(marker in lowered for marker in _COMMENT_MARKERS):
        raise SQLValidationError("SQL comments are not allowed")

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except ParseError as exc:
        raise SQLValidationError("SQL could not be parsed") from exc
    if len(statements) != 1:
        raise SQLValidationError("only one SELECT statement is allowed")
    if isinstance(statements[0], exp.SetOperation):
        raise SQLValidationError("set operations are not allowed")
    if not isinstance(statements[0], exp.Select):
        raise SQLValidationError("only one SELECT statement is allowed")
    statement = statements[0]

    if statement.args.get("with_") is not None:
        raise SQLValidationError("CTEs are not allowed by the Phase 6 SQL contract")
    if statement.args.get("into") is not None:
        raise SQLValidationError("SELECT INTO is not allowed")
    if statement.args.get("locks"):
        raise SQLValidationError("locking SELECT statements are not allowed")
    if any(isinstance(node, exp.SetOperation) for node in statement.walk()):
        raise SQLValidationError("set operations are not allowed")
    if sum(isinstance(node, exp.Select) for node in statement.walk()) > 1 or any(
        isinstance(node, (exp.Subquery, exp.Exists)) for node in statement.walk()
    ):
        raise SQLValidationError("subqueries are not allowed")
    if any(isinstance(node, exp.Or) for node in statement.walk()):
        raise SQLValidationError("OR predicates are not allowed")
    if statement.find(exp.Offset) is not None:
        raise SQLValidationError("OFFSET is not allowed")
    if statement.find(exp.Star) is not None:
        raise SQLValidationError("wildcard columns are not allowed")
    if any(identifier.args.get("quoted") for identifier in statement.find_all(exp.Identifier)):
        raise SQLValidationError("Quoted identifiers are not allowed")

    tables = list(statement.find_all(exp.Table))
    if not tables:
        raise SQLValidationError("A query must read an allowlisted table")
    alias_to_table: dict[str, str] = {}
    for table in tables:
        table_name = table.name.casefold()
        if table.db or table.catalog:
            raise SQLValidationError("schema-qualified tables are not allowed")
        if table_name not in _ALLOWED_COLUMNS:
            raise SQLValidationError(f"Table '{table_name}' is not allowlisted")
        alias = table.alias_or_name.casefold()
        if alias in alias_to_table:
            raise SQLValidationError("Table aliases must be unique")
        alias_to_table[alias] = table_name

    for join in statement.args.get("joins") or ():
        if join.args.get("on") is None:
            raise SQLValidationError("Every joined table requires an ON predicate")

    for column in statement.find_all(exp.Column):
        if not column.table:
            raise SQLValidationError("Every column must use an explicit table alias")
        alias = column.table.casefold()
        table_name = alias_to_table.get(alias)
        if table_name is None:
            raise SQLValidationError(f"Unknown table alias '{alias}'")
        column_name = column.name.casefold()
        if column_name not in _ALLOWED_COLUMNS[table_name]:
            raise SQLValidationError(f"column '{table_name}.{column_name}' is not allowlisted")

    for literal in statement.find_all(exp.Literal):
        if literal.is_string:
            raise SQLValidationError("string literals are not allowed; use bound parameters")

    for function in statement.find_all(exp.Func):
        if isinstance(function, exp.Connector):
            continue
        if function.sql_name().upper() not in _ALLOWED_FUNCTIONS:
            raise SQLValidationError("function is not allowlisted")

    tenant_aliases = _tenant_scoped_aliases(statement)
    missing_tenant_scope = sorted(set(alias_to_table) - tenant_aliases)
    if missing_tenant_scope:
        raise SQLValidationError(
            "Every table requires an explicit tenant_id = :tenant_id predicate"
        )

    limit_node = statement.args.get("limit")
    if limit_node is None or not isinstance(limit_node.expression, exp.Literal):
        raise SQLValidationError("A literal LIMIT is required")
    try:
        limit = int(limit_node.expression.this)
    except (TypeError, ValueError) as exc:
        raise SQLValidationError("LIMIT must be an integer") from exc
    if not 1 <= limit <= MAX_SQL_RESULTS:
        raise SQLValidationError(f"limit must be between 1 and {MAX_SQL_RESULTS}")

    parameters = tuple(
        sorted({placeholder.name for placeholder in statement.find_all(exp.Placeholder)})
    )
    if "tenant_id" not in parameters:
        raise SQLValidationError("The tenant_id bound parameter is required")
    return SQLValidationResult(
        tables=tuple(sorted(set(alias_to_table.values()))),
        limit=limit,
        parameters=parameters,
    )


def _tenant_scoped_aliases(statement: exp.Select) -> set[str]:
    scoped: set[str] = set()
    where = statement.args.get("where")
    if where is None:
        return scoped
    for equality in where.find_all(exp.EQ):
        pairs = ((equality.left, equality.right), (equality.right, equality.left))
        for column, placeholder in pairs:
            if (
                isinstance(column, exp.Column)
                and column.name.casefold() == "tenant_id"
                and column.table
                and isinstance(placeholder, exp.Placeholder)
                and placeholder.name.casefold() == "tenant_id"
            ):
                scoped.add(column.table.casefold())
    return scoped


def build_incidents_for_service_query(
    *,
    service_name: str,
    started_at: datetime,
    ended_at: datetime,
    limit: int = 25,
) -> SQLQuerySpec:
    """Build the canonical half-open [started_at, ended_at) incident query."""

    if not service_name.strip():
        raise ValueError("service_name must not be blank")
    if ended_at <= started_at:
        raise ValueError("ended_at must be later than started_at")
    if not 1 <= limit <= MAX_SQL_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_SQL_RESULTS}")
    sql = f"""
        SELECT
            i.id AS incident_id,
            i.title AS incident_title,
            i.summary AS incident_summary,
            i.root_cause AS root_cause,
            i.severity AS severity,
            i.status AS incident_status,
            i.started_at AS started_at,
            i.resolved_at AS resolved_at,
            s.name AS service_name
        FROM incidents AS i
        JOIN services AS s
          ON s.id = i.service_id
         AND s.tenant_id = i.tenant_id
        WHERE i.tenant_id = :tenant_id
          AND s.tenant_id = :tenant_id
          AND s.name = :service_name
          AND i.started_at >= :started_at
          AND i.started_at < :ended_at
        ORDER BY i.started_at ASC, i.id ASC
        LIMIT {limit}
    """.strip()
    validate_read_only_sql(sql)
    return SQLQuerySpec(
        name="incidents_for_service",
        sql=sql,
        parameters={
            "service_name": service_name,
            "started_at": started_at,
            "ended_at": ended_at,
        },
    )


def execute_evidence_query(
    session: Session,
    *,
    tenant_id: str,
    query: SQLQuerySpec,
) -> list[Evidence]:
    """Execute an approved template with bound values and normalize SQL evidence."""

    if not tenant_id.strip():
        raise ValueError("tenant_id must not be blank")
    if query.name != "incidents_for_service":
        raise SQLExecutionError("No evidence normalizer is registered for this query")
    validation = validate_read_only_sql(query.sql)
    parameters = {**query.parameters, "tenant_id": tenant_id}
    missing = set(validation.parameters) - set(parameters)
    if missing:
        raise SQLValidationError(f"Missing bound query parameters: {sorted(missing)}")
    statement = text(query.sql).bindparams(
        bindparam("tenant_id", type_=String()),
        bindparam("service_name", type_=String()),
        bindparam("started_at", type_=DateTime(timezone=True)),
        bindparam("ended_at", type_=DateTime(timezone=True)),
    )
    try:
        rows = session.execute(statement, parameters).mappings().all()
    except (SQLAlchemyError, RuntimeError) as exc:
        safe_detail = redact_secrets(str(exc))
        raise SQLExecutionError(f"Safe SQL query failed: {safe_detail}") from exc
    try:
        return [_incident_evidence(row, tenant_id=tenant_id, query=query) for row in rows]
    except (KeyError, TypeError, ValueError) as exc:
        raise SQLExecutionError("Safe SQL result did not match its evidence contract") from exc


def _incident_evidence(
    row: dict[str, Any],
    *,
    tenant_id: str,
    query: SQLQuerySpec,
) -> Evidence:
    incident_id = str(row["incident_id"])
    stable_digest = hashlib.sha256(
        f"{tenant_id}\0{query.name}\0{incident_id}".encode()
    ).hexdigest()[:24]
    service_name = redact_secrets(str(row["service_name"]))
    severity = str(row["severity"])
    status = str(row["incident_status"])
    summary = redact_secrets(str(row["incident_summary"]))
    root_cause = redact_secrets(str(row["root_cause"]))
    content = (
        f"{service_name} incident {incident_id}: {row['incident_title']} "
        f"({severity}, {status}). {summary} Root cause: {root_cause}"
    )
    return Evidence(
        id=f"evidence-sql-{stable_digest}",
        source_type=EvidenceSourceType.SQL,
        source_id=incident_id,
        locator=f"incidents.id={incident_id}",
        title=redact_secrets(str(row["incident_title"])),
        content=content,
        query=query.sql,
        metadata={
            "query_name": query.name,
            "service_name": service_name,
            "severity": severity,
            "status": status,
            "started_at": str(row["started_at"]),
            "resolved_at": str(row["resolved_at"]) if row["resolved_at"] is not None else None,
        },
    )


__all__ = [
    "MAX_SQL_RESULTS",
    "SQLExecutionError",
    "SQLQuerySpec",
    "SQLValidationError",
    "SQLValidationResult",
    "build_incidents_for_service_query",
    "execute_evidence_query",
    "validate_read_only_sql",
]
