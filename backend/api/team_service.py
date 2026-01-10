"""Team collaboration service layer for business logic."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    LabMember,
    TeamActivityLog,
    User,
    InvitationStatus,
)
from backend.schemas.team import (
    TeamInviteRequest,
    TeamMemberUpdate,
    TeamActivityFilters,
    MemberPermissions,
    MemberRole,
    ActivityType,
    EntityType,
)
from backend.core.exceptions import NotFoundError, ValidationError, ConflictError


# Invitation expiration period in days
INVITATION_EXPIRY_DAYS = 7


class TeamService:
    """Service class for team collaboration operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the team service.

        Args:
            db: Async database session.
        """
        self.db = db

    # =========================================================================
    # Invitation Operations
    # =========================================================================

    async def send_invitation(
        self,
        lab_owner_id: UUID,
        data: TeamInviteRequest,
    ) -> LabMember:
        """
        Send a team invitation to a new member.

        Args:
            lab_owner_id: ID of the lab owner sending the invitation.
            data: Invitation request data.

        Returns:
            Created LabMember record.

        Raises:
            ConflictError: If member is already invited.
            ValidationError: If trying to invite self.
        """
        # Get lab owner details
        owner_result = await self.db.execute(select(User).where(User.id == lab_owner_id))
        lab_owner = owner_result.scalar_one_or_none()
        if not lab_owner:
            raise NotFoundError("User", str(lab_owner_id))

        # Prevent self-invitation
        if lab_owner.email.lower() == data.email.lower():
            raise ValidationError("You cannot invite yourself to your own team")

        # Check if already invited
        existing_result = await self.db.execute(
            select(LabMember).where(
                LabMember.lab_owner_id == lab_owner_id,
                LabMember.member_email == data.email.lower(),
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            if existing.invitation_status == InvitationStatus.ACCEPTED.value:
                raise ConflictError("This person is already a member of your team")
            elif existing.invitation_status == InvitationStatus.PENDING.value:
                raise ConflictError("An invitation is already pending for this email address")
            elif existing.invitation_status in [
                InvitationStatus.DECLINED.value,
                InvitationStatus.EXPIRED.value,
                InvitationStatus.CANCELLED.value,
            ]:
                # Allow re-inviting someone who previously declined/expired
                await self.db.delete(existing)
                await self.db.flush()

        # Check if invited user exists
        user_result = await self.db.execute(select(User).where(User.email == data.email.lower()))
        existing_user = user_result.scalar_one_or_none()

        # Generate invitation token and expiry
        token = self._generate_invitation_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)

        # Get permissions based on role
        permissions = self._get_role_permissions(data.role)

        # Create lab member record
        member = LabMember(
            lab_owner_id=lab_owner_id,
            member_email=data.email.lower(),
            member_user_id=existing_user.id if existing_user else None,
            role=data.role.value,
            invitation_token=token,
            invitation_expires_at=expires_at,
            invitation_status=InvitationStatus.PENDING.value,
            permissions=permissions.model_dump(),
        )
        self.db.add(member)

        # Log activity
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=lab_owner_id,
            action_type=ActivityType.INVITATION_SENT.value,
            entity_type=EntityType.INVITATION.value,
            entity_id=member.id,
            entity_name=data.email,
            metadata={
                "role": data.role.value,
                "message": data.message,
                "expires_at": expires_at.isoformat(),
            },
        )

        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def resend_invitation(
        self,
        lab_owner_id: UUID,
        member_id: UUID,
    ) -> LabMember:
        """
        Resend an invitation with a new token.

        Args:
            lab_owner_id: ID of the lab owner.
            member_id: ID of the lab member record.

        Returns:
            Updated LabMember record.

        Raises:
            NotFoundError: If member not found.
            ValidationError: If invitation is not pending or expired.
        """
        member = await self._get_member_by_id(lab_owner_id, member_id)

        if member.invitation_status not in [
            InvitationStatus.PENDING.value,
            InvitationStatus.EXPIRED.value,
        ]:
            raise ValidationError(f"Cannot resend invitation with status '{member.invitation_status}'")

        # Generate new token and expiry
        member.invitation_token = self._generate_invitation_token()
        member.invitation_expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
        member.invitation_status = InvitationStatus.PENDING.value

        # Log activity
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=lab_owner_id,
            action_type=ActivityType.INVITATION_RESENT.value,
            entity_type=EntityType.INVITATION.value,
            entity_id=member.id,
            entity_name=member.member_email,
            metadata={
                "new_expires_at": member.invitation_expires_at.isoformat(),
            },
        )

        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def accept_invitation(
        self,
        token: str,
        user: Optional[User] = None,
    ) -> LabMember:
        """
        Accept an invitation using the token.

        Args:
            token: Invitation token.
            user: Currently logged in user (optional for token-based acceptance).

        Returns:
            Updated LabMember record.

        Raises:
            NotFoundError: If invitation not found.
            ValidationError: If invitation is expired or not pending.
        """
        # Find invitation by token
        result = await self.db.execute(
            select(LabMember).options(selectinload(LabMember.lab_owner)).where(LabMember.invitation_token == token)
        )
        member = result.scalar_one_or_none()

        if not member:
            raise NotFoundError("Invitation", token)

        # Check if pending
        if member.invitation_status != InvitationStatus.PENDING.value:
            raise ValidationError(f"Invitation has already been {member.invitation_status}")

        # Check expiration
        if member.invitation_expires_at and member.invitation_expires_at < datetime.now(timezone.utc):
            member.invitation_status = InvitationStatus.EXPIRED.value
            await self.db.commit()
            raise ValidationError("This invitation has expired")

        # Update member record
        member.invitation_status = InvitationStatus.ACCEPTED.value
        member.accepted_at = datetime.now(timezone.utc)
        member.invitation_token = None  # Clear token after use

        # Link user if provided
        if user:
            member.member_user_id = user.id
        else:
            # Try to find user by email
            user_result = await self.db.execute(select(User).where(User.email == member.member_email))
            existing_user = user_result.scalar_one_or_none()
            if existing_user:
                member.member_user_id = existing_user.id

        # Log activity
        await self._log_activity(
            lab_owner_id=member.lab_owner_id,
            actor_id=member.member_user_id,
            action_type=ActivityType.INVITATION_ACCEPTED.value,
            entity_type=EntityType.MEMBER.value,
            entity_id=member.id,
            entity_name=member.member_email,
            metadata={"role": member.role},
        )

        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def decline_invitation(
        self,
        token: str,
        reason: Optional[str] = None,
    ) -> LabMember:
        """
        Decline an invitation using the token.

        Args:
            token: Invitation token.
            reason: Optional reason for declining.

        Returns:
            Updated LabMember record.

        Raises:
            NotFoundError: If invitation not found.
            ValidationError: If invitation is not pending.
        """
        # Find invitation by token
        result = await self.db.execute(select(LabMember).where(LabMember.invitation_token == token))
        member = result.scalar_one_or_none()

        if not member:
            raise NotFoundError("Invitation", token)

        # Check if pending
        if member.invitation_status != InvitationStatus.PENDING.value:
            raise ValidationError(f"Invitation has already been {member.invitation_status}")

        # Update member record
        member.invitation_status = InvitationStatus.DECLINED.value
        member.declined_at = datetime.now(timezone.utc)
        member.invitation_token = None  # Clear token

        # Log activity
        await self._log_activity(
            lab_owner_id=member.lab_owner_id,
            actor_id=None,  # Declining user may not be logged in
            action_type=ActivityType.INVITATION_DECLINED.value,
            entity_type=EntityType.INVITATION.value,
            entity_id=member.id,
            entity_name=member.member_email,
            metadata={"reason": reason} if reason else None,
        )

        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def cancel_invitation(
        self,
        lab_owner_id: UUID,
        member_id: UUID,
    ) -> None:
        """
        Cancel a pending invitation.

        Args:
            lab_owner_id: ID of the lab owner.
            member_id: ID of the lab member record.

        Raises:
            NotFoundError: If member not found.
            ValidationError: If invitation is not pending.
        """
        member = await self._get_member_by_id(lab_owner_id, member_id)

        if member.invitation_status != InvitationStatus.PENDING.value:
            raise ValidationError(f"Cannot cancel invitation with status '{member.invitation_status}'")

        member.invitation_status = InvitationStatus.CANCELLED.value
        member.invitation_token = None

        # Log activity
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=lab_owner_id,
            action_type=ActivityType.INVITATION_CANCELLED.value,
            entity_type=EntityType.INVITATION.value,
            entity_id=member.id,
            entity_name=member.member_email,
            metadata=None,
        )

        await self.db.commit()

    # =========================================================================
    # Member Operations
    # =========================================================================

    async def list_members(
        self,
        lab_owner_id: UUID,
        include_pending: bool = True,
    ) -> List[LabMember]:
        """
        List all team members for a lab.

        Args:
            lab_owner_id: ID of the lab owner.
            include_pending: Include pending invitations.

        Returns:
            List of LabMember records.
        """
        query = (
            select(LabMember).options(selectinload(LabMember.member_user)).where(LabMember.lab_owner_id == lab_owner_id)
        )

        if not include_pending:
            query = query.where(LabMember.invitation_status == InvitationStatus.ACCEPTED.value)

        result = await self.db.execute(query.order_by(LabMember.invited_at.desc()))
        return list(result.scalars().all())

    async def get_member(
        self,
        lab_owner_id: UUID,
        member_id: UUID,
    ) -> LabMember:
        """
        Get a specific team member.

        Args:
            lab_owner_id: ID of the lab owner.
            member_id: ID of the lab member record.

        Returns:
            LabMember record.

        Raises:
            NotFoundError: If member not found.
        """
        return await self._get_member_by_id(lab_owner_id, member_id)

    async def update_member(
        self,
        lab_owner_id: UUID,
        member_id: UUID,
        data: TeamMemberUpdate,
    ) -> LabMember:
        """
        Update a team member's role and/or permissions.

        Args:
            lab_owner_id: ID of the lab owner.
            member_id: ID of the lab member record.
            data: Update data.

        Returns:
            Updated LabMember record.

        Raises:
            NotFoundError: If member not found.
        """
        member = await self._get_member_by_id(lab_owner_id, member_id)

        old_role = member.role
        old_permissions = member.permissions

        update_metadata = {}

        if data.role is not None:
            member.role = data.role.value
            update_metadata["old_role"] = old_role
            update_metadata["new_role"] = data.role.value

            # Update permissions based on new role if not explicitly provided
            if data.permissions is None:
                member.permissions = self._get_role_permissions(data.role).model_dump()

        if data.permissions is not None:
            member.permissions = data.permissions.model_dump()
            update_metadata["permissions_updated"] = True

        # Log activity for role change
        if "new_role" in update_metadata:
            await self._log_activity(
                lab_owner_id=lab_owner_id,
                actor_id=lab_owner_id,
                action_type=ActivityType.ROLE_CHANGED.value,
                entity_type=EntityType.MEMBER.value,
                entity_id=member.id,
                entity_name=member.member_email,
                metadata=update_metadata,
            )

        # Log activity for permissions change
        if data.permissions is not None:
            await self._log_activity(
                lab_owner_id=lab_owner_id,
                actor_id=lab_owner_id,
                action_type=ActivityType.PERMISSIONS_UPDATED.value,
                entity_type=EntityType.PERMISSION.value,
                entity_id=member.id,
                entity_name=member.member_email,
                metadata={
                    "old_permissions": old_permissions,
                    "new_permissions": member.permissions,
                },
            )

        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def remove_member(
        self,
        lab_owner_id: UUID,
        member_id: UUID,
    ) -> None:
        """
        Remove a team member.

        Args:
            lab_owner_id: ID of the lab owner.
            member_id: ID of the lab member record.

        Raises:
            NotFoundError: If member not found.
        """
        member = await self._get_member_by_id(lab_owner_id, member_id)

        # Log activity before deletion
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=lab_owner_id,
            action_type=ActivityType.MEMBER_REMOVED.value,
            entity_type=EntityType.MEMBER.value,
            entity_id=member.id,
            entity_name=member.member_email,
            metadata={"role": member.role, "status": member.invitation_status},
        )

        await self.db.delete(member)
        await self.db.commit()

    # =========================================================================
    # Activity Operations
    # =========================================================================

    async def log_activity(
        self,
        lab_owner_id: UUID,
        actor_id: Optional[UUID],
        action_type: str,
        entity_type: str,
        entity_id: Optional[UUID] = None,
        entity_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> TeamActivityLog:
        """
        Log a team activity. Public interface for logging.

        Args:
            lab_owner_id: ID of the lab owner.
            actor_id: ID of the user performing the action.
            action_type: Type of action.
            entity_type: Type of entity affected.
            entity_id: ID of the affected entity.
            entity_name: Name of the affected entity.
            metadata: Additional metadata.

        Returns:
            Created TeamActivityLog record.
        """
        return await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            metadata=metadata,
        )

    async def get_activities(
        self,
        lab_owner_id: UUID,
        filters: Optional[TeamActivityFilters] = None,
    ) -> tuple[List[TeamActivityLog], int]:
        """
        Get team activities with optional filtering.

        Args:
            lab_owner_id: ID of the lab owner.
            filters: Optional filters for querying.

        Returns:
            Tuple of (activities list, total count).
        """
        if filters is None:
            filters = TeamActivityFilters()

        # Build base query
        query = (
            select(TeamActivityLog)
            .options(selectinload(TeamActivityLog.actor))
            .where(TeamActivityLog.lab_owner_id == lab_owner_id)
        )

        # Apply filters
        if filters.action_types:
            action_values = [at.value for at in filters.action_types]
            query = query.where(TeamActivityLog.action_type.in_(action_values))

        if filters.entity_types:
            entity_values = [et.value for et in filters.entity_types]
            query = query.where(TeamActivityLog.entity_type.in_(entity_values))

        if filters.actor_id:
            query = query.where(TeamActivityLog.actor_id == filters.actor_id)

        if filters.entity_id:
            query = query.where(TeamActivityLog.entity_id == filters.entity_id)

        if filters.from_date:
            query = query.where(TeamActivityLog.created_at >= filters.from_date)

        if filters.to_date:
            query = query.where(TeamActivityLog.created_at <= filters.to_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(TeamActivityLog.created_at.desc()).offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)
        activities = list(result.scalars().all())

        return activities, total

    # =========================================================================
    # Stats Operations
    # =========================================================================

    async def get_team_stats(self, lab_owner_id: UUID) -> dict:
        """
        Get team statistics for a lab owner.

        Args:
            lab_owner_id: ID of the lab owner.

        Returns:
            Dictionary of team statistics.
        """
        # Get all members
        members_result = await self.db.execute(select(LabMember).where(LabMember.lab_owner_id == lab_owner_id))
        members = members_result.scalars().all()

        # Calculate stats
        total = len(members)
        active = sum(1 for m in members if m.invitation_status == InvitationStatus.ACCEPTED.value)
        pending = sum(1 for m in members if m.invitation_status == InvitationStatus.PENDING.value)
        declined = sum(1 for m in members if m.invitation_status == InvitationStatus.DECLINED.value)
        expired = sum(1 for m in members if m.invitation_status == InvitationStatus.EXPIRED.value)

        # Count by role (only accepted members)
        members_by_role = {}
        for member in members:
            if member.invitation_status == InvitationStatus.ACCEPTED.value:
                role = member.role
                members_by_role[role] = members_by_role.get(role, 0) + 1

        # Get recent activity count (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        activity_result = await self.db.execute(
            select(func.count())
            .select_from(TeamActivityLog)
            .where(
                and_(
                    TeamActivityLog.lab_owner_id == lab_owner_id,
                    TeamActivityLog.created_at >= week_ago,
                )
            )
        )
        recent_activity_count = activity_result.scalar() or 0

        return {
            "total_members": total,
            "active_members": active,
            "pending_invitations": pending,
            "declined_invitations": declined,
            "expired_invitations": expired,
            "members_by_role": members_by_role,
            "recent_activity_count": recent_activity_count,
        }

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def bulk_invite(
        self,
        lab_owner_id: UUID,
        invitations: List[dict],
    ) -> dict:
        """
        Send multiple invitations at once.

        Args:
            lab_owner_id: ID of the lab owner sending the invitations.
            invitations: List of invitation dicts containing:
                - email: Email address to invite
                - role: MemberRole value (optional, defaults to MEMBER)
                - message: Personal message (optional)
                - permission_template_id: UUID of permission template (optional)

        Returns:
            Dict with successful and failed invitations:
            {
                "successful": [{"email": ..., "member_id": ..., "role": ...}],
                "failed": [{"email": ..., "error": ...}]
            }
        """
        # Get lab owner details
        owner_result = await self.db.execute(select(User).where(User.id == lab_owner_id))
        lab_owner = owner_result.scalar_one_or_none()
        if not lab_owner:
            raise NotFoundError("User", str(lab_owner_id))

        successful = []
        failed = []

        for invite in invitations:
            email = invite.get("email", "").lower().strip()
            role_str = invite.get("role", MemberRole.MEMBER.value)
            message = invite.get("message")
            template_id = invite.get("permission_template_id")

            # Validate email
            if not email or "@" not in email:
                failed.append(
                    {
                        "email": email or "(empty)",
                        "error": "Invalid email address",
                    }
                )
                continue

            # Prevent self-invitation
            if lab_owner.email.lower() == email:
                failed.append(
                    {
                        "email": email,
                        "error": "Cannot invite yourself",
                    }
                )
                continue

            try:
                # Parse role
                role = MemberRole(role_str) if isinstance(role_str, str) else role_str

                # Check if already invited
                existing_result = await self.db.execute(
                    select(LabMember).where(
                        LabMember.lab_owner_id == lab_owner_id,
                        LabMember.member_email == email,
                    )
                )
                existing = existing_result.scalar_one_or_none()

                if existing:
                    if existing.invitation_status == InvitationStatus.ACCEPTED.value:
                        failed.append(
                            {
                                "email": email,
                                "error": "Already a team member",
                            }
                        )
                        continue
                    elif existing.invitation_status == InvitationStatus.PENDING.value:
                        failed.append(
                            {
                                "email": email,
                                "error": "Invitation already pending",
                            }
                        )
                        continue
                    else:
                        # Remove old declined/expired/cancelled invitation
                        await self.db.delete(existing)
                        await self.db.flush()

                # Check if invited user exists
                user_result = await self.db.execute(select(User).where(User.email == email))
                existing_user = user_result.scalar_one_or_none()

                # Generate invitation token and expiry
                token = self._generate_invitation_token()
                expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)

                # Get permissions based on role or template
                permissions = self._get_role_permissions(role)

                # Create lab member record
                member = LabMember(
                    lab_owner_id=lab_owner_id,
                    member_email=email,
                    member_user_id=existing_user.id if existing_user else None,
                    role=role.value,
                    invitation_token=token,
                    invitation_expires_at=expires_at,
                    invitation_status=InvitationStatus.PENDING.value,
                    permissions=permissions.model_dump(),
                    permission_template_id=template_id,
                )
                self.db.add(member)
                await self.db.flush()

                # Log activity
                await self._log_activity(
                    lab_owner_id=lab_owner_id,
                    actor_id=lab_owner_id,
                    action_type=ActivityType.INVITATION_SENT.value,
                    entity_type=EntityType.INVITATION.value,
                    entity_id=member.id,
                    entity_name=email,
                    metadata={
                        "role": role.value,
                        "message": message,
                        "expires_at": expires_at.isoformat(),
                        "bulk_invite": True,
                    },
                )

                successful.append(
                    {
                        "email": email,
                        "member_id": str(member.id),
                        "role": role.value,
                    }
                )

            except ValueError:
                failed.append(
                    {
                        "email": email,
                        "error": f"Invalid role: {role_str}",
                    }
                )
            except Exception as e:
                failed.append(
                    {
                        "email": email,
                        "error": str(e),
                    }
                )

        # Commit all successful invitations
        if successful:
            await self.db.commit()

        return {
            "successful": successful,
            "failed": failed,
        }

    async def search_members(
        self,
        lab_owner_id: UUID,
        query: str,
        include_pending: bool = True,
    ) -> List[LabMember]:
        """
        Search team members by email or name.

        Args:
            lab_owner_id: ID of the lab owner.
            query: Search query string.
            include_pending: Include pending invitations in results.

        Returns:
            List of matching LabMember records.
        """
        if not query or len(query.strip()) < 2:
            return []

        search_query = f"%{query.strip().lower()}%"

        # Build query
        stmt = (
            select(LabMember).options(selectinload(LabMember.member_user)).where(LabMember.lab_owner_id == lab_owner_id)
        )

        if not include_pending:
            stmt = stmt.where(LabMember.invitation_status == InvitationStatus.ACCEPTED.value)

        # Search by email or user name (if linked)
        stmt = stmt.where(func.lower(LabMember.member_email).like(search_query))

        result = await self.db.execute(stmt.order_by(LabMember.member_email))
        members_by_email = list(result.scalars().all())

        # Also search by user name if they have linked users
        stmt_name = (
            select(LabMember)
            .options(selectinload(LabMember.member_user))
            .join(User, LabMember.member_user_id == User.id)
            .where(
                and_(
                    LabMember.lab_owner_id == lab_owner_id,
                    func.lower(User.name).like(search_query),
                )
            )
        )

        if not include_pending:
            stmt_name = stmt_name.where(LabMember.invitation_status == InvitationStatus.ACCEPTED.value)

        result_name = await self.db.execute(stmt_name)
        members_by_name = list(result_name.scalars().all())

        # Combine and deduplicate results
        seen_ids = set()
        combined = []
        for member in members_by_email + members_by_name:
            if member.id not in seen_ids:
                seen_ids.add(member.id)
                combined.append(member)

        return combined

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _generate_invitation_token(self) -> str:
        """
        Generate a secure invitation token.

        Returns:
            A URL-safe 32-byte token (43 characters).
        """
        return secrets.token_urlsafe(32)

    def _get_role_permissions(self, role: MemberRole) -> MemberPermissions:
        """
        Get default permissions for a role.

        Args:
            role: Member role.

        Returns:
            MemberPermissions for the role.
        """
        if role == MemberRole.ADMIN:
            return MemberPermissions(
                can_view=True,
                can_edit=True,
                can_create=True,
                can_delete=True,
                can_invite=True,
            )
        elif role == MemberRole.MEMBER:
            return MemberPermissions(
                can_view=True,
                can_edit=True,
                can_create=True,
                can_delete=False,
                can_invite=False,
            )
        else:  # VIEWER
            return MemberPermissions(
                can_view=True,
                can_edit=False,
                can_create=False,
                can_delete=False,
                can_invite=False,
            )

    async def _get_member_by_id(
        self,
        lab_owner_id: UUID,
        member_id: UUID,
    ) -> LabMember:
        """
        Get a lab member by ID with ownership check.

        Args:
            lab_owner_id: ID of the lab owner.
            member_id: ID of the lab member.

        Returns:
            LabMember record.

        Raises:
            NotFoundError: If not found or ownership mismatch.
        """
        result = await self.db.execute(
            select(LabMember)
            .options(selectinload(LabMember.member_user))
            .where(
                LabMember.id == member_id,
                LabMember.lab_owner_id == lab_owner_id,
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            raise NotFoundError("Team member", str(member_id))

        return member

    async def _log_activity(
        self,
        lab_owner_id: UUID,
        actor_id: Optional[UUID],
        action_type: str,
        entity_type: str,
        entity_id: Optional[UUID] = None,
        entity_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> TeamActivityLog:
        """
        Create a team activity log entry.

        Args:
            lab_owner_id: ID of the lab owner.
            actor_id: ID of the user performing the action.
            action_type: Type of action.
            entity_type: Type of entity affected.
            entity_id: ID of the affected entity.
            entity_name: Name of the affected entity.
            metadata: Additional metadata.

        Returns:
            Created TeamActivityLog record.
        """
        activity = TeamActivityLog(
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            metadata_=metadata,
        )
        self.db.add(activity)
        return activity
