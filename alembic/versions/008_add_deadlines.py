"""Add deadlines table for user deadline tracking.

Revision ID: 008
Revises: 007
Create Date: 2025-01-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create deadlines table for tracking user grant submission deadlines."""
    op.create_table(
        "deadlines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("grants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("funder", sa.String(100), nullable=True),
        sa.Column("mechanism", sa.String(50), nullable=True),
        sa.Column(
            "sponsor_deadline",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "internal_deadline",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "color",
            sa.String(7),
            nullable=False,
            server_default="#3B82F6",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for efficient querying
    op.create_index("ix_deadlines_user_id", "deadlines", ["user_id"])
    op.create_index("ix_deadlines_sponsor_deadline", "deadlines", ["sponsor_deadline"])
    op.create_index("ix_deadlines_status", "deadlines", ["status"])


def downgrade() -> None:
    """Remove deadlines table."""
    op.drop_index("ix_deadlines_status", table_name="deadlines")
    op.drop_index("ix_deadlines_sponsor_deadline", table_name="deadlines")
    op.drop_index("ix_deadlines_user_id", table_name="deadlines")
    op.drop_table("deadlines")
