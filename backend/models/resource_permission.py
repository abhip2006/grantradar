"""
Resource Permission Models for Fine-Grained Access Control
SQLAlchemy ORM models for resource-level sharing and permission management.
"""

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models import Base, GUID

if TYPE_CHECKING:
    from backend.models import User


class ResourcePermission(Base):
    """
    Fine-grained resource-level permission.

    Allows sharing individual resources (grants, applications, documents)
    with specific users or teams at various permission levels.
    """

    __tablename__ = "resource_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the permission",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of resource: 'grant', 'application', 'document'",
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
        doc="ID of the shared resource",
    )

    # Who has access (one of these will be set)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="User who has been granted permission",
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        nullable=True,
        index=True,
        doc="Team that has been granted permission (future feature)",
    )

    permission_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Permission level: 'view', 'comment', 'edit', 'admin'",
    )

    granted_by: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User who granted the permission",
    )
    granted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the permission was granted",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the permission expires (null = never)",
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        doc="User with permission",
    )
    granter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[granted_by],
        doc="User who granted permission",
    )

    __table_args__ = (
        UniqueConstraint(
            "resource_type",
            "resource_id",
            "user_id",
            name="unique_user_resource_permission",
        ),
        Index("ix_resource_permissions_resource", "resource_type", "resource_id"),
        Index("ix_resource_permissions_user_resource", "user_id", "resource_type"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<ResourcePermission(id={self.id}, type='{self.resource_type}', "
            f"resource={self.resource_id}, user={self.user_id}, level='{self.permission_level}')>"
        )

    def is_expired(self) -> bool:
        """Check if the permission has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(self.expires_at.tzinfo) > self.expires_at


class ShareLink(Base):
    """
    Shareable link for resource access.

    Allows creating public or semi-public links that grant access to
    resources without requiring the recipient to be a registered user.
    """

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the share link",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of resource: 'grant', 'application', 'document'",
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
        doc="ID of the shared resource",
    )
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique token for the share link",
    )
    permission_level: Mapped[str] = mapped_column(
        String(20),
        default="view",
        nullable=False,
        doc="Permission level: 'view', 'comment', 'edit'",
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User who created the share link",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the share link was created",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the share link expires (null = never)",
    )

    max_uses: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Maximum number of times the link can be used (null = unlimited)",
    )
    use_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times the link has been used",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the share link is active",
    )

    # Optional password protection
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Hashed password for protected links",
    )

    # Optional name/description for the link
    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Optional name for the share link",
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        doc="User who created the share link",
    )

    __table_args__ = (
        Index("ix_share_links_resource", "resource_type", "resource_id"),
        Index("ix_share_links_created_by", "created_by"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<ShareLink(id={self.id}, type='{self.resource_type}', "
            f"resource={self.resource_id}, active={self.is_active})>"
        )

    def is_valid(self) -> bool:
        """Check if the share link is still valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.now(self.expires_at.tzinfo) > self.expires_at:
            return False
        if self.max_uses and self.use_count >= self.max_uses:
            return False
        return True

    def increment_use_count(self) -> None:
        """Increment the use count for this share link."""
        self.use_count += 1

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token for the share link."""
        return secrets.token_urlsafe(48)
