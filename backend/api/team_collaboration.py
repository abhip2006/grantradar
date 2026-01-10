"""Team collaboration API endpoints for grant assignments, comments, and coordination."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.services.team_collaboration import TeamCollaborationService
from backend.schemas.team_collaboration import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
    AssignmentListResponse,
    AssigneeInfo,
    GrantInfo,
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentListResponse,
    CommentAuthorInfo,
    WorkloadSummary,
    TeamWorkloadResponse,
    ActivityFeedResponse,
    ActivityItem,
    DeadlineConflictsResponse,
    DeadlineConflict,
    DeadlineAssignment,
    TeamNotificationResponse,
    TeamNotificationListResponse,
    MarkNotificationsReadRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/team",
    tags=["Team Collaboration"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def _build_assignment_response(assignment) -> AssignmentResponse:
    """Build an AssignmentResponse from a GrantAssignment model."""
    assignee = None
    if assignment.assignee:
        assignee = AssigneeInfo(
            id=assignment.assignee.id,
            name=assignment.assignee.name,
            email=assignment.assignee.email,
        )

    assigner = None
    if assignment.assigner:
        assigner = AssigneeInfo(
            id=assignment.assigner.id,
            name=assignment.assigner.name,
            email=assignment.assigner.email,
        )

    grant = None
    if assignment.grant:
        grant = GrantInfo(
            id=assignment.grant.id,
            title=assignment.grant.title,
            agency=assignment.grant.agency,
            deadline=assignment.grant.deadline,
        )

    return AssignmentResponse(
        id=assignment.id,
        match_id=assignment.match_id,
        grant_id=assignment.grant_id,
        assigned_to=assignment.assigned_to,
        assigned_by=assignment.assigned_by,
        lab_owner_id=assignment.lab_owner_id,
        role=assignment.role,
        status=assignment.status,
        due_date=assignment.due_date,
        notes=assignment.notes,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        assignee=assignee,
        assigner=assigner,
        grant=grant,
    )


def _build_comment_response(comment, include_replies: bool = False) -> CommentResponse:
    """Build a CommentResponse from a TeamComment model."""
    author = None
    if comment.author:
        author = CommentAuthorInfo(
            id=comment.author.id,
            name=comment.author.name,
            email=comment.author.email,
        )

    replies = None
    reply_count = 0
    if hasattr(comment, "replies") and comment.replies:
        reply_count = len(comment.replies)
        if include_replies:
            replies = [_build_comment_response(r, include_replies=False) for r in comment.replies]

    return CommentResponse(
        id=comment.id,
        match_id=comment.match_id,
        grant_id=comment.grant_id,
        user_id=comment.user_id,
        lab_owner_id=comment.lab_owner_id,
        comment_text=comment.comment_text,
        parent_id=comment.parent_id,
        mentions=comment.mentions,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=author,
        reply_count=reply_count,
        replies=replies,
    )


# =============================================================================
# Assignment Endpoints
# =============================================================================


@router.post(
    "/grants/{match_id}/assign",
    response_model=AssignmentResponse,
    status_code=201,
    summary="Assign grant to team member",
    description="Assign a grant to a team member with a specific role.",
)
async def assign_grant(
    match_id: UUID,
    data: AssignmentCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> AssignmentResponse:
    """
    Assign a grant to a team member.

    Creates an assignment linking a team member to a grant with a specified role
    (lead, contributor, reviewer) and optional due date.
    """
    # Override match_id from path
    data.match_id = match_id

    service = TeamCollaborationService(db)
    assignment = await service.create_assignment(
        lab_owner_id=current_user.id,
        assigned_by=current_user.id,
        data=data,
    )

    logger.info(f"Grant assigned: grant_id={data.grant_id}, assignee={data.assigned_to}, role={data.role.value}")

    return _build_assignment_response(assignment)


@router.get(
    "/grants/{match_id}/assignments",
    response_model=AssignmentListResponse,
    summary="Get grant assignments",
    description="Get all assignments for a specific grant or match.",
)
async def get_grant_assignments(
    match_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    grant_id: Optional[UUID] = Query(None, description="Filter by grant ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
) -> AssignmentListResponse:
    """
    Get all assignments for a grant or match.

    Returns assignments with assignee information, role, status, and due dates.
    """
    service = TeamCollaborationService(db)
    assignments, total = await service.get_grant_assignments(
        lab_owner_id=current_user.id,
        match_id=match_id,
        grant_id=grant_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return AssignmentListResponse(
        assignments=[_build_assignment_response(a) for a in assignments],
        total=total,
        has_more=(offset + len(assignments)) < total,
    )


@router.patch(
    "/assignments/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Update assignment",
    description="Update an assignment's role, status, due date, or notes.",
)
async def update_assignment(
    assignment_id: UUID,
    data: AssignmentUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> AssignmentResponse:
    """
    Update a grant assignment.

    Can update role, status, due date, and notes.
    """
    service = TeamCollaborationService(db)
    assignment = await service.update_assignment(
        lab_owner_id=current_user.id,
        assignment_id=assignment_id,
        data=data,
        updated_by=current_user.id,
    )

    logger.info(f"Assignment updated: id={assignment_id}")

    return _build_assignment_response(assignment)


@router.delete(
    "/assignments/{assignment_id}",
    status_code=204,
    summary="Remove assignment",
    description="Remove a team member's assignment from a grant.",
)
async def remove_assignment(
    assignment_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Remove a grant assignment.

    This action cannot be undone.
    """
    service = TeamCollaborationService(db)
    await service.delete_assignment(
        lab_owner_id=current_user.id,
        assignment_id=assignment_id,
        deleted_by=current_user.id,
    )

    logger.info(f"Assignment removed: id={assignment_id}")


