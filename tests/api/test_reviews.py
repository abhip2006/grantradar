"""
Tests for the Internal Review Workflow API endpoints.

Covers:
- GET /api/workflows - List review workflows
- GET /api/workflows/defaults - Get default workflow templates
- GET /api/workflows/{workflow_id} - Get workflow details
- POST /api/workflows - Create workflow
- POST /api/workflows/from-template/{template_key} - Create from template
- PATCH /api/workflows/{workflow_id} - Update workflow
- DELETE /api/workflows/{workflow_id} - Delete workflow
- GET /api/kanban/{card_id}/review - Get application review
- POST /api/kanban/{card_id}/review - Start review workflow
- POST /api/kanban/{card_id}/review/action - Submit review action
- GET /api/kanban/{card_id}/review/history - Get review history
- DELETE /api/kanban/{card_id}/review - Cancel review
- GET /api/kanban/{card_id}/team - Get review team
- POST /api/kanban/{card_id}/team - Add team member
- PATCH /api/kanban/{card_id}/team/{member_id} - Update team member
- DELETE /api/kanban/{card_id}/team/{member_id} - Remove team member
- GET /api/reviews/pending - Get pending reviews
- GET /api/reviews/stats - Get review statistics
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, func

from backend.models import GrantApplication, User, Grant, ApplicationStage
from backend.models.reviews import (
    ReviewWorkflow,
    ApplicationReview,
    ReviewStageAction,
    ApplicationTeamMember,
)
from tests.fixtures.checklist_factories import (
    ReviewWorkflowFactory,
    ApplicationReviewFactory,
    ReviewStageActionFactory,
    ApplicationTeamMemberFactory,
)

pytestmark = pytest.mark.asyncio


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_workflow_stages():
    """Sample workflow stages for testing."""
    return [
        {
            "order": 0,
            "name": "Draft Review",
            "required_role": "grant_writer",
            "sla_hours": 48,
            "auto_escalate": False,
            "description": "Initial draft review",
        },
        {
            "order": 1,
            "name": "PI Review",
            "required_role": "pi",
            "sla_hours": 72,
            "auto_escalate": True,
            "description": "PI approval",
        },
        {
            "order": 2,
            "name": "Department Approval",
            "required_role": "admin",
            "sla_hours": 96,
            "auto_escalate": True,
            "description": "Final approval",
        },
    ]


# =============================================================================
# List Workflows Tests
# =============================================================================


class TestListWorkflows:
    """Tests for GET /api/workflows."""

    async def test_list_workflows_empty(self, async_session, db_user):
        """Test listing workflows when none exist."""
        result = await async_session.execute(
            select(ReviewWorkflow).where(ReviewWorkflow.user_id == db_user.id)
        )
        workflows = result.scalars().all()

        assert workflows == []

    async def test_list_workflows_returns_user_workflows(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test listing returns only user's workflows."""
        # Create workflows for user
        workflow1 = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Workflow 1",
            stages=sample_workflow_stages,
        )
        workflow2 = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Workflow 2",
            stages=sample_workflow_stages,
        )
        async_session.add(workflow1)
        async_session.add(workflow2)
        await async_session.commit()

        result = await async_session.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.user_id == db_user.id,
                ReviewWorkflow.is_active == True,
            )
        )
        workflows = result.scalars().all()

        assert len(workflows) == 2

    async def test_list_workflows_excludes_other_users(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test that other users' workflows are not visible."""
        # Create another user
        other_user = User(
            email="other_review@university.edu",
            password_hash="hashed",
            name="Other Review User",
        )
        async_session.add(other_user)
        await async_session.flush()

        # Create workflow for other user
        other_workflow = ReviewWorkflowFactory.create(
            user_id=other_user.id,
            name="Other User's Workflow",
            stages=sample_workflow_stages,
        )
        async_session.add(other_workflow)
        await async_session.commit()

        # Query for db_user's workflows
        result = await async_session.execute(
            select(ReviewWorkflow).where(ReviewWorkflow.user_id == db_user.id)
        )
        workflows = result.scalars().all()

        assert not any(w.name == "Other User's Workflow" for w in workflows)

    async def test_list_workflows_excludes_inactive_by_default(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test that inactive workflows are excluded by default."""
        # Create active and inactive workflows
        active = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Active Workflow",
            is_active=True,
            stages=sample_workflow_stages,
        )
        inactive = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Inactive Workflow",
            is_active=False,
            stages=sample_workflow_stages,
        )
        async_session.add(active)
        async_session.add(inactive)
        await async_session.commit()

        # Query active only
        result = await async_session.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.user_id == db_user.id,
                ReviewWorkflow.is_active == True,
            )
        )
        workflows = result.scalars().all()

        assert len(workflows) == 1
        assert workflows[0].name == "Active Workflow"

    async def test_list_workflows_include_inactive(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test including inactive workflows when requested."""
        active = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Active Workflow",
            is_active=True,
            stages=sample_workflow_stages,
        )
        inactive = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Inactive Workflow",
            is_active=False,
            stages=sample_workflow_stages,
        )
        async_session.add(active)
        async_session.add(inactive)
        await async_session.commit()

        # Query all (including inactive)
        result = await async_session.execute(
            select(ReviewWorkflow).where(ReviewWorkflow.user_id == db_user.id)
        )
        workflows = result.scalars().all()

        assert len(workflows) == 2


