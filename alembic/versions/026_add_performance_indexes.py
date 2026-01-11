"""Add performance indexes for dashboard features.

Revision ID: 026
Revises: 025
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def index_exists(index_name: str, table_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    """Add performance indexes (idempotent)."""
    # Composite index for pending reviews lookup
    if not index_exists("ix_application_reviews_card_status", "application_reviews"):
        op.create_index(
            "ix_application_reviews_card_status",
            "application_reviews",
            ["kanban_card_id", "status"]
        )

    # Composite index for workflow analytics time-range queries
    if not index_exists("ix_workflow_events_stage_occurred", "workflow_events"):
        op.create_index(
            "ix_workflow_events_stage_occurred",
            "workflow_events",
            ["stage", "occurred_at"]
        )

    # Composite index for recent compliance scans
    if not index_exists("ix_compliance_scans_card_scanned", "compliance_scans"):
        op.create_index(
            "ix_compliance_scans_card_scanned",
            "compliance_scans",
            ["kanban_card_id", "scanned_at"]
        )

    # Composite index for filtered component lists
    if not index_exists("ix_document_components_user_category_current", "document_components"):
        op.create_index(
            "ix_document_components_user_category_current",
            "document_components",
            ["user_id", "category", "is_current"]
        )


def downgrade() -> None:
    op.drop_index("ix_document_components_user_category_current", "document_components")
    op.drop_index("ix_compliance_scans_card_scanned", "compliance_scans")
    op.drop_index("ix_workflow_events_stage_occurred", "workflow_events")
    op.drop_index("ix_application_reviews_card_status", "application_reviews")
