"""Add checklist templates and application checklists tables.

Revision ID: 020
Revises: 019
Create Date: 2026-01-08
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Create checklist tables (idempotent)."""
    if table_exists("checklist_templates") and table_exists("application_checklists"):
        return

    # Create checklist_templates table
    if not table_exists("checklist_templates"):
        op.create_table(
            "checklist_templates",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("funder", sa.String(100), nullable=False),
            sa.Column("mechanism", sa.String(50), nullable=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("items", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("is_system", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_checklist_templates_funder", "checklist_templates", ["funder"])
        op.create_index("ix_checklist_templates_mechanism", "checklist_templates", ["mechanism"])
        op.create_index("ix_checklist_templates_is_system", "checklist_templates", ["is_system"])

    # Create application_checklists table
    if not table_exists("application_checklists"):
        op.create_table(
            "application_checklists",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("kanban_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("checklist_templates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("items", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("progress_percent", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_application_checklists_kanban_card_id", "application_checklists", ["kanban_card_id"])
        op.create_index("ix_application_checklists_template_id", "application_checklists", ["template_id"])

        # Create unique constraint - one checklist per template per card
        op.create_unique_constraint(
            "uq_application_checklist_card_template",
            "application_checklists",
            ["kanban_card_id", "template_id"]
        )


def downgrade() -> None:
    op.drop_constraint("uq_application_checklist_card_template", "application_checklists", type_="unique")
    op.drop_index("ix_application_checklists_template_id", table_name="application_checklists")
    op.drop_index("ix_application_checklists_kanban_card_id", table_name="application_checklists")
    op.drop_table("application_checklists")
    op.drop_index("ix_checklist_templates_is_system", table_name="checklist_templates")
    op.drop_index("ix_checklist_templates_mechanism", table_name="checklist_templates")
    op.drop_index("ix_checklist_templates_funder", table_name="checklist_templates")
    op.drop_table("checklist_templates")
