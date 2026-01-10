"""Team collaboration API endpoints for member management and activity tracking."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from backend.api.deps import AsyncSessionDep, CurrentUser, OptionalUser
from backend.api.team_service import TeamService
from backend.schemas.team import (
    TeamInviteRequest,
    InvitationAcceptRequest,
    InvitationDeclineRequest,
    TeamMemberResponse,
    TeamMemberUpdate,
    TeamMembersListResponse,
    TeamActivityResponse,
    TeamActivitiesListResponse,
    TeamActivityFilters,
    TeamStatsResponse,
    InvitationResponse,
    MemberPermissions,
    ActivityType,
    EntityType,
    BulkInviteRequest,
    BulkInviteResponse,
    BulkInviteResultItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/team",
    tags=["Team"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def _build_member_response(member) -> TeamMemberResponse:
    """Build a TeamMemberResponse from a LabMember model."""
    permissions = None
    if member.permissions:
        permissions = MemberPermissions(**member.permissions)

    return TeamMemberResponse(
        id=member.id,
        lab_owner_id=member.lab_owner_id,
        member_email=member.member_email,
        member_user_id=member.member_user_id,
        role=member.role,
        invited_at=member.invited_at,
        accepted_at=member.accepted_at,
        invitation_status=member.invitation_status,
        invitation_expires_at=member.invitation_expires_at,
        declined_at=member.declined_at,
        permissions=permissions,
        member_name=member.member_user.name if member.member_user else None,
    )


def _build_activity_response(activity) -> TeamActivityResponse:
    """Build a TeamActivityResponse from a TeamActivityLog model."""
    return TeamActivityResponse(
        id=activity.id,
        lab_owner_id=activity.lab_owner_id,
        actor_id=activity.actor_id,
        action_type=activity.action_type,
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        entity_name=activity.entity_name,
        metadata=activity.metadata_,
        created_at=activity.created_at,
        actor_name=activity.actor.name if activity.actor else None,
        actor_email=activity.actor.email if activity.actor else None,
    )


# =============================================================================
# Team Member Endpoints
# =============================================================================


@router.get(
    "",
    response_model=TeamMembersListResponse,
    summary="List team members",
    description="Get all team members for the current user's lab, including pending invitations.",
)
async def list_team_members(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    include_pending: bool = Query(True, description="Include pending invitations in the list"),
    search: Optional[str] = Query(None, description="Search by email or name"),
) -> TeamMembersListResponse:
    """
    List all team members for the current user's lab.

    Returns members with their invitation status, role, and permissions.
    Supports optional search filtering by email or member name.
    """
    service = TeamService(db)
    members = await service.list_members(
        lab_owner_id=current_user.id,
        include_pending=include_pending,
    )

    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        members = [
            m
            for m in members
            if search_lower in m.member_email.lower()
            or (m.member_user and m.member_user.name and search_lower in m.member_user.name.lower())
        ]

    member_responses = [_build_member_response(m) for m in members]

    pending_count = sum(1 for m in members if m.invitation_status == "pending")
    active_count = sum(1 for m in members if m.invitation_status == "accepted")

    return TeamMembersListResponse(
        members=member_responses,
        total=len(members),
        pending_count=pending_count,
        active_count=active_count,
    )


@router.get(
    "/stats",
    response_model=TeamStatsResponse,
    summary="Get team statistics",
    description="Get statistics about the team including member counts and activity.",
)
async def get_team_stats(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> TeamStatsResponse:
    """
    Get team statistics for the current user's lab.

    Returns counts of members by status and role, plus recent activity count.
    """
    service = TeamService(db)
    stats = await service.get_team_stats(lab_owner_id=current_user.id)
    return TeamStatsResponse(**stats)


@router.get(
    "/activity",
    response_model=TeamActivitiesListResponse,
    summary="Get team activity",
    description="Get the team activity feed with optional filtering.",
)
async def get_team_activity(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    action_type: Optional[str] = Query(None, description="Filter by action type (comma-separated for multiple)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (comma-separated for multiple)"),
    actor_id: Optional[UUID] = Query(None, description="Filter by actor"),
    entity_id: Optional[UUID] = Query(None, description="Filter by entity"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
) -> TeamActivitiesListResponse:
    """
    Get team activity feed.

    Returns activities sorted by most recent first.
    """
    # Parse filter values
    action_types = None
    if action_type:
        try:
            action_types = [ActivityType(at.strip()) for at in action_type.split(",")]
        except ValueError:
            pass  # Ignore invalid values

    entity_types = None
    if entity_type:
        try:
            entity_types = [EntityType(et.strip()) for et in entity_type.split(",")]
        except ValueError:
            pass  # Ignore invalid values

    filters = TeamActivityFilters(
        action_types=action_types,
        entity_types=entity_types,
        actor_id=actor_id,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )

    service = TeamService(db)
    activities, total = await service.get_activities(
        lab_owner_id=current_user.id,
        filters=filters,
    )

    activity_responses = [_build_activity_response(a) for a in activities]

    return TeamActivitiesListResponse(
        activities=activity_responses,
        total=total,
        has_more=(offset + len(activities)) < total,
    )


@router.get(
    "/{member_id}",
    response_model=TeamMemberResponse,
    summary="Get team member details",
    description="Get detailed information about a specific team member.",
)
async def get_team_member(
    member_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> TeamMemberResponse:
    """
    Get details for a specific team member.

    Includes invitation status, role, and permissions.
    """
    service = TeamService(db)
    member = await service.get_member(
        lab_owner_id=current_user.id,
        member_id=member_id,
    )
    return _build_member_response(member)


@router.patch(
    "/{member_id}",
    response_model=TeamMemberResponse,
    summary="Update team member",
    description="Update a team member's role and/or permissions.",
)
async def update_team_member(
    member_id: UUID,
    data: TeamMemberUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> TeamMemberResponse:
    """
    Update a team member's role and/or permissions.

    Only the lab owner can update member settings.
    """
    service = TeamService(db)
    member = await service.update_member(
        lab_owner_id=current_user.id,
        member_id=member_id,
        data=data,
    )
    return _build_member_response(member)


@router.delete(
    "/{member_id}",
    status_code=204,
    summary="Remove team member",
    description="Remove a team member from the lab.",
)
async def remove_team_member(
    member_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Remove a team member from the lab.

    This action cannot be undone. The member will need to be re-invited.
    """
    service = TeamService(db)
    await service.remove_member(
        lab_owner_id=current_user.id,
        member_id=member_id,
    )


