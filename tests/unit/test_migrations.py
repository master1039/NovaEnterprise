"""The initial Alembic migration creates the complete Phase 2 schema."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from backend.app.core.config import get_settings

EXPECTED_TABLES = {
    "alembic_version",
    "audit_logs",
    "customers",
    "decisions",
    "document_chunks",
    "documents",
    "employees",
    "incident_customers",
    "incidents",
    "organizational_memory",
    "projects",
    "research_sessions",
    "scoped_memory",
    "services",
    "teams",
    "tickets",
    "workflow_events",
}


def test_initial_migration_upgrades_and_downgrades(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "migration.db"
    url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("NOVA_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    inspector = inspect(create_engine(url))
    assert set(inspector.get_table_names()) == EXPECTED_TABLES
    assert "ck_scoped_memory_user_scope_context" in {
        constraint["name"] for constraint in inspector.get_check_constraints("scoped_memory")
    }

    command.downgrade(config, "base")
    assert inspect(create_engine(url)).get_table_names() == ["alembic_version"]
    get_settings.cache_clear()


def test_rls_file_is_explicitly_postgresql_and_tenant_scoped() -> None:
    sql = Path("database/rls_policies.sql").read_text(encoding="utf-8")
    assert "SQLite local mode does not enforce RLS" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "current_setting(''app.tenant_id''" in sql
    for table in ("customers", "documents", "scoped_memory", "research_sessions", "audit_logs"):
        assert f"'{table}'" in sql