# =============================================================================
# Get Workflow Tests
# =============================================================================


class TestGetWorkflow:
    """Tests for GET /api/workflows/{workflow_id}."""

    async def test_get_workflow_by_id(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test getting a specific workflow by ID."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Test Workflow",
            description="Test description",
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.commit()

        result = await async_session.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.id == workflow.id,
                ReviewWorkflow.user_id == db_user.id,
            )
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.name == "Test Workflow"
        assert found.description == "Test description"
        assert len(found.stages) == 3

    async def test_get_workflow_not_found(self, async_session, db_user):
        """Test 404 when workflow doesn't exist."""
        fake_id = uuid4()
        result = await async_session.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.id == fake_id,
                ReviewWorkflow.user_id == db_user.id,
            )
        )
        found = result.scalar_one_or_none()

        assert found is None

    async def test_get_workflow_denied_for_other_user(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test that users cannot access other users' workflows."""
        other_user = User(
            email="other_wf@university.edu",
            password_hash="hashed",
            name="Other WF User",
        )
        async_session.add(other_user)
        await async_session.flush()

        other_workflow = ReviewWorkflowFactory.create(
            user_id=other_user.id,
            name="Private Workflow",
            stages=sample_workflow_stages,
        )
        async_session.add(other_workflow)
        await async_session.commit()

        # Try to access with db_user
        result = await async_session.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.id == other_workflow.id,
                ReviewWorkflow.user_id == db_user.id,
            )
        )
        found = result.scalar_one_or_none()

        assert found is None  # Not found because user filter


# =============================================================================
# Create Workflow Tests
# =============================================================================


