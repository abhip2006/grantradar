"""Internal review workflow API router."""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.exceptions import NotFoundError, ValidationError
from backend.api.utils.auth import verify_card_ownership
from backend.schemas.reviews import (
    ReviewWorkflowCreate,
    ReviewWorkflowUpdate,
    ReviewWorkflowResponse,
    ReviewWorkflowList,
    StartReviewRequest,
    ReviewActionRequest,
    ApplicationReviewResponse,
    ReviewHistoryResponse,
    ReviewStageActionResponse,
    AddTeamMemberRequest,
    UpdateTeamMemberRequest,
    TeamMemberResponse,
    TeamMemberList,
    DefaultWorkflowResponse,
    DEFAULT_WORKFLOWS,
    WorkflowStage,
)
from backend.schemas.common import PaginationInfo
from backend.services.review_workflow import ReviewWorkflowService


router = APIRouter(prefix="/api", tags=["reviews"])


def get_service(db: AsyncSession = Depends(get_db)) -> ReviewWorkflowService:
    return ReviewWorkflowService(db)


# ============================================================================
# Workflow Endpoints
# ============================================================================

@router.get("/workflows", response_model=ReviewWorkflowList)
async def list_workflows(
    current_user: CurrentUser,
    include_inactive: bool = False,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    List all review workflows for the current user.

    Returns all active workflows by default. Set include_inactive=true
    to include inactive workflows as well.
    """
    workflows = await service.list_workflows(
        user_id=current_user.id,
        include_inactive=include_inactive,
    )
    workflow_responses = [service._build_workflow_response(w) for w in workflows]
    return ReviewWorkflowList(
        data=workflow_responses,
        pagination=PaginationInfo(
            total=len(workflows),
            offset=0,
            limit=len(workflows),
            has_more=False,
        ),
    )


@router.get("/workflows/defaults")
async def get_default_workflow_templates(
    current_user: CurrentUser,
) -> List[DefaultWorkflowResponse]:
    """
    Get default workflow templates that can be used as starting points.

    Returns pre-configured workflow templates for common review scenarios.
    """
    templates = []
    for key, template in DEFAULT_WORKFLOWS.items():
        templates.append(DefaultWorkflowResponse(
            key=key,
            name=template["name"],
            description=template["description"],
            stages=[WorkflowStage(**stage) for stage in template["stages"]],
            stage_count=len(template["stages"]),
        ))
    return templates


@router.get("/workflows/{workflow_id}", response_model=ReviewWorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Get a specific review workflow by ID.
    """
    try:
        workflow = await service.get_workflow(current_user.id, workflow_id)
        return service._build_workflow_response(workflow)
    except ValueError as e:
        raise NotFoundError("Workflow", str(workflow_id))


@router.post("/workflows", response_model=ReviewWorkflowResponse, status_code=201)
async def create_workflow(
    data: ReviewWorkflowCreate,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Create a new review workflow.

    Define the stages and rules for an internal review process.
    """
    workflow = await service.create_workflow(current_user.id, data)
    return service._build_workflow_response(workflow)


@router.post("/workflows/from-template/{template_key}", response_model=ReviewWorkflowResponse, status_code=201)
async def create_workflow_from_template(
    template_key: str,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Create a new workflow from a default template.

    Valid template keys: standard, quick, comprehensive
    """
    if template_key not in DEFAULT_WORKFLOWS:
        raise ValidationError(f"Invalid template key. Valid options: {', '.join(DEFAULT_WORKFLOWS.keys())}")

    template = DEFAULT_WORKFLOWS[template_key]
    data = ReviewWorkflowCreate(
        name=template["name"],
        description=template["description"],
        stages=[WorkflowStage(**stage) for stage in template["stages"]],
        is_default=False,
    )
    workflow = await service.create_workflow(current_user.id, data)
    return service._build_workflow_response(workflow)


@router.patch("/workflows/{workflow_id}", response_model=ReviewWorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: ReviewWorkflowUpdate,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Update an existing review workflow.
    """
    try:
        workflow = await service.update_workflow(current_user.id, workflow_id, data)
        return service._build_workflow_response(workflow)
    except ValueError as e:
        raise NotFoundError("Workflow", str(workflow_id))


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Delete a review workflow.

    Note: Cannot delete workflows that are in use by active reviews.
    """
    try:
        await service.delete_workflow(current_user.id, workflow_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise ValidationError(str(e))


# ============================================================================
# Review Process Endpoints
# ============================================================================

@router.get("/kanban/{card_id}/review", response_model=Optional[ApplicationReviewResponse])
async def get_review(
    card_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Get the current review for an application.

    Returns null if no review process has been started.
    """
    # Verify user owns the card before accessing review data
    await verify_card_ownership(db, card_id, current_user.id)

    try:
        review = await service.get_review(current_user.id, card_id)
        if review is None:
            return None
        return service._build_review_response(review)
    except ValueError as e:
        raise NotFoundError("Review", str(card_id))


@router.post("/kanban/{card_id}/review", response_model=ApplicationReviewResponse, status_code=201)
async def start_review(
    card_id: UUID,
    data: StartReviewRequest,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Start a review process for an application.

    If workflow_id is not provided, the user's default workflow will be used.
    """
    try:
        review = await service.start_review(
            user_id=current_user.id,
            card_id=card_id,
            workflow_id=data.workflow_id,
        )
        return service._build_review_response(review)
    except ValueError as e:
        raise ValidationError(str(e))


@router.post("/kanban/{card_id}/review/action", response_model=ApplicationReviewResponse)
async def submit_review_action(
    card_id: UUID,
    data: ReviewActionRequest,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Submit a review action (approve, reject, return, or comment).

    Approving the current stage advances the review to the next stage.
    Rejecting ends the review process with a rejected status.
    Returning sends the application back for revision (stays at current stage).
    """
    try:
        review = await service.submit_action(
            user_id=current_user.id,
            card_id=card_id,
            action=data.action,
            comments=data.comments,
            metadata=data.metadata,
        )
        return service._build_review_response(review)
    except ValueError as e:
        raise ValidationError(str(e))


@router.get("/kanban/{card_id}/review/history", response_model=ReviewHistoryResponse)
async def get_review_history(
    card_id: UUID,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Get the full review history for an application.

    Returns all review actions taken across all stages.
    """
    try:
        review, actions = await service.get_review_history(current_user.id, card_id)
        return ReviewHistoryResponse(
            review=service._build_review_response(review),
            actions=[service._build_action_response(a) for a in actions],
        )
    except ValueError as e:
        raise NotFoundError("Review history", str(card_id))


@router.delete("/kanban/{card_id}/review")
async def cancel_review(
    card_id: UUID,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Cancel an active review process.

    This will remove the review and all its actions.
    """
    try:
        await service.cancel_review(current_user.id, card_id)
        return {"status": "cancelled"}
    except ValueError as e:
        raise ValidationError(str(e))


# ============================================================================
# Team Member Endpoints
# ============================================================================

@router.get("/kanban/{card_id}/team", response_model=TeamMemberList)
async def get_team_members(
    card_id: UUID,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Get all team members for an application.
    """
    try:
        members = await service.get_team_members(current_user.id, card_id)
        member_responses = [service._build_team_member_response(m) for m in members]
        return TeamMemberList(
            data=member_responses,
            pagination=PaginationInfo(
                total=len(members),
                offset=0,
                limit=len(members),
                has_more=False,
            ),
        )
    except ValueError as e:
        raise NotFoundError("Team members", str(card_id))


@router.post("/kanban/{card_id}/team", response_model=TeamMemberResponse, status_code=201)
async def add_team_member(
    card_id: UUID,
    data: AddTeamMemberRequest,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Add a team member to an application.

    Provide either user_id (for existing users) or email (to invite).
    """
    try:
        member = await service.add_team_member(
            user_id=current_user.id,
            card_id=card_id,
            data=data,
        )
        return service._build_team_member_response(member)
    except ValueError as e:
        raise ValidationError(str(e))


@router.patch("/kanban/{card_id}/team/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    card_id: UUID,
    member_id: UUID,
    data: UpdateTeamMemberRequest,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Update a team member's role or permissions.
    """
    try:
        member = await service.update_team_member(
            user_id=current_user.id,
            card_id=card_id,
            member_id=member_id,
            data=data,
        )
        return service._build_team_member_response(member)
    except ValueError as e:
        raise NotFoundError("Team member", str(member_id))


@router.delete("/kanban/{card_id}/team/{member_id}")
async def remove_team_member(
    card_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Remove a team member from an application.
    """
    try:
        await service.remove_team_member(
            user_id=current_user.id,
            card_id=card_id,
            member_id=member_id,
        )
        return {"status": "removed"}
    except ValueError as e:
        raise NotFoundError("Team member", str(member_id))


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/reviews/pending", response_model=List[ApplicationReviewResponse])
async def get_pending_reviews(
    current_user: CurrentUser,
    review_status: Optional[str] = None,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Get all reviews pending action from the current user.

    Only returns reviews for cards owned by the current user.
    Optionally filter by review status.
    """
    # Service layer filters by user_id to ensure only user's own reviews are returned
    reviews = await service.get_pending_reviews(
        user_id=current_user.id,
        status=review_status,
    )
    return [service._build_review_response(r) for r in reviews]


@router.get("/reviews/stats")
async def get_review_stats(
    current_user: CurrentUser,
    service: ReviewWorkflowService = Depends(get_service),
):
    """
    Get review statistics for the current user.
    """
    stats = await service.get_review_stats(current_user.id)
    return stats
