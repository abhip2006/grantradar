"""Add grant_applications table for pipeline tracking

Revision ID: 004
Revises: 003
Create Date: 2025-01-07

Adds grant_applications table for tracking grants through the application pipeline:
- Stages: researching, writing, submitted, awarded, rejected
- Notes and target dates for user tracking
- Links to users, grants, and optionally matches
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# Revision identifiers
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create grant_applications table and its indexes."""

    # Create the application_stage enum type (with checkfirst to handle partial migrations)
    # First create the enum type if it doesn't exist
    connection = op.get_bind()
    result = connection.execute(
        sa.text(
            "SELECT 1 FROM pg_type WHERE typname = 'applicationstage'"
        )
    )
    if result.fetchone() is None:
        application_stage_enum = sa.Enum(
            "researching",
            "writing",
            "submitted",
            "awarded",
            "rejected",
            name="applicationstage",
        )
        application_stage_enum.create(connection, checkfirst=False)

    # Reference the enum for use in the table (create_type=False prevents duplicate creation)
    application_stage_enum = sa.Enum(
        "researching",
        "writing",
        "submitted",
        "awarded",
        "rejected",
        name="applicationstage",
        create_type=False,
    )

    # Create grant_applications table
    op.create_table(
        "grant_applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("grants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "match_id",
            UUID(as_uuid=True),
            sa.ForeignKey("matches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "stage",
            application_stage_enum,
            nullable=False,
            server_default="researching",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("target_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes
    op.create_index(
        "ix_grant_applications_user_id",
        "grant_applications",
        ["user_id"],
    )
    op.create_index(
        "ix_grant_applications_grant_id",
        "grant_applications",
        ["grant_id"],
    )
    op.create_index(
        "ix_grant_applications_stage",
        "grant_applications",
        ["stage"],
    )

    # Create unique constraint for user_id + grant_id
    op.create_unique_constraint(
        "uq_grant_applications_user_grant",
        "grant_applications",
        ["user_id", "grant_id"],
    )


def downgrade() -> None:
    """Drop grant_applications table and application_stage enum."""

    # Drop unique constraint
    op.drop_constraint(
        "uq_grant_applications_user_grant",
        "grant_applications",
        type_="unique",
    )

    # Drop indexes
    op.drop_index("ix_grant_applications_stage", table_name="grant_applications")
    op.drop_index("ix_grant_applications_grant_id", table_name="grant_applications")
    op.drop_index("ix_grant_applications_user_id", table_name="grant_applications")

    # Drop table
    op.drop_table("grant_applications")

    # Drop the enum type
    sa.Enum(name="applicationstage").drop(op.get_bind(), checkfirst=True)