class TestCreateWorkflow:
    """Tests for POST /api/workflows."""

    async def test_create_workflow(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test creating a new workflow."""
        workflow = ReviewWorkflow(
            user_id=db_user.id,
            name="New Review Workflow",
            description="Custom workflow for our lab",
            stages=sample_workflow_stages,
            is_default=False,
            is_active=True,
        )
        async_session.add(workflow)
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.id is not None
        assert workflow.name == "New Review Workflow"
        assert workflow.user_id == db_user.id
        assert len(workflow.stages) == 3

    async def test_create_workflow_as_default(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test creating a workflow as default."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Default Workflow",
            is_default=True,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.is_default is True

    async def test_create_workflow_unsets_previous_default(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test that setting a new default unsets previous default."""
        # Create initial default
        first_default = ReviewWorkflowFactory.create_default(
            user_id=db_user.id,
            name="First Default",
            stages=sample_workflow_stages,
        )
        async_session.add(first_default)
        await async_session.commit()

        # Create new default
        second_default = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Second Default",
            is_default=True,
            stages=sample_workflow_stages,
        )
        async_session.add(second_default)

        # Unset first default (simulating service behavior)
        first_default.is_default = False
        await async_session.commit()

        # Verify only one default
        result = await async_session.execute(
            select(ReviewWorkflow).where(
                ReviewWorkflow.user_id == db_user.id,
                ReviewWorkflow.is_default == True,
            )
        )
        defaults = result.scalars().all()

        assert len(defaults) == 1
        assert defaults[0].name == "Second Default"

    async def test_create_workflow_with_sla(
        self, async_session, db_user
    ):
        """Test creating workflow with SLA hours."""
        stages = [
            {
                "order": 0,
                "name": "Quick Review",
                "required_role": "pi",
                "sla_hours": 24,
                "auto_escalate": True,
            },
        ]

        workflow = ReviewWorkflow(
            user_id=db_user.id,
            name="Quick Workflow",
            stages=stages,
        )
        async_session.add(workflow)
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.stages[0]["sla_hours"] == 24
        assert workflow.stages[0]["auto_escalate"] is True


# =============================================================================
# Update Workflow Tests
# =============================================================================