# =============================================================================
# Invitation Endpoints
# =============================================================================


@router.post(
    "/invite",
    response_model=InvitationResponse,
    status_code=201,
    summary="Send team invitation",
    description="Send an invitation to a new team member.",
)
async def send_invitation(
    data: TeamInviteRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InvitationResponse:
    """
    Send an invitation to a new team member.

    The invitation will be valid for 7 days. An email will be sent
    with a link to accept the invitation.
    """
    service = TeamService(db)
    member = await service.send_invitation(
        lab_owner_id=current_user.id,
        data=data,
    )

    # Trigger email sending task (imported here to avoid circular imports)
    from backend.tasks.team_tasks import send_invitation_email

    send_invitation_email.delay(
        to_email=member.member_email,
        inviter_name=current_user.name or current_user.email,
        lab_name=current_user.institution or "their team",
        role=member.role,
        token=member.invitation_token,
        message=data.message,
    )

    logger.info(f"Invitation sent: from={current_user.id}, to={member.member_email}, role={member.role}")

    return InvitationResponse(
        success=True,
        message=f"Invitation sent to {member.member_email}",
        member=_build_member_response(member),
    )


@router.post(
    "/invite/bulk",
    response_model=BulkInviteResponse,
    status_code=201,
    summary="Bulk invite team members",
    description="Send invitations to multiple team members at once.",
)
async def bulk_invite(
    data: BulkInviteRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> BulkInviteResponse:
    """
    Send invitations to multiple team members at once.

    Processes each invitation independently, so some may succeed while
    others fail (e.g., if email already exists). Returns detailed results
    for each invitation attempt.
    """
    service = TeamService(db)
    results = []
    successful_count = 0
    failed_count = 0

    for invite in data.invites:
        try:
            # Create individual invite request
            invite_request = TeamInviteRequest(
                email=invite.email,
                role=invite.role,
                message=data.message,
            )

            # Send invitation
            member = await service.send_invitation(
                lab_owner_id=current_user.id,
                data=invite_request,
            )

            # Apply permission template if specified
            if invite.permission_template_id and member.invitation_status == "pending":
                # Import here to avoid circular imports
                from sqlalchemy import select
                from backend.models import PermissionTemplate

                result = await db.execute(
                    select(PermissionTemplate).where(
                        PermissionTemplate.id == invite.permission_template_id,
                        PermissionTemplate.owner_id == current_user.id,
                    )
                )
                template = result.scalar_one_or_none()
                if template:
                    member.permissions = template.permissions
                    member.permission_template_id = template.id
                    await db.commit()
                    await db.refresh(member)

            # Trigger email sending task
            from backend.tasks.team_tasks import send_invitation_email

            send_invitation_email.delay(
                to_email=member.member_email,
                inviter_name=current_user.name or current_user.email,
                lab_name=current_user.institution or "their team",
                role=member.role,
                token=member.invitation_token,
                message=data.message,
            )

            results.append(
                BulkInviteResultItem(
                    email=invite.email,
                    success=True,
                    message="Invitation sent successfully",
                    member=_build_member_response(member),
                )
            )
            successful_count += 1

            logger.info(f"Bulk invitation sent: from={current_user.id}, to={invite.email}")

        except Exception as e:
            results.append(
                BulkInviteResultItem(
                    email=invite.email,
                    success=False,
                    message=str(e.detail) if hasattr(e, "detail") else str(e),
                    member=None,
                )
            )
            failed_count += 1

            logger.warning(f"Bulk invitation failed: to={invite.email}, error={str(e)}")

    logger.info(
        f"Bulk invite completed: total={len(data.invites)}, successful={successful_count}, failed={failed_count}"
    )

    return BulkInviteResponse(
        total_requested=len(data.invites),
        successful=successful_count,
        failed=failed_count,
        results=results,
    )


@router.post(
    "/invite/resend/{member_id}",
    response_model=InvitationResponse,
    summary="Resend invitation",
    description="Resend an invitation with a new token.",
)
async def resend_invitation(
    member_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InvitationResponse:
    """
    Resend an invitation to a team member.

    Generates a new token and resets the expiration to 7 days from now.
    """
    service = TeamService(db)
    member = await service.resend_invitation(
        lab_owner_id=current_user.id,
        member_id=member_id,
    )

    # Trigger email sending task
    from backend.tasks.team_tasks import send_invitation_email

    send_invitation_email.delay(
        to_email=member.member_email,
        inviter_name=current_user.name or current_user.email,
        lab_name=current_user.institution or "their team",
        role=member.role,
        token=member.invitation_token,
        message=None,  # No custom message on resend
    )

    logger.info(f"Invitation resent: to={member.member_email}")

    return InvitationResponse(
        success=True,
        message=f"Invitation resent to {member.member_email}",
        member=_build_member_response(member),
    )


@router.post(
    "/invite/accept",
    response_model=InvitationResponse,
    summary="Accept invitation",
    description="Accept a team invitation using the token. Works for both authenticated and unauthenticated users.",
)
async def accept_invitation(
    data: InvitationAcceptRequest,
    db: AsyncSessionDep,
    current_user: OptionalUser = None,
) -> InvitationResponse:
    """
    Accept a team invitation.

    This endpoint can be accessed with or without authentication.
    If authenticated, the member will be linked to the user account.
    """
    service = TeamService(db)
    member = await service.accept_invitation(
        token=data.token,
        user=current_user,
    )

    logger.info(f"Invitation accepted: member={member.member_email}")

    return InvitationResponse(
        success=True,
        message="You have successfully joined the team",
        member=_build_member_response(member),
    )


@router.post(
    "/invite/decline",
    response_model=InvitationResponse,
    summary="Decline invitation",
    description="Decline a team invitation using the token.",
)
async def decline_invitation(
    data: InvitationDeclineRequest,
    db: AsyncSessionDep,
) -> InvitationResponse:
    """
    Decline a team invitation.

    This endpoint does not require authentication.
    """
    service = TeamService(db)
    member = await service.decline_invitation(
        token=data.token,
        reason=data.reason,
    )

    logger.info(f"Invitation declined: member={member.member_email}")

    return InvitationResponse(
        success=True,
        message="Invitation has been declined",
        member=_build_member_response(member),
    )


@router.delete(
    "/invite/{member_id}",
    status_code=204,
    summary="Cancel invitation",
    description="Cancel a pending invitation.",
)
async def cancel_invitation(
    member_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Cancel a pending invitation.

    Only pending invitations can be cancelled.
    """
    service = TeamService(db)
    await service.cancel_invitation(
        lab_owner_id=current_user.id,
        member_id=member_id,
    )

    logger.info(f"Invitation cancelled: member_id={member_id}")
