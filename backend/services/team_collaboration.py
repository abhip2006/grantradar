"""Team collaboration service for grant assignments, comments, and coordination."""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    GrantAssignment,
    TeamComment,
    TeamNotification,
    TeamActivityLog,
    LabMember,
    User,
    Grant,
    InvitationStatus,
)
from backend.schemas.team_collaboration import (
    AssignmentCreate,
    AssignmentUpdate,
    CommentCreate,
    CommentUpdate,
    AssignmentRole,
    AssignmentStatus,
    TeamCollaborationNotificationType,
)
from backend.core.exceptions import NotFoundError, ValidationError, AuthorizationError


logger = logging.getLogger(__name__)


class TeamCollaborationService:
    """Service class for team collaboration operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the team collaboration service.

        Args:
            db: Async database session.
        """
        self.db = db

    # =========================================================================
    # Assignment Operations
    # =========================================================================

    async def create_assignment(
        self,
        lab_owner_id: UUID,
        assigned_by: UUID,
        data: AssignmentCreate,
    ) -> GrantAssignment:
        """
        Create a new grant assignment.

        Args:
            lab_owner_id: ID of the lab owner/PI.
            assigned_by: ID of the user making the assignment.
            data: Assignment creation data.

        Returns:
            Created GrantAssignment.

        Raises:
            NotFoundError: If grant or user not found.
            ValidationError: If user is not a team member.
        """
        # Verify the grant exists
        grant_result = await self.db.execute(select(Grant).where(Grant.id == data.grant_id))
        grant = grant_result.scalar_one_or_none()
        if not grant:
            raise NotFoundError("Grant", str(data.grant_id))

        # Verify the assignee is a valid team member
        await self._verify_team_member(lab_owner_id, data.assigned_to)

        # Check for existing assignment
        existing_result = await self.db.execute(
            select(GrantAssignment).where(
                GrantAssignment.grant_id == data.grant_id,
                GrantAssignment.assigned_to == data.assigned_to,
                GrantAssignment.lab_owner_id == lab_owner_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            raise ValidationError("This user is already assigned to this grant")

        # Create the assignment
        assignment = GrantAssignment(
            match_id=data.match_id,
            grant_id=data.grant_id,
            assigned_to=data.assigned_to,
            assigned_by=assigned_by,
            lab_owner_id=lab_owner_id,
            role=data.role.value,
            status=AssignmentStatus.ACTIVE.value,
            due_date=data.due_date,
            notes=data.notes,
        )
        self.db.add(assignment)

        # Get assignee info for notification
        assignee_result = await self.db.execute(select(User).where(User.id == data.assigned_to))
        assignee = assignee_result.scalar_one_or_none()

        # Create notification for assignee
        await self._create_notification(
            user_id=data.assigned_to,
            team_id=lab_owner_id,
            notification_type=TeamCollaborationNotificationType.ASSIGNMENT_CREATED.value,
            message=f"You have been assigned to '{grant.title}' as {data.role.value}",
            entity_type="assignment",
            entity_id=assignment.id,
            metadata={
                "grant_id": str(data.grant_id),
                "grant_title": grant.title,
                "assigned_by": str(assigned_by),
                "role": data.role.value,
            },
        )

        # Log activity
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=assigned_by,
            action_type="assignment_created",
            entity_type="assignment",
            entity_id=assignment.id,
            entity_name=f"{assignee.email if assignee else 'User'} assigned to {grant.title}",
            metadata={
                "grant_id": str(data.grant_id),
                "assignee_id": str(data.assigned_to),
                "role": data.role.value,
            },
        )

        await self.db.commit()
        await self.db.refresh(assignment)

        return assignment

    async def get_assignment(
        self,
        lab_owner_id: UUID,
        assignment_id: UUID,
    ) -> GrantAssignment:
        """
        Get an assignment by ID.

        Args:
            lab_owner_id: ID of the lab owner.
            assignment_id: ID of the assignment.

        Returns:
            GrantAssignment.

        Raises:
            NotFoundError: If assignment not found.
        """
        result = await self.db.execute(
            select(GrantAssignment)
            .options(
                selectinload(GrantAssignment.assignee),
                selectinload(GrantAssignment.assigner),
                selectinload(GrantAssignment.grant),
            )
            .where(
                GrantAssignment.id == assignment_id,
                GrantAssignment.lab_owner_id == lab_owner_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise NotFoundError("Assignment", str(assignment_id))
        return assignment

    async def get_grant_assignments(
        self,
        lab_owner_id: UUID,
        grant_id: Optional[UUID] = None,
        match_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[GrantAssignment], int]:
        """
        Get assignments for a grant or match.

        Args:
            lab_owner_id: ID of the lab owner.
            grant_id: Optional grant ID filter.
            match_id: Optional match ID filter.
            status: Optional status filter.
            limit: Maximum results.
            offset: Skip first N results.

        Returns:
            Tuple of (assignments list, total count).
        """
        query = (
            select(GrantAssignment)
            .options(
                selectinload(GrantAssignment.assignee),
                selectinload(GrantAssignment.assigner),
                selectinload(GrantAssignment.grant),
            )
            .where(GrantAssignment.lab_owner_id == lab_owner_id)
        )

        if grant_id:
            query = query.where(GrantAssignment.grant_id == grant_id)
        if match_id:
            query = query.where(GrantAssignment.match_id == match_id)
        if status:
            query = query.where(GrantAssignment.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(GrantAssignment.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        assignments = list(result.scalars().all())

        return assignments, total

    async def update_assignment(
        self,
        lab_owner_id: UUID,
        assignment_id: UUID,
        data: AssignmentUpdate,
        updated_by: UUID,
    ) -> GrantAssignment:
        """
        Update an assignment.

        Args:
            lab_owner_id: ID of the lab owner.
            assignment_id: ID of the assignment.
            data: Update data.
            updated_by: ID of the user making the update.

        Returns:
            Updated GrantAssignment.

        Raises:
            NotFoundError: If assignment not found.
        """
        assignment = await self.get_assignment(lab_owner_id, assignment_id)

        old_status = assignment.status
        old_role = assignment.role

        if data.role is not None:
            assignment.role = data.role.value
        if data.status is not None:
            assignment.status = data.status.value
        if data.due_date is not None:
            assignment.due_date = data.due_date
        if data.notes is not None:
            assignment.notes = data.notes

        # Create notification if status changed
        if data.status and data.status.value != old_status:
            notification_type = (
                TeamCollaborationNotificationType.ASSIGNMENT_COMPLETED.value
                if data.status == AssignmentStatus.COMPLETED
                else TeamCollaborationNotificationType.ASSIGNMENT_UPDATED.value
            )
            await self._create_notification(
                user_id=assignment.assigned_to,
                team_id=lab_owner_id,
                notification_type=notification_type,
                message=f"Assignment status changed to {data.status.value}",
                entity_type="assignment",
                entity_id=assignment.id,
                metadata={
                    "old_status": old_status,
                    "new_status": data.status.value,
                },
            )

        # Log activity
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=updated_by,
            action_type="assignment_updated",
            entity_type="assignment",
            entity_id=assignment.id,
            entity_name="Assignment updated",
            metadata={
                "old_status": old_status,
                "new_status": assignment.status,
                "old_role": old_role,
                "new_role": assignment.role,
            },
        )

        await self.db.commit()
        await self.db.refresh(assignment)

        return assignment

    async def delete_assignment(
        self,
        lab_owner_id: UUID,
        assignment_id: UUID,
        deleted_by: UUID,
    ) -> None:
        """
        Delete an assignment.

        Args:
            lab_owner_id: ID of the lab owner.
            assignment_id: ID of the assignment.
            deleted_by: ID of the user deleting the assignment.

        Raises:
            NotFoundError: If assignment not found.
        """
        assignment = await self.get_assignment(lab_owner_id, assignment_id)

        # Log activity before deletion
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=deleted_by,
            action_type="assignment_removed",
            entity_type="assignment",
            entity_id=assignment.id,
            entity_name="Assignment removed",
            metadata={
                "grant_id": str(assignment.grant_id),
                "assignee_id": str(assignment.assigned_to),
            },
        )

        await self.db.delete(assignment)
        await self.db.commit()

    # =========================================================================
    # Comment Operations
    # =========================================================================

    async def create_comment(
        self,
        lab_owner_id: UUID,
        grant_id: UUID,
        user_id: UUID,
        data: CommentCreate,
        match_id: Optional[UUID] = None,
    ) -> TeamComment:
        """
        Create a comment on a grant.

        Args:
            lab_owner_id: ID of the lab owner.
            grant_id: ID of the grant.
            user_id: ID of the user creating the comment.
            data: Comment creation data.
            match_id: Optional match ID.

        Returns:
            Created TeamComment.

        Raises:
            NotFoundError: If grant or parent comment not found.
        """
        # Verify grant exists
        grant_result = await self.db.execute(select(Grant).where(Grant.id == grant_id))
        grant = grant_result.scalar_one_or_none()
        if not grant:
            raise NotFoundError("Grant", str(grant_id))

        # Verify parent comment if provided
        if data.parent_id:
            parent_result = await self.db.execute(
                select(TeamComment).where(
                    TeamComment.id == data.parent_id,
                    TeamComment.lab_owner_id == lab_owner_id,
                )
            )
            parent = parent_result.scalar_one_or_none()
            if not parent:
                raise NotFoundError("Parent comment", str(data.parent_id))

        # Parse mentions from comment text
        mentions = await self._parse_mentions(data.comment_text, lab_owner_id)
        if data.mentions:
            mentions.extend([m.model_dump() for m in data.mentions])

        # Create the comment
        comment = TeamComment(
            match_id=match_id or data.parent_id,
            grant_id=grant_id,
            user_id=user_id,
            lab_owner_id=lab_owner_id,
            comment_text=data.comment_text,
            parent_id=data.parent_id,
            mentions=mentions if mentions else None,
        )
        self.db.add(comment)
        await self.db.flush()

        # Get author info
        author_result = await self.db.execute(select(User).where(User.id == user_id))
        author = author_result.scalar_one_or_none()

        # Create notifications for mentions
        for mention in mentions:
            mentioned_user_id = UUID(mention.get("user_id"))
            if mentioned_user_id != user_id:  # Don't notify self
                await self._create_notification(
                    user_id=mentioned_user_id,
                    team_id=lab_owner_id,
                    notification_type=TeamCollaborationNotificationType.MENTION.value,
                    message=f"{author.name or author.email} mentioned you in a comment on '{grant.title}'",
                    entity_type="comment",
                    entity_id=comment.id,
                    metadata={
                        "grant_id": str(grant_id),
                        "grant_title": grant.title,
                        "comment_preview": data.comment_text[:100],
                    },
                )

        # Notify parent comment author if this is a reply
        if data.parent_id and parent.user_id != user_id:
            await self._create_notification(
                user_id=parent.user_id,
                team_id=lab_owner_id,
                notification_type=TeamCollaborationNotificationType.COMMENT_REPLY.value,
                message=f"{author.name or author.email} replied to your comment on '{grant.title}'",
                entity_type="comment",
                entity_id=comment.id,
                metadata={
                    "grant_id": str(grant_id),
                    "grant_title": grant.title,
                    "reply_preview": data.comment_text[:100],
                },
            )

        # Log activity
        await self._log_activity(
            lab_owner_id=lab_owner_id,
            actor_id=user_id,
            action_type="comment_added",
            entity_type="comment",
            entity_id=comment.id,
            entity_name=f"Comment on {grant.title}",
            metadata={
                "grant_id": str(grant_id),
                "is_reply": data.parent_id is not None,
                "mention_count": len(mentions),
            },
        )

        await self.db.commit()
        await self.db.refresh(comment)

        return comment

    async def get_grant_comments(
        self,
        lab_owner_id: UUID,
        grant_id: UUID,
        include_replies: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[TeamComment], int]:
        """
        Get comments for a grant.

        Args:
            lab_owner_id: ID of the lab owner.
            grant_id: ID of the grant.
            include_replies: Whether to include nested replies.
            limit: Maximum results.
            offset: Skip first N results.

        Returns:
            Tuple of (comments list, total count).
        """
        # Get top-level comments only (parent_id is None)
        query = (
            select(TeamComment)
            .options(
                selectinload(TeamComment.author),
                selectinload(TeamComment.replies).selectinload(TeamComment.author),
            )
            .where(
                TeamComment.grant_id == grant_id,
                TeamComment.lab_owner_id == lab_owner_id,
                TeamComment.parent_id.is_(None),
            )
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(TeamComment.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        comments = list(result.scalars().all())

        return comments, total

    async def update_comment(
        self,
        lab_owner_id: UUID,
        comment_id: UUID,
        user_id: UUID,
        data: CommentUpdate,
    ) -> TeamComment:
        """
        Update a comment.

        Args:
            lab_owner_id: ID of the lab owner.
            comment_id: ID of the comment.
            user_id: ID of the user making the update.
            data: Update data.

        Returns:
            Updated TeamComment.

        Raises:
            NotFoundError: If comment not found.
            AuthorizationError: If user is not the comment author.
        """
        result = await self.db.execute(
            select(TeamComment)
            .options(selectinload(TeamComment.author))
            .where(
                TeamComment.id == comment_id,
                TeamComment.lab_owner_id == lab_owner_id,
            )
        )
        comment = result.scalar_one_or_none()
        if not comment:
            raise NotFoundError("Comment", str(comment_id))

        # Only the author can edit their comment
        if comment.user_id != user_id:
            raise AuthorizationError("You can only edit your own comments")

        # Parse new mentions
        mentions = await self._parse_mentions(data.comment_text, lab_owner_id)
        if data.mentions:
            mentions.extend([m.model_dump() for m in data.mentions])

        comment.comment_text = data.comment_text
        comment.mentions = mentions if mentions else None
        comment.is_edited = True

        await self.db.commit()
        await self.db.refresh(comment)

        return comment

    async def delete_comment(
        self,
        lab_owner_id: UUID,
        comment_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Delete a comment.

        Args:
            lab_owner_id: ID of the lab owner.
            comment_id: ID of the comment.
            user_id: ID of the user deleting.

        Raises:
            NotFoundError: If comment not found.
            AuthorizationError: If user is not authorized to delete.
        """
        result = await self.db.execute(
            select(TeamComment).where(
                TeamComment.id == comment_id,
                TeamComment.lab_owner_id == lab_owner_id,
            )
        )
        comment = result.scalar_one_or_none()
        if not comment:
            raise NotFoundError("Comment", str(comment_id))

        # Only the author or lab owner can delete
        if comment.user_id != user_id and lab_owner_id != user_id:
            raise AuthorizationError("You can only delete your own comments")

        await self.db.delete(comment)
        await self.db.commit()

    # =========================================================================
    # Workload Operations
    # =========================================================================

    async def get_member_workload(
        self,
        lab_owner_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Get workload summary for a team member.

        Args:
            lab_owner_id: ID of the lab owner.
            user_id: ID of the team member.

        Returns:
            Workload summary dictionary.
        """
        # Verify team member
        await self._verify_team_member(lab_owner_id, user_id)

        # Get user info
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        # Get assignments
        assignments_result = await self.db.execute(
            select(GrantAssignment)
            .options(selectinload(GrantAssignment.grant))
            .where(
                GrantAssignment.lab_owner_id == lab_owner_id,
                GrantAssignment.assigned_to == user_id,
            )
        )
        assignments = list(assignments_result.scalars().all())

        now = datetime.now(timezone.utc)
        week_from_now = now + timedelta(days=7)

        # Calculate stats
        active = [a for a in assignments if a.status == AssignmentStatus.ACTIVE.value]
        completed = [a for a in assignments if a.status == AssignmentStatus.COMPLETED.value]
        lead = [a for a in active if a.role == AssignmentRole.LEAD.value]
        contributor = [a for a in active if a.role == AssignmentRole.CONTRIBUTOR.value]
        reviewer = [a for a in active if a.role == AssignmentRole.REVIEWER.value]
        overdue = [a for a in active if a.due_date and a.due_date < now]
        due_this_week = [a for a in active if a.due_date and now <= a.due_date <= week_from_now]

        # Build assignment list
        assignment_list = []
        for a in active:
            days_until = None
            if a.due_date:
                days_until = (a.due_date - now).days
            assignment_list.append(
                {
                    "id": a.id,
                    "grant_id": a.grant_id,
                    "grant_title": a.grant.title if a.grant else "Unknown",
                    "role": a.role,
                    "status": a.status,
                    "due_date": a.due_date,
                    "days_until_due": days_until,
                }
            )

        return {
            "user_id": user_id,
            "user_name": user.name if user else None,
            "user_email": user.email if user else "Unknown",
            "total_assignments": len(assignments),
            "active_assignments": len(active),
            "completed_assignments": len(completed),
            "lead_count": len(lead),
            "contributor_count": len(contributor),
            "reviewer_count": len(reviewer),
            "overdue_count": len(overdue),
            "due_this_week": len(due_this_week),
            "assignments": assignment_list,
        }

    async def get_team_workload(
        self,
        lab_owner_id: UUID,
    ) -> dict:
        """
        Get workload summary for the entire team.

        Args:
            lab_owner_id: ID of the lab owner.

        Returns:
            Team workload summary dictionary.
        """
        # Get all active team members
        members_result = await self.db.execute(
            select(LabMember)
            .options(selectinload(LabMember.member_user))
            .where(
                LabMember.lab_owner_id == lab_owner_id,
                LabMember.invitation_status == InvitationStatus.ACCEPTED.value,
            )
        )
        members = list(members_result.scalars().all())

        # Get workload for each member
        member_workloads = []
        total_assignments = 0
        active_assignments = 0

        for member in members:
            if member.member_user_id:
                workload = await self.get_member_workload(lab_owner_id, member.member_user_id)
                member_workloads.append(workload)
                total_assignments += workload["total_assignments"]
                active_assignments += workload["active_assignments"]

        return {
            "lab_owner_id": lab_owner_id,
            "total_team_members": len(members),
            "total_assignments": total_assignments,
            "active_assignments": active_assignments,
            "members": member_workloads,
        }

    # =========================================================================
    # Deadline Conflict Operations
    # =========================================================================

    async def check_deadline_conflicts(
        self,
        lab_owner_id: UUID,
        conflict_window_days: int = 7,
    ) -> dict:
        """
        Check for deadline conflicts within the team.

        Args:
            lab_owner_id: ID of the lab owner.
            conflict_window_days: Days within which assignments are considered conflicting.

        Returns:
            Deadline conflicts summary.
        """
        # Get all active assignments with due dates
        result = await self.db.execute(
            select(GrantAssignment)
            .options(
                selectinload(GrantAssignment.assignee),
                selectinload(GrantAssignment.grant),
            )
            .where(
                GrantAssignment.lab_owner_id == lab_owner_id,
                GrantAssignment.status == AssignmentStatus.ACTIVE.value,
                GrantAssignment.due_date.isnot(None),
            )
            .order_by(GrantAssignment.due_date)
        )
        assignments = list(result.scalars().all())

        # Group by user and find conflicts
        user_assignments: dict[UUID, List[GrantAssignment]] = {}
        for a in assignments:
            if a.assigned_to not in user_assignments:
                user_assignments[a.assigned_to] = []
            user_assignments[a.assigned_to].append(a)

        conflicts = []
        for user_id, user_assigns in user_assignments.items():
            if len(user_assigns) < 2:
                continue

            # Sort by due date
            user_assigns.sort(key=lambda x: x.due_date)

            # Find overlapping deadlines within window
            for i, a1 in enumerate(user_assigns):
                conflicting = [a1]
                for a2 in user_assigns[i + 1 :]:
                    diff = abs((a2.due_date - a1.due_date).days)
                    if diff <= conflict_window_days:
                        conflicting.append(a2)
                    else:
                        break

                if len(conflicting) > 1:
                    # Calculate severity based on number of conflicts
                    num_conflicts = len(conflicting)
                    if num_conflicts >= 4:
                        severity = "critical"
                    elif num_conflicts >= 3:
                        severity = "high"
                    elif num_conflicts >= 2:
                        severity = "medium"
                    else:
                        severity = "low"

                    assignee = conflicting[0].assignee
                    conflicts.append(
                        {
                            "user_id": user_id,
                            "user_name": assignee.name if assignee else None,
                            "user_email": assignee.email if assignee else "Unknown",
                            "conflict_date": a1.due_date,
                            "conflicting_assignments": [
                                {
                                    "id": c.id,
                                    "grant_id": c.grant_id,
                                    "grant_title": c.grant.title if c.grant else "Unknown",
                                    "due_date": c.due_date,
                                    "role": c.role,
                                    "assigned_to": c.assigned_to,
                                    "assignee_name": c.assignee.name if c.assignee else None,
                                }
                                for c in conflicting
                            ],
                            "severity": severity,
                        }
                    )

        # Deduplicate conflicts (same assignments might appear multiple times)
        seen = set()
        unique_conflicts = []
        for c in conflicts:
            key = tuple(sorted(str(a["id"]) for a in c["conflicting_assignments"]))
            if key not in seen:
                seen.add(key)
                unique_conflicts.append(c)

        users_with_conflicts = len(set(c["user_id"] for c in unique_conflicts))

        return {
            "conflicts": unique_conflicts,
            "total_conflicts": len(unique_conflicts),
            "users_with_conflicts": users_with_conflicts,
            "conflict_window_days": conflict_window_days,
        }

    # =========================================================================
    # Activity Feed Operations
    # =========================================================================

    async def get_activity_feed(
        self,
        lab_owner_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """
        Get team activity feed.

        Args:
            lab_owner_id: ID of the lab owner.
            limit: Maximum results.
            offset: Skip first N results.

        Returns:
            Tuple of (activities list, total count).
        """
        query = (
            select(TeamActivityLog)
            .options(selectinload(TeamActivityLog.actor))
            .where(TeamActivityLog.lab_owner_id == lab_owner_id)
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(TeamActivityLog.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        activities = list(result.scalars().all())

        # Format activities
        activity_list = []
        for activity in activities:
            activity_list.append(
                {
                    "id": activity.id,
                    "activity_type": activity.action_type,
                    "actor_id": activity.actor_id,
                    "actor_name": activity.actor.name if activity.actor else None,
                    "actor_email": activity.actor.email if activity.actor else None,
                    "entity_type": activity.entity_type,
                    "entity_id": activity.entity_id,
                    "entity_name": activity.entity_name,
                    "grant_id": activity.metadata_.get("grant_id") if activity.metadata_ else None,
                    "grant_title": activity.metadata_.get("grant_title") if activity.metadata_ else None,
                    "metadata": activity.metadata_,
                    "created_at": activity.created_at,
                }
            )

        return activity_list, total

    # =========================================================================
    # Notification Operations
    # =========================================================================

    async def get_team_notifications(
        self,
        user_id: UUID,
        team_id: Optional[UUID] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[TeamNotification], int, int]:
        """
        Get team notifications for a user.

        Args:
            user_id: ID of the user.
            team_id: Optional team ID filter.
            unread_only: Only return unread notifications.
            limit: Maximum results.
            offset: Skip first N results.

        Returns:
            Tuple of (notifications list, total count, unread count).
        """
        query = select(TeamNotification).where(TeamNotification.user_id == user_id)

        if team_id:
            query = query.where(TeamNotification.team_id == team_id)
        if unread_only:
            query = query.where(not TeamNotification.is_read)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get unread count
        unread_query = select(func.count()).where(
            TeamNotification.user_id == user_id,
            not TeamNotification.is_read,
        )
        if team_id:
            unread_query = unread_query.where(TeamNotification.team_id == team_id)
        unread_result = await self.db.execute(unread_query)
        unread_count = unread_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(TeamNotification.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total, unread_count

    async def mark_notifications_read(
        self,
        user_id: UUID,
        notification_ids: Optional[List[UUID]] = None,
    ) -> int:
        """
        Mark notifications as read.

        Args:
            user_id: ID of the user.
            notification_ids: Specific notification IDs to mark, or None for all.

        Returns:
            Number of notifications marked as read.
        """
        now = datetime.now(timezone.utc)

        if notification_ids:
            result = await self.db.execute(
                select(TeamNotification).where(
                    TeamNotification.user_id == user_id,
                    TeamNotification.id.in_(notification_ids),
                    not TeamNotification.is_read,
                )
            )
        else:
            result = await self.db.execute(
                select(TeamNotification).where(
                    TeamNotification.user_id == user_id,
                    not TeamNotification.is_read,
                )
            )

        notifications = list(result.scalars().all())
        for notification in notifications:
            notification.is_read = True
            notification.read_at = now

        await self.db.commit()
        return len(notifications)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _verify_team_member(
        self,
        lab_owner_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Verify that a user is a team member.

        Args:
            lab_owner_id: ID of the lab owner.
            user_id: ID of the user to verify.

        Raises:
            ValidationError: If user is not a team member.
        """
        # Lab owner is always valid
        if user_id == lab_owner_id:
            return

        # Check if user is a team member
        result = await self.db.execute(
            select(LabMember).where(
                LabMember.lab_owner_id == lab_owner_id,
                LabMember.member_user_id == user_id,
                LabMember.invitation_status == InvitationStatus.ACCEPTED.value,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValidationError("User is not a member of this team")

    async def _parse_mentions(
        self,
        text: str,
        lab_owner_id: UUID,
    ) -> List[dict]:
        """
        Parse @mentions from comment text.

        Args:
            text: Comment text to parse.
            lab_owner_id: ID of the lab owner for member lookup.

        Returns:
            List of mention dictionaries.
        """
        # Find @mentions in text (format: @email or @name)
        mention_pattern = r"@(\S+@\S+\.\S+)"  # Simple email pattern
        matches = re.finditer(mention_pattern, text)

        mentions = []
        for match in matches:
            email = match.group(1).lower()

            # Look up user by email
            user_result = await self.db.execute(select(User).where(User.email == email))
            user = user_result.scalar_one_or_none()

            if user:
                # Verify they're a team member
                try:
                    await self._verify_team_member(lab_owner_id, user.id)
                    mentions.append(
                        {
                            "user_id": str(user.id),
                            "name": user.name,
                            "email": user.email,
                            "position": match.start(),
                        }
                    )
                except ValidationError:
                    pass  # Skip non-team members

        return mentions

    async def _create_notification(
        self,
        user_id: UUID,
        team_id: UUID,
        notification_type: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> TeamNotification:
        """
        Create a team notification.

        Args:
            user_id: ID of the user to notify.
            team_id: ID of the team.
            notification_type: Type of notification.
            message: Notification message.
            entity_type: Type of related entity.
            entity_id: ID of related entity.
            metadata: Additional metadata.

        Returns:
            Created TeamNotification.
        """
        notification = TeamNotification(
            user_id=user_id,
            team_id=team_id,
            notification_type=notification_type,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata,
        )
        self.db.add(notification)
        return notification

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
        Log a team activity.

        Args:
            lab_owner_id: ID of the lab owner.
            actor_id: ID of the user performing the action.
            action_type: Type of action.
            entity_type: Type of entity affected.
            entity_id: ID of the affected entity.
            entity_name: Name of the affected entity.
            metadata: Additional metadata.

        Returns:
            Created TeamActivityLog.
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
