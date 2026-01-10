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

# Revision identifiers
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create grant_applications table and its indexes."""
    connection = op.get_bind()

    # Check if table already exists (handles partial migration state)
    table_exists = connection.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'grant_applications'"
        )
    ).fetchone()

    if table_exists:
        # Table already exists, migration was already applied
        print("grant_applications table already exists, skipping migration")
        return

    # Create the enum type using raw SQL if it doesn't exist
    enum_exists = connection.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'applicationstage'")
    ).fetchone()

    if not enum_exists:
        connection.execute(
            sa.text(
                "CREATE TYPE applicationstage AS ENUM "
                "('researching', 'writing', 'submitted', 'awarded', 'rejected')"
            )
        )

    # Create grant_applications table using raw SQL to avoid SQLAlchemy's
    # automatic enum type creation which causes "already exists" errors
    connection.execute(
        sa.text("""
            CREATE TABLE grant_applications (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                grant_id UUID NOT NULL REFERENCES grants(id) ON DELETE CASCADE,
                match_id UUID REFERENCES matches(id) ON DELETE SET NULL,
                stage applicationstage NOT NULL DEFAULT 'researching',
                notes TEXT,
                target_date TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)
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
