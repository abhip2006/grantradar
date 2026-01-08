"""Add custom fields tables.

Revision ID: 017
Revises: 016
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create custom field definitions table
    op.create_table(
        "custom_field_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(30), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("show_in_card", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_user_field_name"),
    )
    op.create_index("ix_custom_field_definitions_user_id", "custom_field_definitions", ["user_id"])

    # Create custom field values table
    op.create_table(
        "custom_field_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("custom_field_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("application_id", "field_id", name="uq_app_field"),
    )
    op.create_index("ix_custom_field_values_application_id", "custom_field_values", ["application_id"])
    op.create_index("ix_custom_field_values_field_id", "custom_field_values", ["field_id"])


def downgrade() -> None:
    op.drop_index("ix_custom_field_values_field_id", table_name="custom_field_values")
    op.drop_index("ix_custom_field_values_application_id", table_name="custom_field_values")
    op.drop_table("custom_field_values")
    op.drop_index("ix_custom_field_definitions_user_id", table_name="custom_field_definitions")
    op.drop_table("custom_field_definitions")
