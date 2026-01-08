"""Add kanban columns to grant_applications.

Revision ID: 019
Revises: 018
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add kanban columns to grant_applications table
    op.add_column("grant_applications", sa.Column("position", sa.Integer(), server_default="0", nullable=False))
    op.add_column("grant_applications", sa.Column("priority", sa.String(20), server_default="medium", nullable=False))
    op.add_column("grant_applications", sa.Column("color", sa.String(7), nullable=True))
    op.add_column("grant_applications", sa.Column("archived", sa.Boolean(), server_default="false", nullable=False))

    # Add indexes for common queries
    op.create_index("ix_grant_applications_position", "grant_applications", ["position"])
    op.create_index("ix_grant_applications_priority", "grant_applications", ["priority"])
    op.create_index("ix_grant_applications_archived", "grant_applications", ["archived"])


def downgrade() -> None:
    op.drop_index("ix_grant_applications_archived", table_name="grant_applications")
    op.drop_index("ix_grant_applications_priority", table_name="grant_applications")
    op.drop_index("ix_grant_applications_position", table_name="grant_applications")
    op.drop_column("grant_applications", "archived")
    op.drop_column("grant_applications", "color")
    op.drop_column("grant_applications", "priority")
    op.drop_column("grant_applications", "position")
