"""Add compliance scanner tables.

Revision ID: 022
Revises: 021
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create compliance_rules table
    op.create_table(
        "compliance_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("funder", sa.String(100), nullable=False, index=True),
        sa.Column("mechanism", sa.String(50), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("rules", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create indexes for compliance_rules
    op.create_index("ix_compliance_rules_funder_mechanism", "compliance_rules", ["funder", "mechanism"])
    op.create_index("ix_compliance_rules_is_active", "compliance_rules", ["is_active"])
    op.create_index("ix_compliance_rules_is_system", "compliance_rules", ["is_system"])

    # Create compliance_scans table
    op.create_table(
        "compliance_scans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kanban_card_id", UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_set_id", UUID(as_uuid=True), sa.ForeignKey("compliance_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_content_hash", sa.String(64), nullable=True),
        sa.Column("results", JSONB, nullable=False, server_default="[]"),
        sa.Column("passed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("overall_status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("scanned_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scanned_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for compliance_scans
    op.create_index("ix_compliance_scans_kanban_card_id", "compliance_scans", ["kanban_card_id"])
    op.create_index("ix_compliance_scans_rule_set_id", "compliance_scans", ["rule_set_id"])
    op.create_index("ix_compliance_scans_document_type", "compliance_scans", ["document_type"])
    op.create_index("ix_compliance_scans_overall_status", "compliance_scans", ["overall_status"])
    op.create_index("ix_compliance_scans_scanned_at", "compliance_scans", ["scanned_at"])


def downgrade() -> None:
    # Drop compliance_scans indexes and table
    op.drop_index("ix_compliance_scans_scanned_at", table_name="compliance_scans")
    op.drop_index("ix_compliance_scans_overall_status", table_name="compliance_scans")
    op.drop_index("ix_compliance_scans_document_type", table_name="compliance_scans")
    op.drop_index("ix_compliance_scans_rule_set_id", table_name="compliance_scans")
    op.drop_index("ix_compliance_scans_kanban_card_id", table_name="compliance_scans")
    op.drop_table("compliance_scans")

    # Drop compliance_rules indexes and table
    op.drop_index("ix_compliance_rules_is_system", table_name="compliance_rules")
    op.drop_index("ix_compliance_rules_is_active", table_name="compliance_rules")
    op.drop_index("ix_compliance_rules_funder_mechanism", table_name="compliance_rules")
    op.drop_table("compliance_rules")
