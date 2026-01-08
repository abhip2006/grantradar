"""Add grant_deadline_history table for deadline forecasting.

Revision ID: 011
Revises: 010
Create Date: 2025-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create grant_deadline_history table for storing historical deadline data."""
    op.create_table(
        "grant_deadline_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "grant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("grants.id", ondelete="SET NULL"),
            nullable=True,
            comment="Optional reference to matching grant in system (null for historical records)",
        ),
        sa.Column(
            "funder_name",
            sa.String(255),
            nullable=False,
            comment="Name of the funding organization",
        ),
        sa.Column(
            "grant_title",
            sa.Text(),
            nullable=False,
            comment="Title of the grant opportunity",
        ),
        sa.Column(
            "deadline_date",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            comment="Application deadline date",
        ),
        sa.Column(
            "open_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Date when grant opened for applications",
        ),
        sa.Column(
            "announcement_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Date when grant was announced",
        ),
        sa.Column(
            "fiscal_year",
            sa.Integer(),
            nullable=False,
            comment="Fiscal year of the grant cycle",
        ),
        sa.Column(
            "amount_min",
            sa.Integer(),
            nullable=True,
            comment="Minimum funding amount in USD",
        ),
        sa.Column(
            "amount_max",
            sa.Integer(),
            nullable=True,
            comment="Maximum funding amount in USD",
        ),
        sa.Column(
            "categories",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            comment="Research categories/tags associated with the grant",
        ),
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            comment="Data source (e.g., 'grants.gov', 'nih', 'nsf')",
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
    op.create_index(
        "ix_grant_deadline_history_funder_name",
        "grant_deadline_history",
        ["funder_name"],
    )
    op.create_index(
        "ix_grant_deadline_history_deadline_date",
        "grant_deadline_history",
        ["deadline_date"],
    )
    op.create_index(
        "ix_grant_deadline_history_fiscal_year",
        "grant_deadline_history",
        ["fiscal_year"],
    )
    op.create_index(
        "ix_grant_deadline_history_source",
        "grant_deadline_history",
        ["source"],
    )
    op.create_index(
        "ix_grant_deadline_history_grant_id",
        "grant_deadline_history",
        ["grant_id"],
    )


def downgrade() -> None:
    """Remove grant_deadline_history table."""
    # Drop indexes
    op.drop_index("ix_grant_deadline_history_grant_id", table_name="grant_deadline_history")
    op.drop_index("ix_grant_deadline_history_source", table_name="grant_deadline_history")
    op.drop_index("ix_grant_deadline_history_fiscal_year", table_name="grant_deadline_history")
    op.drop_index("ix_grant_deadline_history_deadline_date", table_name="grant_deadline_history")
    op.drop_index("ix_grant_deadline_history_funder_name", table_name="grant_deadline_history")

    # Drop table
    op.drop_table("grant_deadline_history")