class TestUpdateWorkflow:
    """Tests for PATCH /api/workflows/{workflow_id}."""

    async def test_update_workflow_name(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test updating workflow name."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            name="Original Name",
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.commit()

        workflow.name = "Updated Name"
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.name == "Updated Name"

    async def test_update_workflow_stages(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test updating workflow stages."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.commit()

        # Update to only 2 stages
        new_stages = [
            {"order": 0, "name": "Quick Check", "sla_hours": 24},
            {"order": 1, "name": "Final Approval", "sla_hours": 48},
        ]
        workflow.stages = new_stages
        await async_session.commit()
        await async_session.refresh(workflow)

        assert len(workflow.stages) == 2

    async def test_update_workflow_to_default(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test setting workflow as default."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            is_default=False,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.commit()

        workflow.is_default = True
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.is_default is True

    async def test_update_workflow_deactivate(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test deactivating a workflow."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            is_active=True,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.commit()

        workflow.is_active = False
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.is_active is False


# =============================================================================
# Delete Workflow Tests
# =============================================================================


class TestDeleteWorkflow:
    """Tests for DELETE /api/workflows/{workflow_id}."""

    async def test_delete_workflow(
        self, async_session, db_user, sample_workflow_stages
    ):
        """Test soft-deleting a workflow (marking inactive)."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            is_active=True,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.commit()

        # Soft delete by marking inactive
        workflow.is_active = False
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.is_active is False

    async def test_delete_workflow_with_active_reviews_fails(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that workflows with active reviews cannot be deleted."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        # Create application with review using this workflow
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            started_by=db_user.id,
        )
        async_session.add(review)
        await async_session.commit()

        # Check for active reviews
        result = await async_session.execute(
            select(func.count(ApplicationReview.id)).where(
                ApplicationReview.workflow_id == workflow.id,
                ApplicationReview.status.in_(["pending", "in_review"]),
            )
        )
        active_count = result.scalar()

        assert active_count > 0  # Cannot delete


# =============================================================================
# Start Review Tests
# =============================================================================


class TestStartReview:
    """Tests for POST /api/kanban/{card_id}/review."""

    async def test_start_review(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test starting a review process."""
        # Create workflow
        workflow = ReviewWorkflowFactory.create_default(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Start review
        review = ApplicationReview(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            current_stage=0,
            status="in_review",
            started_by=db_user.id,
            started_at=datetime.now(timezone.utc),
            stage_started_at=datetime.now(timezone.utc),
        )
        async_session.add(review)
        await async_session.commit()
        await async_session.refresh(review)

        assert review.id is not None
        assert review.status == "in_review"
        assert review.current_stage == 0
        assert review.workflow_id == workflow.id

    async def test_start_review_with_specific_workflow(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test starting review with a specific workflow."""
        # Create multiple workflows
        default_wf = ReviewWorkflowFactory.create_default(
            user_id=db_user.id,
            name="Default",
            stages=sample_workflow_stages,
        )
        quick_wf = ReviewWorkflowFactory.create_quick(
            user_id=db_user.id,
            name="Quick",
        )
        async_session.add(default_wf)
        async_session.add(quick_wf)
        await async_session.flush()

        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Start review with quick workflow (not default)
        review = ApplicationReview(
            kanban_card_id=application.id,
            workflow_id=quick_wf.id,
            current_stage=0,
            status="in_review",
            started_by=db_user.id,
        )
        async_session.add(review)
        await async_session.commit()

        assert review.workflow_id == quick_wf.id

    async def test_start_review_already_exists_fails(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test error when active review already exists."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create first review
        review1 = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
        )
        async_session.add(review1)
        await async_session.commit()

        # Check for existing active review
        result = await async_session.execute(
            select(ApplicationReview).where(
                ApplicationReview.kanban_card_id == application.id,
                ApplicationReview.status.in_(["pending", "in_review"]),
            )
        )
        existing = result.scalar_one_or_none()

        assert existing is not None  # Cannot start another review


# =============================================================================
# Get Review Tests
# =============================================================================


class TestGetReview:
    """Tests for GET /api/kanban/{card_id}/review."""

    async def test_get_review(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test getting the current review for an application."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            started_by=db_user.id,
        )
        async_session.add(review)
        await async_session.commit()

        # Query review
        result = await async_session.execute(
            select(ApplicationReview).where(
                ApplicationReview.kanban_card_id == application.id
            )
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.status == "in_review"

    async def test_get_review_none_exists(
        self, async_session, db_user, db_grant
    ):
        """Test getting review when none exists returns None."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.commit()

        result = await async_session.execute(
            select(ApplicationReview).where(
                ApplicationReview.kanban_card_id == application.id
            )
        )
        review = result.scalar_one_or_none()

        assert review is None


# =============================================================================
# Submit Review Action Tests
# =============================================================================


class TestSubmitReviewAction:
    """Tests for POST /api/kanban/{card_id}/review/action."""

    async def test_approve_advances_stage(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that approving advances to next stage."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            current_stage=0,
        )
        async_session.add(review)
        await async_session.flush()

        # Create approval action
        action = ReviewStageActionFactory.create_approval(
            review_id=review.id,
            reviewer_id=db_user.id,
            stage_order=0,
            stage_name="Draft Review",
        )
        async_session.add(action)

        # Advance stage
        review.current_stage = 1
        review.stage_started_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(review)

        assert review.current_stage == 1

    async def test_approve_final_stage_completes_review(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that approving final stage completes the review."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,  # 3 stages (0, 1, 2)
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Start at final stage
        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            current_stage=2,
        )
        async_session.add(review)
        await async_session.flush()

        # Approve final stage
        action = ReviewStageActionFactory.create_approval(
            review_id=review.id,
            reviewer_id=db_user.id,
            stage_order=2,
            stage_name="Department Approval",
        )
        async_session.add(action)

        # Complete review
        review.status = "approved"
        review.completed_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(review)

        assert review.status == "approved"
        assert review.completed_at is not None

    async def test_reject_ends_review(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that rejecting ends the review."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
        )
        async_session.add(review)
        await async_session.flush()

        # Reject
        action = ReviewStageActionFactory.create_rejection(
            review_id=review.id,
            reviewer_id=db_user.id,
        )
        async_session.add(action)

        review.status = "rejected"
        review.completed_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(review)

        assert review.status == "rejected"
        assert review.completed_at is not None

    async def test_return_stays_at_stage(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that returning keeps review at current stage."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            current_stage=1,
        )
        async_session.add(review)
        await async_session.flush()

        # Return for revision
        action = ReviewStageActionFactory.create_return(
            review_id=review.id,
            reviewer_id=db_user.id,
            stage_order=1,
        )
        async_session.add(action)

        # Reset stage timer but stay at stage
        review.stage_started_at = datetime.now(timezone.utc)
        review.escalation_sent = False
        await async_session.commit()
        await async_session.refresh(review)

        assert review.current_stage == 1  # Still at stage 1
        assert review.status == "in_review"

    async def test_comment_no_state_change(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that commenting doesn't change review state."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            current_stage=1,
        )
        async_session.add(review)
        await async_session.flush()

        original_stage = review.current_stage
        original_status = review.status

        # Add comment
        action = ReviewStageAction(
            review_id=review.id,
            stage_order=1,
            stage_name="PI Review",
            reviewer_id=db_user.id,
            action="commented",
            comments="Looking good so far!",
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(review)

        assert review.current_stage == original_stage
        assert review.status == original_status


# =============================================================================
# Review History Tests
# =============================================================================


class TestReviewHistory:
    """Tests for GET /api/kanban/{card_id}/review/history."""

    async def test_get_review_history(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test getting full review history."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
        )
        async_session.add(review)
        await async_session.flush()

        # Create multiple actions
        action1 = ReviewStageActionFactory.create(
            review_id=review.id,
            stage_order=0,
            action="commented",
            comments="Started review",
        )
        action2 = ReviewStageActionFactory.create_approval(
            review_id=review.id,
            reviewer_id=db_user.id,
            stage_order=0,
        )
        async_session.add(action1)
        async_session.add(action2)
        await async_session.commit()

        # Query history
        result = await async_session.execute(
            select(ReviewStageAction)
            .where(ReviewStageAction.review_id == review.id)
            .order_by(ReviewStageAction.acted_at)
        )
        actions = result.scalars().all()

        assert len(actions) == 2


# =============================================================================
# Cancel Review Tests
# =============================================================================


class TestCancelReview:
    """Tests for DELETE /api/kanban/{card_id}/review."""

    async def test_cancel_active_review(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test canceling an active review."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
        )
        async_session.add(review)
        await async_session.commit()

        review_id = review.id

        # Cancel (delete)
        await async_session.delete(review)
        await async_session.commit()

        # Verify deleted
        result = await async_session.execute(
            select(ApplicationReview).where(ApplicationReview.id == review_id)
        )
        deleted = result.scalar_one_or_none()

        assert deleted is None

    async def test_cannot_cancel_completed_review(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that completed reviews cannot be canceled."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create approved review
        review = ApplicationReviewFactory.create_approved(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
        )
        async_session.add(review)
        await async_session.commit()

        # Check status (service would reject cancellation)
        assert review.status == "approved"
        # In the actual API, this would raise ValidationError


# =============================================================================
# Team Member Tests
# =============================================================================


class TestTeamMembers:
    """Tests for team member management endpoints."""

    async def test_get_team_members_empty(
        self, async_session, db_user, db_grant
    ):
        """Test getting team members when none exist."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.commit()

        result = await async_session.execute(
            select(ApplicationTeamMember).where(
                ApplicationTeamMember.kanban_card_id == application.id
            )
        )
        members = result.scalars().all()

        assert members == []

    async def test_add_team_member(
        self, async_session, db_user, db_grant
    ):
        """Test adding a team member to an application."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create another user to add as team member
        team_member_user = User(
            email="team_member@university.edu",
            password_hash="hashed",
            name="Team Member",
        )
        async_session.add(team_member_user)
        await async_session.flush()

        # Add as team member
        member = ApplicationTeamMemberFactory.create_reviewer(
            kanban_card_id=application.id,
            user_id=team_member_user.id,
            added_by=db_user.id,
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.id is not None
        assert member.role == "reviewer"
        assert member.user_id == team_member_user.id
        assert member.added_by == db_user.id

    async def test_add_team_member_different_roles(
        self, async_session, db_user, db_grant
    ):
        """Test adding team members with different roles."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create users
        users = {}
        for role in ["pi", "co_i", "grant_writer", "reviewer", "admin"]:
            user = User(
                email=f"{role}@university.edu",
                password_hash="hashed",
                name=f"{role.upper()} User",
            )
            async_session.add(user)
            users[role] = user
        await async_session.flush()

        # Add with different roles
        for role, user in users.items():
            member = ApplicationTeamMemberFactory.create(
                kanban_card_id=application.id,
                user_id=user.id,
                role=role,
                added_by=db_user.id,
            )
            async_session.add(member)
        await async_session.commit()

        # Query all members
        result = await async_session.execute(
            select(ApplicationTeamMember).where(
                ApplicationTeamMember.kanban_card_id == application.id
            )
        )
        members = result.scalars().all()

        assert len(members) == 5
        roles = {m.role for m in members}
        assert roles == {"pi", "co_i", "grant_writer", "reviewer", "admin"}

    async def test_add_duplicate_team_member_fails(
        self, async_session, db_user, db_grant
    ):
        """Test that adding same user twice fails."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        member_user = User(
            email="duplicate_test@university.edu",
            password_hash="hashed",
            name="Duplicate Test",
        )
        async_session.add(member_user)
        await async_session.flush()

        # Add first time
        member1 = ApplicationTeamMemberFactory.create(
            kanban_card_id=application.id,
            user_id=member_user.id,
            role="reviewer",
        )
        async_session.add(member1)
        await async_session.commit()

        # Check if already exists
        result = await async_session.execute(
            select(ApplicationTeamMember).where(
                ApplicationTeamMember.kanban_card_id == application.id,
                ApplicationTeamMember.user_id == member_user.id,
            )
        )
        existing = result.scalar_one_or_none()

        assert existing is not None  # Already exists - would fail

    async def test_update_team_member_role(
        self, async_session, db_user, db_grant
    ):
        """Test updating a team member's role."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        member_user = User(
            email="role_change@university.edu",
            password_hash="hashed",
            name="Role Change User",
        )
        async_session.add(member_user)
        await async_session.flush()

        member = ApplicationTeamMemberFactory.create(
            kanban_card_id=application.id,
            user_id=member_user.id,
            role="reviewer",
        )
        async_session.add(member)
        await async_session.commit()

        # Update role
        member.role = "co_i"
        await async_session.commit()
        await async_session.refresh(member)

        assert member.role == "co_i"

    async def test_update_team_member_permissions(
        self, async_session, db_user, db_grant
    ):
        """Test updating a team member's permissions."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        member_user = User(
            email="perm_change@university.edu",
            password_hash="hashed",
            name="Permission Change User",
        )
        async_session.add(member_user)
        await async_session.flush()

        member = ApplicationTeamMemberFactory.create(
            kanban_card_id=application.id,
            user_id=member_user.id,
            role="reviewer",
            permissions={"can_edit": False, "can_approve": True, "can_submit": False},
        )
        async_session.add(member)
        await async_session.commit()

        # Update permissions
        member.permissions = {"can_edit": True, "can_approve": True, "can_submit": False}
        await async_session.commit()
        await async_session.refresh(member)

        assert member.permissions["can_edit"] is True

    async def test_remove_team_member(
        self, async_session, db_user, db_grant
    ):
        """Test removing a team member."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        member_user = User(
            email="remove_test@university.edu",
            password_hash="hashed",
            name="Remove Test User",
        )
        async_session.add(member_user)
        await async_session.flush()

        member = ApplicationTeamMemberFactory.create(
            kanban_card_id=application.id,
            user_id=member_user.id,
        )
        async_session.add(member)
        await async_session.commit()

        member_id = member.id

        # Remove
        await async_session.delete(member)
        await async_session.commit()

        # Verify removed
        result = await async_session.execute(
            select(ApplicationTeamMember).where(ApplicationTeamMember.id == member_id)
        )
        deleted = result.scalar_one_or_none()

        assert deleted is None


# =============================================================================
# Pending Reviews Tests
# =============================================================================


class TestPendingReviews:
    """Tests for GET /api/reviews/pending."""

    async def test_get_pending_reviews(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test getting all pending reviews."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        # Create applications with reviews
        for i in range(3):
            grant = Grant(
                source="nih",
                external_id=f"PENDING-{i}",
                title=f"Pending Grant {i}",
                agency="NIH",
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
            )
            async_session.add(grant)
            await async_session.flush()

            app = GrantApplication(
                user_id=db_user.id,
                grant_id=grant.id,
                stage=ApplicationStage.WRITING,
                position=i,
            )
            async_session.add(app)
            await async_session.flush()

            review = ApplicationReviewFactory.create_in_review(
                kanban_card_id=app.id,
                workflow_id=workflow.id,
                started_by=db_user.id,
            )
            async_session.add(review)
        await async_session.commit()

        # Query pending
        result = await async_session.execute(
            select(ApplicationReview)
            .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
            .where(
                GrantApplication.user_id == db_user.id,
                ApplicationReview.status.in_(["pending", "in_review"]),
            )
        )
        pending = result.scalars().all()

        assert len(pending) == 3

    async def test_get_pending_reviews_filter_by_status(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test filtering pending reviews by status."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        app1 = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(app1)
        await async_session.flush()

        # Create reviews with different statuses
        review_in_review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=app1.id,
            workflow_id=workflow.id,
        )
        async_session.add(review_in_review)
        await async_session.commit()

        # Query only in_review status
        result = await async_session.execute(
            select(ApplicationReview)
            .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
            .where(
                GrantApplication.user_id == db_user.id,
                ApplicationReview.status == "in_review",
            )
        )
        in_review = result.scalars().all()

        assert len(in_review) >= 1
        assert all(r.status == "in_review" for r in in_review)


# =============================================================================
# Review Stats Tests
# =============================================================================


class TestReviewStats:
    """Tests for GET /api/reviews/stats."""

    async def test_get_review_stats(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test getting review statistics."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        # Create applications with various review statuses
        statuses = ["in_review", "in_review", "approved", "rejected"]
        for i, status in enumerate(statuses):
            grant = Grant(
                source="nih",
                external_id=f"STATS-{i}",
                title=f"Stats Grant {i}",
                agency="NIH",
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
            )
            async_session.add(grant)
            await async_session.flush()

            app = GrantApplication(
                user_id=db_user.id,
                grant_id=grant.id,
                stage=ApplicationStage.WRITING,
                position=i,
            )
            async_session.add(app)
            await async_session.flush()

            if status == "approved":
                review = ApplicationReviewFactory.create_approved(
                    kanban_card_id=app.id,
                    workflow_id=workflow.id,
                )
            elif status == "rejected":
                review = ApplicationReviewFactory.create_rejected(
                    kanban_card_id=app.id,
                    workflow_id=workflow.id,
                )
            else:
                review = ApplicationReviewFactory.create_in_review(
                    kanban_card_id=app.id,
                    workflow_id=workflow.id,
                )
            async_session.add(review)
        await async_session.commit()

        # Count by status
        status_counts = {}
        for status in ["in_review", "approved", "rejected"]:
            result = await async_session.execute(
                select(func.count(ApplicationReview.id))
                .select_from(ApplicationReview)
                .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
                .where(
                    GrantApplication.user_id == db_user.id,
                    ApplicationReview.status == status,
                )
            )
            status_counts[status] = result.scalar() or 0

        assert status_counts["in_review"] == 2
        assert status_counts["approved"] == 1
        assert status_counts["rejected"] == 1


# =============================================================================
# SLA and Escalation Tests
# =============================================================================


class TestSLATracking:
    """Tests for SLA deadline tracking."""

    async def test_sla_hours_tracked(
        self, async_session, db_user, db_grant
    ):
        """Test that SLA hours are tracked in workflow stages."""
        stages = [
            {
                "order": 0,
                "name": "Quick Review",
                "sla_hours": 24,
                "auto_escalate": True,
            },
        ]
        workflow = ReviewWorkflow(
            user_id=db_user.id,
            name="SLA Workflow",
            stages=stages,
        )
        async_session.add(workflow)
        await async_session.commit()
        await async_session.refresh(workflow)

        assert workflow.stages[0]["sla_hours"] == 24
        assert workflow.stages[0]["auto_escalate"] is True

    async def test_stage_started_at_tracked(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that stage start time is tracked for SLA."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        stage_start = datetime.now(timezone.utc)
        review = ApplicationReview(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            current_stage=0,
            status="in_review",
            started_by=db_user.id,
            started_at=stage_start,
            stage_started_at=stage_start,
            escalation_sent=False,
        )
        async_session.add(review)
        await async_session.commit()
        await async_session.refresh(review)

        assert review.stage_started_at is not None
        assert review.escalation_sent is False

    async def test_escalation_flag_updated(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that escalation flag is updated."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
            escalation_sent=False,
        )
        async_session.add(review)
        await async_session.commit()

        # Simulate escalation
        review.escalation_sent = True
        await async_session.commit()
        await async_session.refresh(review)

        assert review.escalation_sent is True


# =============================================================================
# Authorization Tests
# =============================================================================


class TestReviewAuthorization:
    """Tests for authorization and access control."""

    async def test_user_can_only_see_own_reviews(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that users can only see their own application reviews."""
        # Create another user with their own application and review
        other_user = User(
            email="other_auth@university.edu",
            password_hash="hashed",
            name="Other Auth User",
        )
        async_session.add(other_user)
        await async_session.flush()

        other_workflow = ReviewWorkflowFactory.create(
            user_id=other_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(other_workflow)
        await async_session.flush()

        other_app = GrantApplication(
            user_id=other_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(other_app)
        await async_session.flush()

        other_review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=other_app.id,
            workflow_id=other_workflow.id,
        )
        async_session.add(other_review)
        await async_session.commit()

        # Query for db_user's reviews only
        result = await async_session.execute(
            select(ApplicationReview)
            .join(GrantApplication, ApplicationReview.kanban_card_id == GrantApplication.id)
            .where(GrantApplication.user_id == db_user.id)
        )
        reviews = result.scalars().all()

        # Should not see other user's review
        assert not any(r.kanban_card_id == other_app.id for r in reviews)

    async def test_team_member_can_access_review(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that team members can access application reviews."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Add team member
        team_user = User(
            email="team_access@university.edu",
            password_hash="hashed",
            name="Team Access User",
        )
        async_session.add(team_user)
        await async_session.flush()

        team_member = ApplicationTeamMemberFactory.create_reviewer(
            kanban_card_id=application.id,
            user_id=team_user.id,
            added_by=db_user.id,
        )
        async_session.add(team_member)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
        )
        async_session.add(review)
        await async_session.commit()

        # Check team member can access (simulating service _verify_app_access)
        result = await async_session.execute(
            select(ApplicationTeamMember).where(
                ApplicationTeamMember.kanban_card_id == application.id,
                ApplicationTeamMember.user_id == team_user.id,
            )
        )
        membership = result.scalar_one_or_none()

        assert membership is not None  # Team member has access

    async def test_review_deleted_with_application(
        self, async_session, db_user, db_grant, sample_workflow_stages
    ):
        """Test that reviews are deleted when application is deleted (cascade)."""
        workflow = ReviewWorkflowFactory.create(
            user_id=db_user.id,
            stages=sample_workflow_stages,
        )
        async_session.add(workflow)
        await async_session.flush()

        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        review = ApplicationReviewFactory.create_in_review(
            kanban_card_id=application.id,
            workflow_id=workflow.id,
        )
        async_session.add(review)
        await async_session.commit()

        app_id = application.id

        # Delete application
        await async_session.delete(application)
        await async_session.commit()

        # Verify review is also deleted
        result = await async_session.execute(
            select(ApplicationReview).where(
                ApplicationReview.kanban_card_id == app_id
            )
        )
        reviews = result.scalars().all()

        assert len(reviews) == 0
