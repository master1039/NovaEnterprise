"""Add durable user memory and organizational provenance metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0002_scoped_memory"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizational_memory",
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_table(
        "scoped_memory",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("scope", sa.String(24), nullable=False),
        sa.Column("user_id", sa.String(64)),
        sa.Column("session_id", sa.String(64)),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(240), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope = 'user' AND user_id IS NOT NULL AND session_id IS NULL",
            name="user_scope_context",
        ),
    )
    op.create_index("ix_scoped_memory_scope", "scoped_memory", ["scope"])
    op.create_index("ix_scoped_memory_user_id", "scoped_memory", ["user_id"])
    op.create_index("ix_scoped_memory_session_id", "scoped_memory", ["session_id"])
    op.create_index("ix_scoped_memory_tenant_id", "scoped_memory", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("scoped_memory")
    op.drop_column("organizational_memory", "metadata_json")
