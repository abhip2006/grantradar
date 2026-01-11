"""Add document templates tables.

Revision ID: 010
Revises: 009
Create Date: 2025-01-07
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Create template categories and templates tables (idempotent)."""
    # Skip if tables already exist
    if table_exists("template_categories") and table_exists("templates"):
        return

    # Create template_categories table
    if not table_exists("template_categories"):
        op.create_table(
            "template_categories",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "name",
                sa.String(100),
                nullable=False,
                unique=True,
                comment="Category name (e.g., 'Abstract', 'Budget Justification')",
            ),
            sa.Column(
                "description",
                sa.Text(),
                nullable=True,
                comment="Description of the category",
            ),
            sa.Column(
                "display_order",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
                comment="Order for displaying categories",
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        # Create index for template_categories
        op.create_index(
            "ix_template_categories_name",
            "template_categories",
            ["name"],
        )
        op.create_index(
            "ix_template_categories_display_order",
            "template_categories",
            ["display_order"],
        )

    # Create templates table
    if not table_exists("templates"):
        op.create_table(
            "templates",
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
                nullable=True,
                comment="Owner user ID (null for system templates)",
            ),
            sa.Column(
                "category_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("template_categories.id", ondelete="SET NULL"),
                nullable=True,
                comment="Template category reference",
            ),
            sa.Column(
                "title",
                sa.String(255),
                nullable=False,
                comment="Template title",
            ),
            sa.Column(
                "description",
                sa.Text(),
                nullable=True,
                comment="Template description",
            ),
            sa.Column(
                "content",
                sa.Text(),
                nullable=False,
                comment="Template content with placeholders",
            ),
            sa.Column(
                "variables",
                postgresql.JSONB(),
                nullable=True,
                server_default=sa.text("'[]'::jsonb"),
                comment="Variable definitions: [{name, type, description, default}]",
            ),
            sa.Column(
                "is_public",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="Whether template is publicly visible",
            ),
            sa.Column(
                "is_system",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="System templates are read-only",
            ),
            sa.Column(
                "usage_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
                comment="Number of times template has been used",
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

        # Create indexes for templates
        op.create_index(
            "ix_templates_user_id",
            "templates",
            ["user_id"],
        )
        op.create_index(
            "ix_templates_category_id",
            "templates",
            ["category_id"],
        )
        op.create_index(
            "ix_templates_is_public",
            "templates",
            ["is_public"],
        )
        op.create_index(
            "ix_templates_is_system",
            "templates",
            ["is_system"],
        )
        op.create_index(
            "ix_templates_title",
            "templates",
            ["title"],
        )


def downgrade() -> None:
    """Remove template tables."""
    # Drop templates indexes and table
    op.drop_index("ix_templates_title", table_name="templates")
    op.drop_index("ix_templates_is_system", table_name="templates")
    op.drop_index("ix_templates_is_public", table_name="templates")
    op.drop_index("ix_templates_category_id", table_name="templates")
    op.drop_index("ix_templates_user_id", table_name="templates")
    op.drop_table("templates")

    # Drop template_categories indexes and table
    op.drop_index("ix_template_categories_display_order", table_name="template_categories")
    op.drop_index("ix_template_categories_name", table_name="template_categories")
    op.drop_table("template_categories")
