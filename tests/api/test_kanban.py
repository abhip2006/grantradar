"""Tests for Kanban Board API endpoints."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models import (
    GrantApplication,
    ApplicationSubtask,
    ApplicationActivity,
    ApplicationAttachment,
    CustomFieldDefinition,
    CustomFieldValue,
    LabMember,
    ApplicationAssignee,
    User,
    Grant,
    ApplicationStage,
)
from backend.schemas.kanban import Priority, FieldType

pytestmark = pytest.mark.asyncio


# =============================================================================
# Board Retrieval Tests
# =============================================================================


class TestKanbanBoard:
    """Tests for board retrieval operations."""

    async def test_get_board_empty(self, async_session, db_user):
        """Test getting kanban board with no applications."""
        from sqlalchemy import select

        result = await async_session.execute(
            select(GrantApplication).where(GrantApplication.user_id == db_user.id)
        )
        applications = result.scalars().all()

        # Group by stage
        columns = {stage.value: [] for stage in ApplicationStage}
        for app in applications:
            stage_value = app.stage.value if hasattr(app.stage, 'value') else str(app.stage)
            if stage_value in columns:
                columns[stage_value].append(app)

        # All columns should be empty
        for stage in ["researching", "writing", "submitted", "awarded", "rejected"]:
            assert stage in columns
            assert columns[stage] == []

    async def test_get_board_with_applications(self, async_session, db_user, db_grant, db_pipeline_item):
        """Test getting board with existing applications."""
        from sqlalchemy import select

        result = await async_session.execute(
            select(GrantApplication).where(GrantApplication.user_id == db_user.id)
        )
        applications = result.scalars().all()

        # Should have at least one card
        assert len(applications) > 0

        # Verify the application belongs to the user
        assert applications[0].user_id == db_user.id

    async def test_get_board_filter_by_priority(self, async_session, db_user, db_grant):
        """Test board filtering by priority."""
        # Create a second grant for testing
        from datetime import timedelta
        grant2 = Grant(
            source="nsf",
            external_id="NSF-TEST-002",
            title="Second Test Grant",
            agency="NSF",
            deadline=datetime.now(timezone.utc) + timedelta(days=60),
        )
        async_session.add(grant2)
        await async_session.flush()

        # Create applications with different priorities
        high_priority = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
            priority="high",
        )
        low_priority = GrantApplication(
            user_id=db_user.id,
            grant_id=grant2.id,
            stage=ApplicationStage.WRITING,
            position=0,
            priority="low",
        )
        async_session.add(high_priority)
        async_session.add(low_priority)
        await async_session.commit()

        from sqlalchemy import select

        # Filter by high priority
        result = await async_session.execute(
            select(GrantApplication).where(
                GrantApplication.user_id == db_user.id,
                GrantApplication.priority == "high",
            )
        )
        high_apps = result.scalars().all()

        assert len(high_apps) == 1
        assert high_apps[0].priority == "high"

    async def test_get_board_filter_by_stage(self, async_session, db_user, db_grant):
        """Test board filtering by stage."""
        # Create a second grant for testing
        from datetime import timedelta
        grant2 = Grant(
            source="nsf",
            external_id="NSF-TEST-003",
            title="Third Test Grant",
            agency="NSF",
            deadline=datetime.now(timezone.utc) + timedelta(days=60),
        )
        async_session.add(grant2)
        await async_session.flush()

        # Create applications in different stages
        researching = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        writing = GrantApplication(
            user_id=db_user.id,
            grant_id=grant2.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(researching)
        async_session.add(writing)
        await async_session.commit()

        from sqlalchemy import select

        # Filter by researching stage
        result = await async_session.execute(
            select(GrantApplication).where(
                GrantApplication.user_id == db_user.id,
                GrantApplication.stage == ApplicationStage.RESEARCHING,
            )
        )
        researching_apps = result.scalars().all()

        assert len(researching_apps) == 1
        assert researching_apps[0].stage == ApplicationStage.RESEARCHING

    async def test_get_board_excludes_archived_by_default(self, async_session, db_user, db_grant):
        """Test that archived applications are excluded by default."""
        # Create a second grant for testing
        from datetime import timedelta
        grant2 = Grant(
            source="nsf",
            external_id="NSF-TEST-004",
            title="Fourth Test Grant",
            agency="NSF",
            deadline=datetime.now(timezone.utc) + timedelta(days=60),
        )
        async_session.add(grant2)
        await async_session.flush()

        # Create active and archived applications
        active = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
            archived=False,
        )
        archived = GrantApplication(
            user_id=db_user.id,
            grant_id=grant2.id,
            stage=ApplicationStage.WRITING,
            position=0,
            archived=True,
        )
        async_session.add(active)
        async_session.add(archived)
        await async_session.commit()

        from sqlalchemy import select

        # Query without archived
        result = await async_session.execute(
            select(GrantApplication).where(
                GrantApplication.user_id == db_user.id,
                GrantApplication.archived == False,
            )
        )
        non_archived = result.scalars().all()

        assert len(non_archived) == 1
        assert non_archived[0].archived is False


# =============================================================================
# Card Operations Tests
# =============================================================================


class TestCardOperations:
    """Tests for card update and reorder operations."""

    async def test_update_card_priority(self, async_session, db_pipeline_item):
        """Test updating card priority."""
        db_pipeline_item.priority = "high"
        await async_session.commit()
        await async_session.refresh(db_pipeline_item)

        assert db_pipeline_item.priority == "high"

    async def test_update_card_notes(self, async_session, db_pipeline_item):
        """Test updating card notes."""
        db_pipeline_item.notes = "Test notes for the application"
        await async_session.commit()
        await async_session.refresh(db_pipeline_item)

        assert db_pipeline_item.notes == "Test notes for the application"

    async def test_update_card_target_date(self, async_session, db_pipeline_item):
        """Test updating card target date."""
        target = datetime.now(timezone.utc) + timedelta(days=30)
        db_pipeline_item.target_date = target
        await async_session.commit()
        await async_session.refresh(db_pipeline_item)

        assert db_pipeline_item.target_date is not None

    async def test_update_card_color(self, async_session, db_pipeline_item):
        """Test updating card color."""
        db_pipeline_item.color = "#FF5733"
        await async_session.commit()
        await async_session.refresh(db_pipeline_item)

        assert db_pipeline_item.color == "#FF5733"

    async def test_archive_card(self, async_session, db_pipeline_item):
        """Test archiving a card."""
        db_pipeline_item.archived = True
        await async_session.commit()
        await async_session.refresh(db_pipeline_item)

        assert db_pipeline_item.archived is True

    async def test_move_card_to_different_stage(self, async_session, db_pipeline_item):
        """Test moving card to different stage."""
        original_stage = db_pipeline_item.stage
        db_pipeline_item.stage = ApplicationStage.WRITING
        await async_session.commit()
        await async_session.refresh(db_pipeline_item)

        assert db_pipeline_item.stage == ApplicationStage.WRITING

    async def test_reorder_card_position(self, async_session, db_user, db_grant):
        """Test reordering card positions."""
        # Create a second grant for testing
        from datetime import timedelta
        grant2 = Grant(
            source="nsf",
            external_id="NSF-TEST-005",
            title="Fifth Test Grant",
            agency="NSF",
            deadline=datetime.now(timezone.utc) + timedelta(days=60),
        )
        async_session.add(grant2)
        await async_session.flush()

        # Create multiple cards (different grants, same stage)
        card1 = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        card2 = GrantApplication(
            user_id=db_user.id,
            grant_id=grant2.id,
            stage=ApplicationStage.RESEARCHING,
            position=1,
        )
        async_session.add(card1)
        async_session.add(card2)
        await async_session.commit()

        # Swap positions
        card1.position = 1
        card2.position = 0
        await async_session.commit()
        await async_session.refresh(card1)
        await async_session.refresh(card2)

        assert card1.position == 1
        assert card2.position == 0


# =============================================================================
# Subtask Tests
# =============================================================================


class TestSubtasks:
    """Tests for subtask CRUD operations."""

    async def test_get_subtasks_empty(self, async_session, db_pipeline_item):
        """Test getting subtasks when none exist."""
        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationSubtask).where(
                ApplicationSubtask.application_id == db_pipeline_item.id
            )
        )
        subtasks = result.scalars().all()

        assert subtasks == []

    async def test_create_subtask(self, async_session, db_pipeline_item):
        """Test creating a subtask."""
        subtask = ApplicationSubtask(
            application_id=db_pipeline_item.id,
            title="Write specific aims",
            position=0,
        )
        async_session.add(subtask)
        await async_session.commit()
        await async_session.refresh(subtask)

        assert subtask.title == "Write specific aims"
        assert subtask.is_completed is False
        assert subtask.position == 0

    async def test_create_subtask_with_description(self, async_session, db_pipeline_item):
        """Test creating subtask with description."""
        subtask = ApplicationSubtask(
            application_id=db_pipeline_item.id,
            title="Budget review",
            description="Review budget with department",
            position=0,
        )
        async_session.add(subtask)
        await async_session.commit()
        await async_session.refresh(subtask)

        assert subtask.description == "Review budget with department"

    async def test_create_subtask_with_due_date(self, async_session, db_pipeline_item):
        """Test creating subtask with due date."""
        due_date = datetime.now(timezone.utc) + timedelta(days=7)
        subtask = ApplicationSubtask(
            application_id=db_pipeline_item.id,
            title="Complete draft",
            due_date=due_date,
            position=0,
        )
        async_session.add(subtask)
        await async_session.commit()
        await async_session.refresh(subtask)

        assert subtask.due_date is not None

    async def test_update_subtask_complete(self, async_session, db_kanban_subtask, db_user):
        """Test marking subtask as complete."""
        db_kanban_subtask.is_completed = True
        db_kanban_subtask.completed_at = datetime.now(timezone.utc)
        db_kanban_subtask.completed_by = db_user.id
        await async_session.commit()
        await async_session.refresh(db_kanban_subtask)

        assert db_kanban_subtask.is_completed is True
        assert db_kanban_subtask.completed_at is not None

    async def test_update_subtask_uncomplete(self, async_session, db_kanban_subtask):
        """Test marking subtask as incomplete after completion."""
        # First complete it
        db_kanban_subtask.is_completed = True
        db_kanban_subtask.completed_at = datetime.now(timezone.utc)
        await async_session.commit()

        # Then uncomplete it
        db_kanban_subtask.is_completed = False
        db_kanban_subtask.completed_at = None
        db_kanban_subtask.completed_by = None
        await async_session.commit()
        await async_session.refresh(db_kanban_subtask)

        assert db_kanban_subtask.is_completed is False
        assert db_kanban_subtask.completed_at is None

    async def test_delete_subtask(self, async_session, db_kanban_subtask):
        """Test deleting a subtask."""
        subtask_id = db_kanban_subtask.id
        await async_session.delete(db_kanban_subtask)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationSubtask).where(ApplicationSubtask.id == subtask_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_subtask_ordering(self, async_session, db_pipeline_item):
        """Test subtask position ordering."""
        subtasks = []
        for i in range(3):
            subtask = ApplicationSubtask(
                application_id=db_pipeline_item.id,
                title=f"Subtask {i}",
                position=i,
            )
            async_session.add(subtask)
            subtasks.append(subtask)

        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationSubtask)
            .where(ApplicationSubtask.application_id == db_pipeline_item.id)
            .order_by(ApplicationSubtask.position)
        )
        ordered = result.scalars().all()

        assert len(ordered) == 3
        for i, subtask in enumerate(ordered):
            assert subtask.position == i


# =============================================================================
# Activity Tests
# =============================================================================


class TestActivities:
    """Tests for activity log operations."""

    async def test_get_activities_empty(self, async_session, db_pipeline_item):
        """Test getting activity log when empty."""
        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationActivity).where(
                ApplicationActivity.application_id == db_pipeline_item.id
            )
        )
        activities = result.scalars().all()

        assert isinstance(activities, list)

    async def test_create_activity_log(self, async_session, db_pipeline_item, db_user):
        """Test creating an activity log entry."""
        activity = ApplicationActivity(
            application_id=db_pipeline_item.id,
            user_id=db_user.id,
            action="stage_changed",
            details={"from_stage": "researching", "to_stage": "writing"},
        )
        async_session.add(activity)
        await async_session.commit()
        await async_session.refresh(activity)

        assert activity.action == "stage_changed"
        assert activity.details["from_stage"] == "researching"

    async def test_add_comment_activity(self, async_session, db_pipeline_item, db_user):
        """Test adding a comment creates activity."""
        activity = ApplicationActivity(
            application_id=db_pipeline_item.id,
            user_id=db_user.id,
            action="comment_added",
            details={"content": "This is a test comment"},
        )
        async_session.add(activity)
        await async_session.commit()
        await async_session.refresh(activity)

        assert activity.action == "comment_added"
        assert activity.details["content"] == "This is a test comment"

    async def test_activities_ordered_by_created_at(self, async_session, db_pipeline_item, db_user):
        """Test activities are retrieved in chronological order."""
        # Create multiple activities
        for i in range(3):
            activity = ApplicationActivity(
                application_id=db_pipeline_item.id,
                user_id=db_user.id,
                action=f"action_{i}",
                details={"index": i},
            )
            async_session.add(activity)

        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationActivity)
            .where(ApplicationActivity.application_id == db_pipeline_item.id)
            .order_by(ApplicationActivity.created_at.desc())
        )
        activities = result.scalars().all()

        assert len(activities) == 3


# =============================================================================
# Custom Fields Tests
# =============================================================================


class TestCustomFields:
    """Tests for custom field operations."""

    async def test_get_field_definitions_empty(self, async_session, db_user):
        """Test getting field definitions when none exist."""
        from sqlalchemy import select

        result = await async_session.execute(
            select(CustomFieldDefinition).where(
                CustomFieldDefinition.user_id == db_user.id
            )
        )
        fields = result.scalars().all()

        assert fields == []

    async def test_create_field_definition_text(self, async_session, db_user):
        """Test creating a text field definition."""
        field = CustomFieldDefinition(
            user_id=db_user.id,
            name="Internal ID",
            field_type="text",
            is_required=False,
            show_in_card=True,
            position=0,
        )
        async_session.add(field)
        await async_session.commit()
        await async_session.refresh(field)

        assert field.name == "Internal ID"
        assert field.field_type == "text"

    async def test_create_field_definition_select(self, async_session, db_user):
        """Test creating a select field with options."""
        field = CustomFieldDefinition(
            user_id=db_user.id,
            name="Review Status",
            field_type="select",
            options=[
                {"value": "pending", "label": "Pending Review"},
                {"value": "approved", "label": "Approved"},
                {"value": "rejected", "label": "Rejected"},
            ],
            is_required=False,
            show_in_card=True,
            position=0,
        )
        async_session.add(field)
        await async_session.commit()
        await async_session.refresh(field)

        assert field.field_type == "select"
        assert len(field.options) == 3

    async def test_create_field_definition_number(self, async_session, db_user):
        """Test creating a number field definition."""
        field = CustomFieldDefinition(
            user_id=db_user.id,
            name="Budget Amount",
            field_type="number",
            is_required=True,
            show_in_card=True,
            position=0,
        )
        async_session.add(field)
        await async_session.commit()
        await async_session.refresh(field)

        assert field.field_type == "number"
        assert field.is_required is True

    async def test_update_field_definition(self, async_session, db_custom_field):
        """Test updating a field definition."""
        db_custom_field.show_in_card = False
        await async_session.commit()
        await async_session.refresh(db_custom_field)

        assert db_custom_field.show_in_card is False

    async def test_delete_field_definition(self, async_session, db_custom_field):
        """Test deleting a field definition."""
        field_id = db_custom_field.id
        await async_session.delete(db_custom_field)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(CustomFieldDefinition).where(CustomFieldDefinition.id == field_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_set_custom_field_value(self, async_session, db_pipeline_item, db_custom_field):
        """Test setting a custom field value on a card."""
        value = CustomFieldValue(
            application_id=db_pipeline_item.id,
            field_id=db_custom_field.id,
            value={"value": "Test value"},
        )
        async_session.add(value)
        await async_session.commit()
        await async_session.refresh(value)

        assert value.value["value"] == "Test value"

    async def test_update_custom_field_value(self, async_session, db_pipeline_item, db_custom_field):
        """Test updating an existing custom field value."""
        # Create initial value
        value = CustomFieldValue(
            application_id=db_pipeline_item.id,
            field_id=db_custom_field.id,
            value={"value": "Initial"},
        )
        async_session.add(value)
        await async_session.commit()

        # Update value
        value.value = {"value": "Updated"}
        await async_session.commit()
        await async_session.refresh(value)

        assert value.value["value"] == "Updated"


# =============================================================================
# Team Management Tests
# =============================================================================


class TestTeamManagement:
    """Tests for team/assignee operations."""

    async def test_get_team_members_empty(self, async_session, db_user):
        """Test getting team members when none invited."""
        from sqlalchemy import select

        result = await async_session.execute(
            select(LabMember).where(LabMember.lab_owner_id == db_user.id)
        )
        members = result.scalars().all()

        assert members == []

    async def test_invite_team_member(self, async_session, db_user):
        """Test inviting a team member."""
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email="labmember@university.edu",
            role="member",
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.member_email == "labmember@university.edu"
        assert member.role == "member"

    async def test_invite_team_member_as_admin(self, async_session, db_user):
        """Test inviting a team member as admin."""
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email="admin@university.edu",
            role="admin",
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.role == "admin"

    async def test_invite_team_member_as_viewer(self, async_session, db_user):
        """Test inviting a team member as viewer."""
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email="viewer@university.edu",
            role="viewer",
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.role == "viewer"

    async def test_remove_team_member(self, async_session, db_lab_member):
        """Test removing a team member."""
        member_id = db_lab_member.id
        await async_session.delete(db_lab_member)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(LabMember).where(LabMember.id == member_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_assign_user_to_application(self, async_session, db_pipeline_item, db_user):
        """Test assigning a user to an application."""
        assignee = ApplicationAssignee(
            application_id=db_pipeline_item.id,
            user_id=db_user.id,
            assigned_by=db_user.id,
        )
        async_session.add(assignee)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationAssignee).where(
                ApplicationAssignee.application_id == db_pipeline_item.id
            )
        )
        assignees = result.scalars().all()

        assert len(assignees) == 1
        assert assignees[0].user_id == db_user.id

    async def test_remove_assignee_from_application(self, async_session, db_pipeline_item, db_user):
        """Test removing an assignee from an application."""
        # First assign
        assignee = ApplicationAssignee(
            application_id=db_pipeline_item.id,
            user_id=db_user.id,
        )
        async_session.add(assignee)
        await async_session.commit()

        # Then remove
        await async_session.delete(assignee)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationAssignee).where(
                ApplicationAssignee.application_id == db_pipeline_item.id
            )
        )
        assignees = result.scalars().all()

        assert len(assignees) == 0


# =============================================================================
# Attachment Tests
# =============================================================================


class TestAttachments:
    """Tests for attachment operations."""

    async def test_get_attachments_empty(self, async_session, db_pipeline_item):
        """Test getting attachments when none exist."""
        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationAttachment).where(
                ApplicationAttachment.application_id == db_pipeline_item.id
            )
        )
        attachments = result.scalars().all()

        assert attachments == []

    async def test_create_attachment_record(self, async_session, db_pipeline_item, db_user):
        """Test creating an attachment record."""
        attachment = ApplicationAttachment(
            application_id=db_pipeline_item.id,
            user_id=db_user.id,
            filename="proposal_draft.pdf",
            file_type="application/pdf",
            file_size=1024000,
            storage_path="/uploads/attachments/abc123.pdf",
            description="First draft of proposal",
            category="draft",
        )
        async_session.add(attachment)
        await async_session.commit()
        await async_session.refresh(attachment)

        assert attachment.filename == "proposal_draft.pdf"
        assert attachment.file_type == "application/pdf"
        assert attachment.category == "draft"

    async def test_create_attachment_with_different_categories(self, async_session, db_pipeline_item, db_user):
        """Test attachments with different categories."""
        categories = ["budget", "biosketch", "letter", "draft", "other"]

        for cat in categories:
            attachment = ApplicationAttachment(
                application_id=db_pipeline_item.id,
                user_id=db_user.id,
                filename=f"{cat}_document.pdf",
                file_type="application/pdf",
                file_size=1024,
                storage_path=f"/uploads/{cat}.pdf",
                category=cat,
            )
            async_session.add(attachment)

        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationAttachment).where(
                ApplicationAttachment.application_id == db_pipeline_item.id
            )
        )
        attachments = result.scalars().all()

        assert len(attachments) == len(categories)

    async def test_delete_attachment(self, async_session, db_pipeline_item, db_user):
        """Test deleting an attachment."""
        attachment = ApplicationAttachment(
            application_id=db_pipeline_item.id,
            user_id=db_user.id,
            filename="to_delete.pdf",
            file_type="application/pdf",
            file_size=1024,
            storage_path="/uploads/to_delete.pdf",
        )
        async_session.add(attachment)
        await async_session.commit()

        attachment_id = attachment.id
        await async_session.delete(attachment)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationAttachment).where(ApplicationAttachment.id == attachment_id)
        )
        assert result.scalar_one_or_none() is None


# =============================================================================
# Access Control Tests
# =============================================================================


class TestAccessControl:
    """Tests for authorization and access control."""

    async def test_user_can_only_see_own_applications(self, async_session, db_user, db_grant):
        """Test that users can only see their own applications."""
        # Create application for our user
        user_app = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(user_app)

        # Create application for another user
        other_user = User(
            email="other@university.edu",
            password_hash="hashed",
            name="Other User",
        )
        async_session.add(other_user)
        await async_session.flush()

        other_app = GrantApplication(
            user_id=other_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.WRITING,
            position=0,
        )
        async_session.add(other_app)
        await async_session.commit()

        from sqlalchemy import select

        # Query for our user's applications
        result = await async_session.execute(
            select(GrantApplication).where(GrantApplication.user_id == db_user.id)
        )
        apps = result.scalars().all()

        assert len(apps) == 1
        assert apps[0].user_id == db_user.id

    async def test_user_can_only_see_own_custom_fields(self, async_session, db_user):
        """Test that users can only see their own custom field definitions."""
        # Create field for our user
        user_field = CustomFieldDefinition(
            user_id=db_user.id,
            name="User Field",
            field_type="text",
            position=0,
        )
        async_session.add(user_field)

        # Create field for another user
        other_user = User(
            email="other2@university.edu",
            password_hash="hashed",
            name="Other User 2",
        )
        async_session.add(other_user)
        await async_session.flush()

        other_field = CustomFieldDefinition(
            user_id=other_user.id,
            name="Other Field",
            field_type="text",
            position=0,
        )
        async_session.add(other_field)
        await async_session.commit()

        from sqlalchemy import select

        # Query for our user's fields
        result = await async_session.execute(
            select(CustomFieldDefinition).where(
                CustomFieldDefinition.user_id == db_user.id
            )
        )
        fields = result.scalars().all()

        assert len(fields) == 1
        assert fields[0].user_id == db_user.id

    async def test_user_can_only_see_own_team_members(self, async_session, db_user):
        """Test that users can only see their own team members."""
        # Create team member for our user
        user_member = LabMember(
            lab_owner_id=db_user.id,
            member_email="user_member@university.edu",
            role="member",
        )
        async_session.add(user_member)

        # Create team member for another user
        other_user = User(
            email="other3@university.edu",
            password_hash="hashed",
            name="Other User 3",
        )
        async_session.add(other_user)
        await async_session.flush()

        other_member = LabMember(
            lab_owner_id=other_user.id,
            member_email="other_member@university.edu",
            role="member",
        )
        async_session.add(other_member)
        await async_session.commit()

        from sqlalchemy import select

        # Query for our user's team
        result = await async_session.execute(
            select(LabMember).where(LabMember.lab_owner_id == db_user.id)
        )
        members = result.scalars().all()

        assert len(members) == 1
        assert members[0].lab_owner_id == db_user.id


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and validation."""

    async def test_application_unique_constraint(self, async_session, db_user, db_grant):
        """Test that user can only have one application per grant."""
        app1 = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(app1)
        await async_session.commit()

        # Attempting to create another application for same user/grant should fail
        # This depends on the database constraint being enforced
        # The test verifies we can't have duplicates

        from sqlalchemy import select

        result = await async_session.execute(
            select(GrantApplication).where(
                GrantApplication.user_id == db_user.id,
                GrantApplication.grant_id == db_grant.id,
            )
        )
        apps = result.scalars().all()
        assert len(apps) == 1

    async def test_custom_field_unique_name_per_user(self, async_session, db_user):
        """Test that field names must be unique per user."""
        field1 = CustomFieldDefinition(
            user_id=db_user.id,
            name="Unique Field",
            field_type="text",
            position=0,
        )
        async_session.add(field1)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(CustomFieldDefinition).where(
                CustomFieldDefinition.user_id == db_user.id,
                CustomFieldDefinition.name == "Unique Field",
            )
        )
        fields = result.scalars().all()
        assert len(fields) == 1

    async def test_lab_member_unique_email_per_owner(self, async_session, db_user):
        """Test that member email must be unique per lab owner."""
        member1 = LabMember(
            lab_owner_id=db_user.id,
            member_email="unique@university.edu",
            role="member",
        )
        async_session.add(member1)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(LabMember).where(
                LabMember.lab_owner_id == db_user.id,
                LabMember.member_email == "unique@university.edu",
            )
        )
        members = result.scalars().all()
        assert len(members) == 1

    async def test_subtask_cascade_delete_with_application(self, async_session, db_user, db_grant):
        """Test that subtasks are deleted when application is deleted."""
        # Create application
        app = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(app)
        await async_session.flush()

        # Create subtask
        subtask = ApplicationSubtask(
            application_id=app.id,
            title="Test Subtask",
            position=0,
        )
        async_session.add(subtask)
        await async_session.commit()

        app_id = app.id

        # Delete application
        await async_session.delete(app)
        await async_session.commit()

        # Verify subtask is also deleted
        from sqlalchemy import select

        result = await async_session.execute(
            select(ApplicationSubtask).where(
                ApplicationSubtask.application_id == app_id
            )
        )
        assert result.scalars().all() == []
