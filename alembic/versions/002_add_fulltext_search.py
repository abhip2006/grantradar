"""Add PostgreSQL full-text search to grants table

Revision ID: 002
Revises: 001
Create Date: 2025-01-07

Adds:
- search_vector column (tsvector) combining title, description, and agency
- GIN index on search_vector for fast full-text search
- Trigger to auto-update search_vector on INSERT/UPDATE
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full-text search capabilities to grants table."""

    # Add search_vector column (tsvector)
    op.add_column(
        "grants",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
        ),
    )

    # Create GIN index on search_vector for fast full-text search
    op.create_index(
        "ix_grants_search_vector",
        "grants",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create function to generate search vector from title, description, and agency
    # Title gets weight 'A' (highest), agency gets 'B', description gets 'C'
    op.execute(
        """
        CREATE OR REPLACE FUNCTION grants_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.agency, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger to auto-update search_vector on INSERT or UPDATE
    op.execute(
        """
        CREATE TRIGGER grants_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, description, agency
        ON grants
        FOR EACH ROW
        EXECUTE FUNCTION grants_search_vector_update();
        """
    )

    # Populate search_vector for existing rows
    op.execute(
        """
        UPDATE grants SET search_vector =
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(agency, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(description, '')), 'C');
        """
    )


def downgrade() -> None:
    """Remove full-text search capabilities from grants table."""

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS grants_search_vector_trigger ON grants")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS grants_search_vector_update()")

    # Drop index
    op.drop_index("ix_grants_search_vector", table_name="grants")

    # Drop column
    op.drop_column("grants", "search_vector")
