"""Add document components library tables.

Revision ID: 024
Revises: 023
Create Date: 2025-01-08

This migration creates tables for the Component Library feature:
- document_components: Reusable document components (facilities, biosketches, boilerplate)
- component_usage: Tracks where components are used in applications
- document_versions: Version control for application documents
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_components table
    op.create_table(
        "document_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),  # facilities, equipment, biosketch, boilerplate
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),  # Additional structured data
        sa.Column("tags", postgresql.JSONB(), nullable=True),  # Searchable tags
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),  # Reference to previous version
        sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add foreign key constraint for parent_id (self-reference for versioning)
    op.create_foreign_key(
        "fk_document_components_parent",
        "document_components",
        "document_components",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL"
    )

    # Create indexes for document_components
    op.create_index("ix_document_components_user_id", "document_components", ["user_id"])
    op.create_index("ix_document_components_category", "document_components", ["category"])
    op.create_index("ix_document_components_is_current", "document_components", ["is_current"])
    op.create_index("ix_document_components_is_archived", "document_components", ["is_archived"])
    op.create_index("ix_document_components_parent_id", "document_components", ["parent_id"])

    # Create component_usage table
    op.create_table(
        "component_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kanban_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(100), nullable=True),  # Which section the component was used in
        sa.Column("inserted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for component_usage
    op.create_index("ix_component_usage_component_id", "component_usage", ["component_id"])
    op.create_index("ix_component_usage_kanban_card_id", "component_usage", ["kanban_card_id"])
    op.create_index("ix_component_usage_used_at", "component_usage", ["used_at"])

    # Create document_versions table
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kanban_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(100), nullable=True),  # Section name (e.g., 'specific_aims', 'budget')
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("snapshot_name", sa.String(255), nullable=True),  # User-defined name for named snapshots
        sa.Column("change_summary", sa.Text(), nullable=True),  # Description of what changed
        sa.Column("file_path", sa.String(500), nullable=True),  # Path to attached file if any
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_type", sa.String(100), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for document_versions
    op.create_index("ix_document_versions_kanban_card_id", "document_versions", ["kanban_card_id"])
    op.create_index("ix_document_versions_section", "document_versions", ["section"])
    op.create_index("ix_document_versions_version_number", "document_versions", ["kanban_card_id", "section", "version_number"])
    op.create_index("ix_document_versions_created_at", "document_versions", ["created_at"])

    # Create unique constraint for version numbers within card/section
    op.create_unique_constraint(
        "uq_document_versions_card_section_version",
        "document_versions",
        ["kanban_card_id", "section", "version_number"]
    )


def downgrade() -> None:
    # Drop document_versions table and indexes
    op.drop_constraint("uq_document_versions_card_section_version", "document_versions", type_="unique")
    op.drop_index("ix_document_versions_created_at", table_name="document_versions")
    op.drop_index("ix_document_versions_version_number", table_name="document_versions")
    op.drop_index("ix_document_versions_section", table_name="document_versions")
    op.drop_index("ix_document_versions_kanban_card_id", table_name="document_versions")
    op.drop_table("document_versions")

    # Drop component_usage table and indexes
    op.drop_index("ix_component_usage_used_at", table_name="component_usage")
    op.drop_index("ix_component_usage_kanban_card_id", table_name="component_usage")
    op.drop_index("ix_component_usage_component_id", table_name="component_usage")
    op.drop_table("component_usage")

    # Drop document_components table and indexes
    op.drop_constraint("fk_document_components_parent", "document_components", type_="foreignkey")
    op.drop_index("ix_document_components_parent_id", table_name="document_components")
    op.drop_index("ix_document_components_is_archived", table_name="document_components")
    op.drop_index("ix_document_components_is_current", table_name="document_components")
    op.drop_index("ix_document_components_category", table_name="document_components")
    op.drop_index("ix_document_components_user_id", table_name="document_components")
    op.drop_table("document_components")
