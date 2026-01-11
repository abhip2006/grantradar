"""Add kanban columns to grant_applications.

Revision ID: 019
Revises: 018
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(index_name: str, table_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    """Add kanban columns to grant_applications (idempotent)."""
    # Add kanban columns to grant_applications table
    if not column_exists("grant_applications", "position"):
        op.add_column("grant_applications", sa.Column("position", sa.Integer(), server_default="0", nullable=False))
    if not column_exists("grant_applications", "priority"):
        op.add_column("grant_applications", sa.Column("priority", sa.String(20), server_default="medium", nullable=False))
    if not column_exists("grant_applications", "color"):
        op.add_column("grant_applications", sa.Column("color", sa.String(7), nullable=True))
    if not column_exists("grant_applications", "archived"):
        op.add_column("grant_applications", sa.Column("archived", sa.Boolean(), server_default="false", nullable=False))

    # Add indexes for common queries
    if not index_exists("ix_grant_applications_position", "grant_applications"):
        op.create_index("ix_grant_applications_position", "grant_applications", ["position"])
    if not index_exists("ix_grant_applications_priority", "grant_applications"):
        op.create_index("ix_grant_applications_priority", "grant_applications", ["priority"])
    if not index_exists("ix_grant_applications_archived", "grant_applications"):
        op.create_index("ix_grant_applications_archived", "grant_applications", ["archived"])


def downgrade() -> None:
    op.drop_index("ix_grant_applications_archived", table_name="grant_applications")
    op.drop_index("ix_grant_applications_priority", table_name="grant_applications")
    op.drop_index("ix_grant_applications_position", table_name="grant_applications")
    op.drop_column("grant_applications", "archived")
    op.drop_column("grant_applications", "color")
    op.drop_column("grant_applications", "priority")
    op.drop_column("grant_applications", "position")
