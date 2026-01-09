"""
Resource Permission Service
Service for managing fine-grained resource-level permissions and sharing.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from backend.models import Grant, GrantApplication, User
from backend.models.resource_permission import ResourcePermission, ShareLink
from backend.schemas.sharing import (
    PermissionLevel,
    ResourceType,
    ShareResourceRequest,
    CreateShareLinkRequest,
    UpdatePermissionRequest,
    UpdateShareLinkRequest,
)


logger = logging.getLogger(__name__)

# Password hashing context for share link passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ResourcePermissionService:
    """Service class for resource permission operations."""

    # Permission level hierarchy (higher index = more permissions)
    PERMISSION_HIERARCHY = ["view", "comment", "edit", "admin"]

    def __init__(self, db: AsyncSession):
        """
        Initialize the resource permission service.

        Args:
            db: Async database session.
        """
        self.db = db

    # =========================================================================
    # Share Resource Operations
    # =========================================================================

    async def share_resource(
        self,
        owner_id: UUID,
        resource_type: str,
        resource_id: UUID,
        data: ShareResourceRequest,
    ) -> ResourcePermission:
        """
        Share a resource with a user.

        Args:
            owner_id: ID of the resource owner.
            resource_type: Type of resource (grant, application, document).
            resource_id: ID of the resource.
            data: Share request data.

        Returns:
            Created ResourcePermission.

        Raises:
            NotFoundError: If resource or user not found.
            ValidationError: If invalid request data.
            AuthorizationError: If owner doesn't have permission.
        """
        # Verify resource exists and owner has admin permission
        await self._verify_resource_ownership(owner_id, resource_type, resource_id)

        # Find target user by ID or email
        target_user = await self._find_user(data.user_id, data.email)
        if not target_user:
            raise NotFoundError("User", str(data.user_id or data.email))

        # Cannot share with yourself
        if target_user.id == owner_id:
            raise ValidationError("Cannot share a resource with yourself")

        # Check for existing permission
        existing = await self._get_existing_permission(
            resource_type, resource_id, target_user.id
        )
        if existing:
            # Update existing permission if different level
            if existing.permission_level != data.permission_level.value:
                existing.permission_level = data.permission_level.value
                existing.expires_at = data.expires_at
                await self.db.commit()
                await self.db.refresh(existing)
                logger.info(
                    f"Updated permission: resource={resource_type}/{resource_id}, "
                    f"user={target_user.id}, level={data.permission_level}"
                )
            return existing

        # Create new permission
        permission = ResourcePermission(
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=target_user.id,
            permission_level=data.permission_level.value,
            granted_by=owner_id,
            expires_at=data.expires_at,
        )
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)

        logger.info(
            f"Created permission: resource={resource_type}/{resource_id}, "
            f"user={target_user.id}, level={data.permission_level}"
        )

        return permission

    async def revoke_permission(
        self,
        owner_id: UUID,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Revoke a user's permission on a resource.

        Args:
            owner_id: ID of the resource owner.
            resource_type: Type of resource.
            resource_id: ID of the resource.
            user_id: ID of user whose permission to revoke.

        Returns:
            True if permission was revoked.

        Raises:
            NotFoundError: If permission not found.
            AuthorizationError: If owner doesn't have permission.
        """
        # Verify ownership
        await self._verify_resource_ownership(owner_id, resource_type, resource_id)

        # Find and delete permission
        result = await self.db.execute(
            select(ResourcePermission).where(
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
                ResourcePermission.user_id == user_id,
            )
        )
        permission = result.scalar_one_or_none()
        if not permission:
            raise NotFoundError("Permission", f"{resource_type}/{resource_id}/{user_id}")

        await self.db.delete(permission)
        await self.db.commit()

        logger.info(
            f"Revoked permission: resource={resource_type}/{resource_id}, user={user_id}"
        )

        return True

    async def update_permission(
        self,
        owner_id: UUID,
        permission_id: UUID,
        data: UpdatePermissionRequest,
    ) -> ResourcePermission:
        """
        Update a resource permission.

        Args:
            owner_id: ID of the resource owner.
            permission_id: ID of the permission to update.
            data: Update data.

        Returns:
            Updated ResourcePermission.

        Raises:
            NotFoundError: If permission not found.
            AuthorizationError: If not authorized.
        """
        result = await self.db.execute(
            select(ResourcePermission)
            .options(selectinload(ResourcePermission.user))
            .where(ResourcePermission.id == permission_id)
        )
        permission = result.scalar_one_or_none()
        if not permission:
            raise NotFoundError("Permission", str(permission_id))

        # Verify ownership
        await self._verify_resource_ownership(
            owner_id, permission.resource_type, permission.resource_id
        )

        # Update fields
        if data.permission_level is not None:
            permission.permission_level = data.permission_level.value
        if data.expires_at is not None:
            permission.expires_at = data.expires_at

        await self.db.commit()
        await self.db.refresh(permission)

        return permission

    # =========================================================================
    # Share Link Operations
    # =========================================================================

    async def create_share_link(
        self,
        owner_id: UUID,
        data: CreateShareLinkRequest,
    ) -> ShareLink:
        """
        Create a shareable link for a resource.

        Args:
            owner_id: ID of the resource owner.
            data: Share link creation data.

        Returns:
            Created ShareLink.

        Raises:
            NotFoundError: If resource not found.
            AuthorizationError: If not authorized.
        """
        # Verify ownership
        await self._verify_resource_ownership(
            owner_id, data.resource_type.value, data.resource_id
        )

        # Hash password if provided
        password_hash = None
        if data.password:
            password_hash = pwd_context.hash(data.password)

        # Create share link
        share_link = ShareLink(
            resource_type=data.resource_type.value,
            resource_id=data.resource_id,
            token=ShareLink.generate_token(),
            permission_level=data.permission_level.value,
            created_by=owner_id,
            expires_at=data.expires_at,
            max_uses=data.max_uses,
            password_hash=password_hash,
            name=data.name,
        )
        self.db.add(share_link)
        await self.db.commit()
        await self.db.refresh(share_link)

        logger.info(
            f"Created share link: resource={data.resource_type}/{data.resource_id}, "
            f"token={share_link.token[:8]}..."
        )

        return share_link

    async def get_share_link_by_token(self, token: str) -> Optional[ShareLink]:
        """
        Get a share link by its token.

        Args:
            token: Share link token.

        Returns:
            ShareLink if found and valid, None otherwise.
        """
        result = await self.db.execute(
            select(ShareLink)
            .options(selectinload(ShareLink.creator))
            .where(ShareLink.token == token)
        )
        return result.scalar_one_or_none()

    async def access_via_share_link(
        self,
        token: str,
        password: Optional[str] = None,
    ) -> Tuple[bool, Optional[ShareLink], str]:
        """
        Attempt to access a resource via share link.

        Args:
            token: Share link token.
            password: Password if link is protected.

        Returns:
            Tuple of (success, share_link, message).
        """
        share_link = await self.get_share_link_by_token(token)
        if not share_link:
            return False, None, "Share link not found or invalid"

        if not share_link.is_valid():
            return False, share_link, "Share link has expired or reached maximum uses"

        # Check password if required
        if share_link.password_hash:
            if not password:
                return False, share_link, "Password required"
            if not pwd_context.verify(password, share_link.password_hash):
                return False, share_link, "Invalid password"

        # Increment use count
        share_link.increment_use_count()
        await self.db.commit()

        return True, share_link, "Access granted"

    async def list_share_links(
        self,
        owner_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ShareLink], int]:
        """
        List share links created by a user.

        Args:
            owner_id: ID of the link creator.
            resource_type: Optional filter by resource type.
            resource_id: Optional filter by resource ID.
            include_inactive: Whether to include inactive links.
            limit: Maximum results.
            offset: Skip first N results.

        Returns:
            Tuple of (share_links, total_count).
        """
        query = select(ShareLink).where(ShareLink.created_by == owner_id)

        if resource_type:
            query = query.where(ShareLink.resource_type == resource_type)
        if resource_id:
            query = query.where(ShareLink.resource_id == resource_id)
        if not include_inactive:
            query = query.where(ShareLink.is_active == True)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get results
        query = query.order_by(ShareLink.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        links = list(result.scalars().all())

        return links, total

    async def update_share_link(
        self,
        owner_id: UUID,
        link_id: UUID,
        data: UpdateShareLinkRequest,
    ) -> ShareLink:
        """
        Update a share link.

        Args:
            owner_id: ID of the link creator.
            link_id: ID of the share link.
            data: Update data.

        Returns:
            Updated ShareLink.

        Raises:
            NotFoundError: If link not found.
            AuthorizationError: If not authorized.
        """
        result = await self.db.execute(
            select(ShareLink).where(
                ShareLink.id == link_id,
                ShareLink.created_by == owner_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise NotFoundError("Share link", str(link_id))

        # Update fields
        if data.permission_level is not None:
            link.permission_level = data.permission_level.value
        if data.expires_at is not None:
            link.expires_at = data.expires_at
        if data.max_uses is not None:
            link.max_uses = data.max_uses
        if data.is_active is not None:
            link.is_active = data.is_active
        if data.name is not None:
            link.name = data.name

        await self.db.commit()
        await self.db.refresh(link)

        return link

    async def delete_share_link(self, owner_id: UUID, link_id: UUID) -> bool:
        """
        Delete a share link.

        Args:
            owner_id: ID of the link creator.
            link_id: ID of the share link.

        Returns:
            True if deleted.

        Raises:
            NotFoundError: If link not found.
        """
        result = await self.db.execute(
            select(ShareLink).where(
                ShareLink.id == link_id,
                ShareLink.created_by == owner_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise NotFoundError("Share link", str(link_id))

        await self.db.delete(link)
        await self.db.commit()

        return True

    # =========================================================================
    # Permission Checking Operations
    # =========================================================================

    async def check_permission(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        required_level: str = "view",
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if a user has the required permission level on a resource.

        Args:
            user_id: ID of the user.
            resource_type: Type of resource.
            resource_id: ID of the resource.
            required_level: Minimum required permission level.

        Returns:
            Tuple of (has_permission, actual_level, source).
        """
        # Check if user is the resource owner
        is_owner = await self._is_resource_owner(user_id, resource_type, resource_id)
        if is_owner:
            return True, "admin", "owner"

        # Check direct permission
        result = await self.db.execute(
            select(ResourcePermission).where(
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
                ResourcePermission.user_id == user_id,
            )
        )
        permission = result.scalar_one_or_none()

        if permission:
            # Check expiration
            if permission.is_expired():
                return False, None, None

            # Check level
            has_level = self._has_permission_level(
                permission.permission_level, required_level
            )
            return has_level, permission.permission_level, "direct"

        # No permission found
        return False, None, None

    async def list_resource_permissions(
        self,
        owner_id: UUID,
        resource_type: str,
        resource_id: UUID,
    ) -> List[ResourcePermission]:
        """
        List all permissions for a resource.

        Args:
            owner_id: ID of the resource owner.
            resource_type: Type of resource.
            resource_id: ID of the resource.

        Returns:
            List of ResourcePermissions.

        Raises:
            AuthorizationError: If not authorized.
        """
        # Verify ownership
        await self._verify_resource_ownership(owner_id, resource_type, resource_id)

        result = await self.db.execute(
            select(ResourcePermission)
            .options(
                selectinload(ResourcePermission.user),
                selectinload(ResourcePermission.granter),
            )
            .where(
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
            )
            .order_by(ResourcePermission.granted_at.desc())
        )
        return list(result.scalars().all())

    async def list_shared_with_me(
        self,
        user_id: UUID,
        resource_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ResourcePermission], int]:
        """
        List resources shared with a user.

        Args:
            user_id: ID of the user.
            resource_type: Optional filter by resource type.
            limit: Maximum results.
            offset: Skip first N results.

        Returns:
            Tuple of (permissions, total_count).
        """
        query = select(ResourcePermission).where(
            ResourcePermission.user_id == user_id
        )

        if resource_type:
            query = query.where(ResourcePermission.resource_type == resource_type)

        # Filter out expired permissions
        query = query.where(
            or_(
                ResourcePermission.expires_at.is_(None),
                ResourcePermission.expires_at > datetime.now(timezone.utc),
            )
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get results with related data
        query = query.options(selectinload(ResourcePermission.granter))
        query = query.order_by(ResourcePermission.granted_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        permissions = list(result.scalars().all())

        return permissions, total

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _find_user(
        self,
        user_id: Optional[UUID] = None,
        email: Optional[str] = None,
    ) -> Optional[User]:
        """Find a user by ID or email."""
        if not user_id and not email:
            raise ValidationError("Either user_id or email must be provided")

        if user_id:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
        else:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
        return result.scalar_one_or_none()

    async def _get_existing_permission(
        self,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
    ) -> Optional[ResourcePermission]:
        """Get existing permission for a user on a resource."""
        result = await self.db.execute(
            select(ResourcePermission).where(
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
                ResourcePermission.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _verify_resource_ownership(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
    ) -> bool:
        """
        Verify that a user owns a resource or has admin permission.

        Raises:
            NotFoundError: If resource not found.
            AuthorizationError: If user is not the owner.
        """
        is_owner = await self._is_resource_owner(user_id, resource_type, resource_id)
        if not is_owner:
            # Check for admin permission
            has_admin, _, _ = await self.check_permission(
                user_id, resource_type, resource_id, "admin"
            )
            if not has_admin:
                raise AuthorizationError(
                    "You don't have permission to manage sharing for this resource"
                )
        return True

    async def _is_resource_owner(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
    ) -> bool:
        """Check if a user owns a resource."""
        if resource_type == "grant":
            # Grants are typically matched to users via Match table
            # For now, check if user has a match for this grant
            from backend.models import Match
            result = await self.db.execute(
                select(Match).where(
                    Match.grant_id == resource_id,
                    Match.user_id == user_id,
                )
            )
            return result.scalar_one_or_none() is not None

        elif resource_type == "application":
            # Check if user owns the application
            result = await self.db.execute(
                select(GrantApplication).where(
                    GrantApplication.id == resource_id,
                    GrantApplication.user_id == user_id,
                )
            )
            return result.scalar_one_or_none() is not None

        elif resource_type == "document":
            # Documents are typically linked to applications
            # For now, return False and rely on explicit permissions
            return False

        return False

    def _has_permission_level(self, actual: str, required: str) -> bool:
        """Check if actual permission level meets required level."""
        try:
            actual_idx = self.PERMISSION_HIERARCHY.index(actual)
            required_idx = self.PERMISSION_HIERARCHY.index(required)
            return actual_idx >= required_idx
        except ValueError:
            return False

    async def get_resource_info(
        self,
        resource_type: str,
        resource_id: UUID,
    ) -> Optional[dict]:
        """Get basic info about a resource for display."""
        if resource_type == "grant":
            result = await self.db.execute(
                select(Grant).where(Grant.id == resource_id)
            )
            grant = result.scalar_one_or_none()
            if grant:
                return {
                    "title": grant.title,
                    "description": grant.description[:200] if grant.description else None,
                }

        elif resource_type == "application":
            result = await self.db.execute(
                select(GrantApplication).where(GrantApplication.id == resource_id)
            )
            app = result.scalar_one_or_none()
            if app:
                return {
                    "title": app.title or "Untitled Application",
                    "description": app.notes[:200] if app.notes else None,
                }

        return None
