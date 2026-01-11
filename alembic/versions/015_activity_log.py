"""Add application activities table.

Revision ID: 015
Revises: 014
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Create application_activities table (idempotent)."""
    if table_exists("application_activities"):
        return

    op.create_table(
        "application_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activities_application_id", "application_activities", ["application_id"])
    op.create_index("ix_activities_created_at", "application_activities", [sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_activities_created_at", table_name="application_activities")
    op.drop_index("ix_activities_application_id", table_name="application_activities")
    op.drop_table("application_activities")