# =============================================================================
# Workload Endpoints
# =============================================================================


@router.get(
    "/members/{user_id}/workload",
    response_model=WorkloadSummary,
    summary="Get member workload",
    description="Get a team member's current workload and assignment summary.",
)
async def get_member_workload(
    user_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> WorkloadSummary:
    """
    Get workload summary for a team member.

    Returns assignment counts by role and status, overdue items, and upcoming deadlines.
    """
    service = TeamCollaborationService(db)
    workload = await service.get_member_workload(
        lab_owner_id=current_user.id,
        user_id=user_id,
    )

    return WorkloadSummary(**workload)


@router.get(
    "/workload",
    response_model=TeamWorkloadResponse,
    summary="Get team workload",
    description="Get workload overview for the entire team.",
)
async def get_team_workload(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> TeamWorkloadResponse:
    """
    Get workload summary for the entire team.

    Returns workload per team member with totals across the team.
    """
    service = TeamCollaborationService(db)
    workload = await service.get_team_workload(lab_owner_id=current_user.id)

    return TeamWorkloadResponse(
        lab_owner_id=workload["lab_owner_id"],
        total_team_members=workload["total_team_members"],
        total_assignments=workload["total_assignments"],
        active_assignments=workload["active_assignments"],
        members=[WorkloadSummary(**m) for m in workload["members"]],
    )


# =============================================================================
# Comment Endpoints
# =============================================================================


@router.post(
    "/grants/{match_id}/comments",
    response_model=CommentResponse,
    status_code=201,
    summary="Add comment to grant",
    description="Add a comment to a grant. Supports @mentions and threading.",
)
async def add_comment(
    match_id: UUID,
    data: CommentCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    grant_id: UUID = Query(..., description="Grant ID to comment on"),
) -> CommentResponse:
    """
    Add a comment to a grant.

    Supports @mentions (using @email format) and threaded replies.
    Mentioned users will receive notifications.
    """
    service = TeamCollaborationService(db)
    comment = await service.create_comment(
        lab_owner_id=current_user.id,
        grant_id=grant_id,
        user_id=current_user.id,
        data=data,
        match_id=match_id,
    )

    logger.info(f"Comment added: grant_id={grant_id}, user={current_user.id}")

    return _build_comment_response(comment, include_replies=False)


@router.get(
    "/grants/{match_id}/comments",
    response_model=CommentListResponse,
    summary="Get grant comments",
    description="Get all comments for a grant with optional threading.",
)
async def get_grant_comments(
    match_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    grant_id: UUID = Query(..., description="Grant ID to get comments for"),
    include_replies: bool = Query(True, description="Include nested replies"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
) -> CommentListResponse:
    """
    Get comments for a grant.

    Returns top-level comments with optional nested replies.
    """
    service = TeamCollaborationService(db)
    comments, total = await service.get_grant_comments(
        lab_owner_id=current_user.id,
        grant_id=grant_id,
        include_replies=include_replies,
        limit=limit,
        offset=offset,
    )

    return CommentListResponse(
        comments=[_build_comment_response(c, include_replies=include_replies) for c in comments],
        total=total,
        has_more=(offset + len(comments)) < total,
    )


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Update comment",
    description="Update a comment's text. Only the author can edit.",
)
async def update_comment(
    comment_id: UUID,
    data: CommentUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> CommentResponse:
    """
    Update a comment.

    Only the comment author can edit their comment.
    The comment will be marked as edited.
    """
    service = TeamCollaborationService(db)
    comment = await service.update_comment(
        lab_owner_id=current_user.id,
        comment_id=comment_id,
        user_id=current_user.id,
        data=data,
    )

    logger.info(f"Comment updated: id={comment_id}")

    return _build_comment_response(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=204,
    summary="Delete comment",
    description="Delete a comment. Only the author or lab owner can delete.",
)
async def delete_comment(
    comment_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Delete a comment.

    Only the comment author or lab owner can delete comments.
    Deleting a parent comment will also delete all replies.
    """
    service = TeamCollaborationService(db)
    await service.delete_comment(
        lab_owner_id=current_user.id,
        comment_id=comment_id,
        user_id=current_user.id,
    )

    logger.info(f"Comment deleted: id={comment_id}")


# =============================================================================
# Activity Feed Endpoint
# =============================================================================


@router.get(
    "/activity",
    response_model=ActivityFeedResponse,
    summary="Get team activity feed",
    description="Get the team activity feed showing recent actions.",
)
async def get_team_activity(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
) -> ActivityFeedResponse:
    """
    Get team activity feed.

    Returns recent activities including assignments, comments, and status changes.
    """
    service = TeamCollaborationService(db)
    activities, total = await service.get_activity_feed(
        lab_owner_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return ActivityFeedResponse(
        activities=[ActivityItem(**a) for a in activities],
        total=total,
        has_more=(offset + len(activities)) < total,
    )


# =============================================================================
# Deadline Conflicts Endpoint
# =============================================================================


@router.get(
    "/deadlines/conflicts",
    response_model=DeadlineConflictsResponse,
    summary="Check deadline conflicts",
    description="Check for overlapping deadlines within the team.",
)
async def check_deadline_conflicts(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    window_days: int = Query(7, ge=1, le=30, description="Days window for conflict detection"),
) -> DeadlineConflictsResponse:
    """
    Check for deadline conflicts within the team.

    Identifies team members who have multiple assignments due within
    the specified time window. Severity is calculated based on the
    number of overlapping deadlines.
    """
    service = TeamCollaborationService(db)
    result = await service.check_deadline_conflicts(
        lab_owner_id=current_user.id,
        conflict_window_days=window_days,
    )

    conflicts = []
    for c in result["conflicts"]:
        conflicts.append(
            DeadlineConflict(
                user_id=c["user_id"],
                user_name=c["user_name"],
                user_email=c["user_email"],
                conflict_date=c["conflict_date"],
                conflicting_assignments=[DeadlineAssignment(**a) for a in c["conflicting_assignments"]],
                severity=c["severity"],
            )
        )

    return DeadlineConflictsResponse(
        conflicts=conflicts,
        total_conflicts=result["total_conflicts"],
        users_with_conflicts=result["users_with_conflicts"],
        conflict_window_days=result["conflict_window_days"],
    )


# =============================================================================
# Team Notification Endpoints
# =============================================================================


@router.get(
    "/notifications",
    response_model=TeamNotificationListResponse,
    summary="Get team notifications",
    description="Get team collaboration notifications for the current user.",
)
async def get_team_notifications(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    unread_only: bool = Query(False, description="Only return unread notifications"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
) -> TeamNotificationListResponse:
    """
    Get team notifications for the current user.

    Returns notifications for assignments, comments, mentions, and other
    team collaboration events.
    """
    service = TeamCollaborationService(db)
    notifications, total, unread_count = await service.get_team_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    return TeamNotificationListResponse(
        notifications=[
            TeamNotificationResponse(
                id=n.id,
                user_id=n.user_id,
                team_id=n.team_id,
                notification_type=n.notification_type,
                message=n.message,
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                metadata=n.metadata_,
                is_read=n.is_read,
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        total=total,
        unread_count=unread_count,
        has_more=(offset + len(notifications)) < total,
    )


@router.post(
    "/notifications/read",
    summary="Mark notifications as read",
    description="Mark team notifications as read.",
)
async def mark_notifications_read(
    data: MarkNotificationsReadRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> dict:
    """
    Mark team notifications as read.

    If notification_ids is not provided, marks all unread notifications as read.
    """
    service = TeamCollaborationService(db)
    count = await service.mark_notifications_read(
        user_id=current_user.id,
        notification_ids=data.notification_ids,
    )

    return {
        "success": True,
        "message": f"Marked {count} notifications as read",
        "count": count,
    }
