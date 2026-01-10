"""Review workflow service layer for business logic."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import GrantApplication, User
from backend.models.reviews import (
    ReviewWorkflow,
    ApplicationReview,
    ReviewStageAction,
    ApplicationTeamMember,
)
from backend.schemas.reviews import (
    ReviewWorkflowCreate,
    ReviewWorkflowUpdate,
    ReviewWorkflowResponse,
    ReviewAction,
    ReviewStatus,
    AddTeamMemberRequest,
    UpdateTeamMemberRequest,
    WorkflowStageResponse,
    ReviewStageActionResponse,
    ApplicationReviewResponse,
    TeamMemberResponse,
    TeamMemberPermissions,
)


class ReviewWorkflowService:
    """Service for managing internal review workflows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Workflow Operations
    # =========================================================================

    async def list_workflows(
        self,
        user_id: UUID,
        include_inactive: bool = False,
    ) -> List[ReviewWorkflow]:
        """List all workflows for a user."""
        query = select(ReviewWorkflow).where(ReviewWorkflow.user_id == user_id)

        if not include_inactive:
            query = query.where(ReviewWorkflow.is_active)

        query = query.order_by(ReviewWorkflow.is_default.desc(), ReviewWorkflow.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_workflow(self, user_id: UUID, workflow_id: UUID) -> ReviewWorkflow:
        """Get a specific workflow by ID."""
        result = await self.db.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.id == workflow_id,
                ReviewWorkflow.user_id == user_id,
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError("Workflow not found")
        return workflow

    async def create_workflow(
        self,
        user_id: UUID,
        data: ReviewWorkflowCreate,
    ) -> ReviewWorkflow:
        """Create a new workflow."""
        # If setting as default, unset any existing default
        if data.is_default:
            await self._unset_default_workflow(user_id)

        # Convert stages to dict format
        stages_data = [stage.model_dump() for stage in data.stages]

        workflow = ReviewWorkflow(
            user_id=user_id,
            name=data.name,
            description=data.description,
            stages=stages_data,
            is_default=data.is_default,
        )
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def update_workflow(
        self,
        user_id: UUID,
        workflow_id: UUID,
        data: ReviewWorkflowUpdate,
    ) -> ReviewWorkflow:
        """Update an existing workflow."""
        workflow = await self.get_workflow(user_id, workflow_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle is_default separately
        if "is_default" in update_data and update_data["is_default"]:
            await self._unset_default_workflow(user_id)

        # Handle stages conversion
        if "stages" in update_data and update_data["stages"]:
            update_data["stages"] = [
                stage.model_dump() if hasattr(stage, "model_dump") else stage for stage in update_data["stages"]
            ]

        for key, value in update_data.items():
            setattr(workflow, key, value)

        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def delete_workflow(self, user_id: UUID, workflow_id: UUID) -> None:
        """Delete a workflow (soft delete by setting inactive)."""
        workflow = await self.get_workflow(user_id, workflow_id)

        # Check if workflow is in use by active reviews
        result = await self.db.execute(
            select(func.count(ApplicationReview.id)).where(
                ApplicationReview.workflow_id == workflow_id,
                ApplicationReview.status.in_(["pending", "in_review"]),
            )
        )
        active_count = result.scalar()
        if active_count > 0:
            raise ValueError(f"Cannot delete workflow with {active_count} active reviews")

        # Soft delete by marking inactive
        workflow.is_active = False
        if workflow.is_default:
            workflow.is_default = False

        await self.db.commit()

    async def _unset_default_workflow(self, user_id: UUID) -> None:
        """Unset any existing default workflow for user."""
        await self.db.execute(
            ReviewWorkflow.__table__.update()
            .where(
                ReviewWorkflow.user_id == user_id,
                ReviewWorkflow.is_default,
            )
            .values(is_default=False)
        )

    async def _get_default_workflow(self, user_id: UUID) -> Optional[ReviewWorkflow]:
        """Get the default workflow for a user."""
        result = await self.db.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.user_id == user_id,
                ReviewWorkflow.is_default,
                ReviewWorkflow.is_active,
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # Review Operations
    # =========================================================================

    async def get_review(
        self,
        user_id: UUID,
        card_id: UUID,
    ) -> Optional[ApplicationReview]:
        """Get the current review for an application."""
        await self._verify_app_access(user_id, card_id)

        result = await self.db.execute(
            select(ApplicationReview)
            .options(
                selectinload(ApplicationReview.workflow),
                selectinload(ApplicationReview.actions).selectinload(ReviewStageAction.reviewer),
                selectinload(ApplicationReview.starter),
            )
            .where(ApplicationReview.kanban_card_id == card_id)
        )
        return result.scalar_one_or_none()

    async def start_review(
        self,
        user_id: UUID,
        card_id: UUID,
        workflow_id: Optional[UUID] = None,
    ) -> ApplicationReview:
        """Start a review process for an application."""
        await self._verify_app_access(user_id, card_id)

        # Check if a review already exists
        existing = await self.get_review(user_id, card_id)
        if existing and existing.status in ["pending", "in_review"]:
            raise ValueError("An active review already exists for this application")

        # Get the workflow
        if workflow_id:
            workflow = await self.get_workflow(user_id, workflow_id)
        else:
            workflow = await self._get_default_workflow(user_id)
            if not workflow:
                raise ValueError("No workflow specified and no default workflow found")

        # Create the review
        review = ApplicationReview(
            kanban_card_id=card_id,
            workflow_id=workflow.id,
            current_stage=0,
            status="in_review",
            started_by=user_id,
            started_at=datetime.now(timezone.utc),
            stage_started_at=datetime.now(timezone.utc),
        )
        self.db.add(review)

        # Log the start action
        stage_name = workflow.stages[0]["name"] if workflow.stages else "Unknown"
        action = ReviewStageAction(
            review_id=review.id,
            stage_order=0,
            stage_name=stage_name,
            reviewer_id=user_id,
            action="commented",
            comments="Review process started",
        )
        self.db.add(action)

        await self.db.commit()
        await self.db.refresh(review)

        # Reload with relationships
        return await self.get_review(user_id, card_id)

    async def submit_action(
        self,
        user_id: UUID,
        card_id: UUID,
        action: ReviewAction,
        comments: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApplicationReview:
        """Submit a review action."""
        review = await self.get_review(user_id, card_id)
        if not review:
            raise ValueError("No active review found for this application")

        if review.status not in ["pending", "in_review"]:
            raise ValueError(f"Cannot submit actions to a review with status: {review.status}")

        # Get current stage info
        workflow = review.workflow
        current_stage_index = review.current_stage
        stages = workflow.stages if workflow else []

        if current_stage_index >= len(stages):
            raise ValueError("Review is at an invalid stage")

        current_stage = stages[current_stage_index]
        stage_name = current_stage.get("name", f"Stage {current_stage_index}")

        # Create the action record
        review_action = ReviewStageAction(
            review_id=review.id,
            stage_order=current_stage_index,
            stage_name=stage_name,
            reviewer_id=user_id,
            action=action.value,
            comments=comments,
            metadata_=metadata,
        )
        self.db.add(review_action)

        # Process the action
        if action == ReviewAction.APPROVED:
            # Move to next stage or complete
            next_stage = current_stage_index + 1
            if next_stage >= len(stages):
                # Review complete
                review.status = "approved"
                review.completed_at = datetime.now(timezone.utc)
            else:
                # Move to next stage
                review.current_stage = next_stage
                review.stage_started_at = datetime.now(timezone.utc)
                review.escalation_sent = False

        elif action == ReviewAction.REJECTED:
            # End the review as rejected
            review.status = "rejected"
            review.completed_at = datetime.now(timezone.utc)

        elif action == ReviewAction.RETURNED:
            # Stay at current stage, reset timer
            review.stage_started_at = datetime.now(timezone.utc)
            review.escalation_sent = False

        # COMMENTED action just adds a comment, no state change

        await self.db.commit()
        return await self.get_review(user_id, card_id)

    async def get_review_history(
        self,
        user_id: UUID,
        card_id: UUID,
    ) -> Tuple[ApplicationReview, List[ReviewStageAction]]:
        """Get review with full action history."""
        review = await self.get_review(user_id, card_id)
        if not review:
            raise ValueError("No review found for this application")

        result = await self.db.execute(
            select(ReviewStageAction)
            .options(selectinload(ReviewStageAction.reviewer))
            .where(ReviewStageAction.review_id == review.id)
            .order_by(ReviewStageAction.acted_at)
        )
        actions = result.scalars().all()

        return review, actions

    async def cancel_review(self, user_id: UUID, card_id: UUID) -> None:
        """Cancel an active review."""
        review = await self.get_review(user_id, card_id)
        if not review:
            raise ValueError("No review found for this application")

        if review.status in ["approved", "rejected"]:
            raise ValueError("Cannot cancel a completed review")

        await self.db.delete(review)
        await self.db.commit()

    async def get_pending_reviews(
        self,
        user_id: UUID,
        status: Optional[str] = None,
    ) -> List[ApplicationReview]:
        """Get reviews pending action from the user."""
        # Get applications owned by user or where user is a team member
        query = (
            select(ApplicationReview)
            .options(
                selectinload(ApplicationReview.workflow),
                selectinload(ApplicationReview.application),
                selectinload(ApplicationReview.starter),
            )
            .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
            .where(
                or_(
                    GrantApplication.user_id == user_id,
                    ApplicationReview.kanban_card_id.in_(
                        select(ApplicationTeamMember.kanban_card_id).where(ApplicationTeamMember.user_id == user_id)
                    ),
                )
            )
        )

        if status:
            query = query.where(ApplicationReview.status == status)
        else:
            query = query.where(ApplicationReview.status.in_(["pending", "in_review"]))

        query = query.order_by(ApplicationReview.stage_started_at)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_review_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get review statistics for a user."""
        # Get all reviews for user's applications
        (
            select(ApplicationReview)
            .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
            .where(GrantApplication.user_id == user_id)
        )

        # Count by status
        status_counts = {}
        for status in ["pending", "in_review", "approved", "rejected", "escalated"]:
            result = await self.db.execute(
                select(func.count(ApplicationReview.id))
                .select_from(ApplicationReview)
                .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
                .where(
                    GrantApplication.user_id == user_id,
                    ApplicationReview.status == status,
                )
            )
            status_counts[status] = result.scalar() or 0

        # Total reviews
        result = await self.db.execute(
            select(func.count(ApplicationReview.id))
            .select_from(ApplicationReview)
            .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
            .where(GrantApplication.user_id == user_id)
        )
        total = result.scalar() or 0

        # Workflows count
        result = await self.db.execute(
            select(func.count(ReviewWorkflow.id)).where(
                ReviewWorkflow.user_id == user_id,
                ReviewWorkflow.is_active,
            )
        )
        workflows_count = result.scalar() or 0

        return {
            "total_reviews": total,
            "by_status": status_counts,
            "active_reviews": status_counts.get("pending", 0) + status_counts.get("in_review", 0),
            "completed_reviews": status_counts.get("approved", 0) + status_counts.get("rejected", 0),
            "workflows_count": workflows_count,
        }

    # =========================================================================
    # Team Member Operations
    # =========================================================================

    async def get_team_members(
        self,
        user_id: UUID,
        card_id: UUID,
    ) -> List[ApplicationTeamMember]:
        """Get all team members for an application."""
        await self._verify_app_access(user_id, card_id)

        result = await self.db.execute(
            select(ApplicationTeamMember)
            .options(
                selectinload(ApplicationTeamMember.user),
                selectinload(ApplicationTeamMember.added_by_user),
            )
            .where(ApplicationTeamMember.kanban_card_id == card_id)
            .order_by(ApplicationTeamMember.added_at)
        )
        return result.scalars().all()

    async def add_team_member(
        self,
        user_id: UUID,
        card_id: UUID,
        data: AddTeamMemberRequest,
    ) -> ApplicationTeamMember:
        """Add a team member to an application."""
        await self._verify_app_access(user_id, card_id)

        # Determine the member user ID
        member_user_id = data.user_id
        if not member_user_id and data.email:
            # Look up user by email
            result = await self.db.execute(select(User).where(User.email == data.email))
            member_user = result.scalar_one_or_none()
            if member_user:
                member_user_id = member_user.id
            else:
                raise ValueError(f"User with email {data.email} not found")

        if not member_user_id:
            raise ValueError("Must provide either user_id or email")

        # Check if already a team member
        result = await self.db.execute(
            select(ApplicationTeamMember).where(
                ApplicationTeamMember.kanban_card_id == card_id,
                ApplicationTeamMember.user_id == member_user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("User is already a team member for this application")

        # Convert permissions to dict if provided
        permissions_data = None
        if data.permissions:
            permissions_data = data.permissions.model_dump()

        member = ApplicationTeamMember(
            kanban_card_id=card_id,
            user_id=member_user_id,
            role=data.role.value,
            permissions=permissions_data,
            added_by=user_id,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)

        # Reload with relationships
        result = await self.db.execute(
            select(ApplicationTeamMember)
            .options(
                selectinload(ApplicationTeamMember.user),
                selectinload(ApplicationTeamMember.added_by_user),
            )
            .where(ApplicationTeamMember.id == member.id)
        )
        return result.scalar_one()

    async def update_team_member(
        self,
        user_id: UUID,
        card_id: UUID,
        member_id: UUID,
        data: UpdateTeamMemberRequest,
    ) -> ApplicationTeamMember:
        """Update a team member's role or permissions."""
        await self._verify_app_access(user_id, card_id)

        result = await self.db.execute(
            select(ApplicationTeamMember)
            .options(
                selectinload(ApplicationTeamMember.user),
                selectinload(ApplicationTeamMember.added_by_user),
            )
            .where(
                ApplicationTeamMember.id == member_id,
                ApplicationTeamMember.kanban_card_id == card_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("Team member not found")

        if data.role:
            member.role = data.role.value
        if data.permissions:
            member.permissions = data.permissions.model_dump()

        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_team_member(
        self,
        user_id: UUID,
        card_id: UUID,
        member_id: UUID,
    ) -> None:
        """Remove a team member from an application."""
        await self._verify_app_access(user_id, card_id)

        result = await self.db.execute(
            select(ApplicationTeamMember).where(
                ApplicationTeamMember.id == member_id,
                ApplicationTeamMember.kanban_card_id == card_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("Team member not found")

        await self.db.delete(member)
        await self.db.commit()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _verify_app_access(self, user_id: UUID, card_id: UUID) -> None:
        """Verify that a user has access to an application."""
        # Check if user owns the application or is a team member
        result = await self.db.execute(
            select(GrantApplication.id).where(
                GrantApplication.id == card_id,
                GrantApplication.user_id == user_id,
            )
        )
        if result.scalar_one_or_none():
            return

        # Check team membership
        result = await self.db.execute(
            select(ApplicationTeamMember.id).where(
                ApplicationTeamMember.kanban_card_id == card_id,
                ApplicationTeamMember.user_id == user_id,
            )
        )
        if result.scalar_one_or_none():
            return

        raise ValueError("Application not found or access denied")

    def _build_workflow_response(self, workflow: ReviewWorkflow) -> ReviewWorkflowResponse:
        """Build a workflow response from model."""
        stages = []
        for stage_data in workflow.stages or []:
            stages.append(
                WorkflowStageResponse(
                    order=stage_data.get("order", 0),
                    name=stage_data.get("name", "Unknown"),
                    required_role=stage_data.get("required_role"),
                    sla_hours=stage_data.get("sla_hours"),
                    auto_escalate=stage_data.get("auto_escalate", False),
                    description=stage_data.get("description"),
                )
            )

        return ReviewWorkflowResponse(
            id=workflow.id,
            user_id=workflow.user_id,
            name=workflow.name,
            description=workflow.description,
            stages=stages,
            is_default=workflow.is_default,
            is_active=workflow.is_active,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    def _build_review_response(self, review: ApplicationReview) -> ApplicationReviewResponse:
        """Build a review response from model."""
        workflow = review.workflow
        stages = workflow.stages if workflow else []
        total_stages = len(stages)

        current_stage_name = None
        sla_hours = None
        if review.current_stage < len(stages):
            current_stage_data = stages[review.current_stage]
            current_stage_name = current_stage_data.get("name")
            sla_hours = current_stage_data.get("sla_hours")

        actions = []
        for action in review.actions or []:
            actions.append(self._build_action_response(action))

        return ApplicationReviewResponse(
            id=review.id,
            kanban_card_id=review.kanban_card_id,
            workflow_id=review.workflow_id,
            workflow_name=workflow.name if workflow else None,
            current_stage=review.current_stage,
            current_stage_name=current_stage_name,
            total_stages=total_stages,
            status=ReviewStatus(review.status),
            started_by=review.started_by,
            started_by_name=review.starter.name if review.starter else None,
            started_at=review.started_at,
            completed_at=review.completed_at,
            stage_started_at=review.stage_started_at,
            escalation_sent=review.escalation_sent,
            sla_hours=sla_hours,
            actions=actions,
        )

    def _build_action_response(self, action: ReviewStageAction) -> ReviewStageActionResponse:
        """Build an action response from model."""
        return ReviewStageActionResponse(
            id=action.id,
            review_id=action.review_id,
            stage_order=action.stage_order,
            stage_name=action.stage_name,
            reviewer_id=action.reviewer_id,
            reviewer_name=action.reviewer.name if action.reviewer else None,
            reviewer_email=action.reviewer.email if action.reviewer else None,
            action=ReviewAction(action.action),
            comments=action.comments,
            metadata=action.metadata_,
            acted_at=action.acted_at,
        )

    def _build_team_member_response(self, member: ApplicationTeamMember) -> TeamMemberResponse:
        """Build a team member response from model."""
        permissions = None
        if member.permissions:
            permissions = TeamMemberPermissions(**member.permissions)

        from backend.schemas.reviews import TeamMemberRole

        return TeamMemberResponse(
            id=member.id,
            kanban_card_id=member.kanban_card_id,
            user_id=member.user_id,
            user_name=member.user.name if member.user else None,
            user_email=member.user.email if member.user else None,
            role=TeamMemberRole(member.role),
            permissions=permissions,
            added_by=member.added_by,
            added_at=member.added_at,
        )
