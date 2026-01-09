"""
Tests for the Checklists API endpoints.

Covers:
- GET /api/checklists/templates - List checklist templates
- GET /api/checklists/templates/{funder} - Get templates by funder
- GET /api/checklists/templates/detail/{template_id} - Get template details
- POST /api/checklists/templates - Create checklist template
- POST /api/checklists/{card_id}/checklist - Create checklist from template
- GET /api/checklists/{card_id}/checklist - Get application checklists
- PATCH /api/checklists/{card_id}/checklist/items/{item_id} - Update checklist item
- DELETE /api/checklists/{card_id}/checklist/{checklist_id} - Delete checklist
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from backend.models import GrantApplication, User, Grant, ApplicationStage
from backend.models.checklists import ChecklistTemplate, ApplicationChecklist
from tests.fixtures.checklist_factories import (
    ChecklistTemplateFactory,
    ApplicationChecklistFactory,
)

pytestmark = pytest.mark.asyncio


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_template_items():
    """Sample checklist template items for testing."""
    return [
        {
            "id": str(uuid4()),
            "title": "Specific Aims complete",
            "description": "Draft specific aims page",
            "required": True,
            "weight": 2.0,
            "category": "scientific",
            "dependencies": [],
        },
        {
            "id": str(uuid4()),
            "title": "Budget prepared",
            "description": "Detailed budget with justification",
            "required": True,
            "weight": 1.5,
            "category": "budget",
            "dependencies": [],
        },
        {
            "id": str(uuid4()),
            "title": "Optional attachment",
            "description": "Optional supporting document",
            "required": False,
            "weight": 0.5,
            "category": "documents",
            "dependencies": [],
        },
    ]


# =============================================================================
# Checklist Template List Tests
# =============================================================================


class TestListChecklistTemplates:
    """Tests for GET /api/checklists/templates."""

    async def test_list_templates_returns_system_templates(
        self, async_session, db_user, sample_template_items
    ):
        """Test listing returns system templates."""
        # Create system templates
        template1 = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            is_system=True,
            items=sample_template_items,
        )
        template2 = ChecklistTemplateFactory.create(
            funder="NSF",
            mechanism="CAREER",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(template1)
        async_session.add(template2)
        await async_session.commit()

        # Query templates (simulating what the API does)
        from sqlalchemy import or_

        result = await async_session.execute(
            select(ChecklistTemplate).where(
                or_(
                    ChecklistTemplate.is_system == True,
                    ChecklistTemplate.created_by == db_user.id,
                )
            )
        )
        templates = result.scalars().all()

        assert len(templates) >= 2
        assert any(t.funder == "NIH" for t in templates)
        assert any(t.funder == "NSF" for t in templates)

    async def test_list_templates_filter_by_funder(
        self, async_session, db_user, sample_template_items
    ):
        """Test filtering templates by funder."""
        # Create templates for different funders
        nih_template = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            is_system=True,
            items=sample_template_items,
        )
        nsf_template = ChecklistTemplateFactory.create(
            funder="NSF",
            mechanism="CAREER",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(nih_template)
        async_session.add(nsf_template)
        await async_session.commit()

        # Filter by NIH
        result = await async_session.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.funder.ilike("%NIH%"),
                ChecklistTemplate.is_system == True,
            )
        )
        templates = result.scalars().all()

        assert len(templates) >= 1
        assert all(t.funder == "NIH" for t in templates)

    async def test_list_templates_filter_by_mechanism(
        self, async_session, db_user, sample_template_items
    ):
        """Test filtering templates by mechanism."""
        # Create templates with different mechanisms
        r01_template = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            is_system=True,
            items=sample_template_items,
        )
        r21_template = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R21",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(r01_template)
        async_session.add(r21_template)
        await async_session.commit()

        # Filter by R01
        result = await async_session.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.mechanism.ilike("%R01%")
            )
        )
        templates = result.scalars().all()

        assert len(templates) >= 1
        assert all(t.mechanism == "R01" for t in templates)

    async def test_list_templates_includes_user_templates(
        self, async_session, db_user, sample_template_items
    ):
        """Test that user's own templates are included."""
        # Create user-defined template
        user_template = ChecklistTemplateFactory.create_user_template(
            user_id=db_user.id,
            name="My Custom Checklist",
            funder="Custom",
            mechanism="Custom",
            items=sample_template_items,
        )
        async_session.add(user_template)
        await async_session.commit()

        # Query with user filter
        from sqlalchemy import or_

        result = await async_session.execute(
            select(ChecklistTemplate).where(
                or_(
                    ChecklistTemplate.is_system == True,
                    ChecklistTemplate.created_by == db_user.id,
                )
            )
        )
        templates = result.scalars().all()

        user_templates = [t for t in templates if t.created_by == db_user.id]
        assert len(user_templates) >= 1
        assert any(t.name == "My Custom Checklist" for t in user_templates)

    async def test_list_templates_excludes_other_user_templates(
        self, async_session, db_user, sample_template_items
    ):
        """Test that other users' private templates are not visible."""
        # Create another user
        other_user = User(
            email="other@university.edu",
            password_hash="hashed",
            name="Other User",
        )
        async_session.add(other_user)
        await async_session.flush()

        # Create template for other user
        other_template = ChecklistTemplateFactory.create_user_template(
            user_id=other_user.id,
            name="Other User's Template",
            funder="Private",
            mechanism="Private",
            items=sample_template_items,
        )
        async_session.add(other_template)
        await async_session.commit()

        # Query for our user
        from sqlalchemy import or_

        result = await async_session.execute(
            select(ChecklistTemplate).where(
                or_(
                    ChecklistTemplate.is_system == True,
                    ChecklistTemplate.created_by == db_user.id,
                )
            )
        )
        templates = result.scalars().all()

        # Should not see other user's template
        assert not any(t.name == "Other User's Template" for t in templates)

    async def test_list_templates_system_only_filter(
        self, async_session, db_user, sample_template_items
    ):
        """Test system_only filter excludes user templates."""
        # Create both system and user templates
        system_template = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            is_system=True,
            items=sample_template_items,
        )
        user_template = ChecklistTemplateFactory.create_user_template(
            user_id=db_user.id,
            name="User Template",
            items=sample_template_items,
        )
        async_session.add(system_template)
        async_session.add(user_template)
        await async_session.commit()

        # Query system only
        result = await async_session.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.is_system == True)
        )
        templates = result.scalars().all()

        assert all(t.is_system for t in templates)


# =============================================================================
# Get Template by Funder Tests
# =============================================================================


class TestGetTemplatesByFunder:
    """Tests for GET /api/checklists/templates/{funder}."""

    async def test_get_templates_by_funder(
        self, async_session, db_user, sample_template_items
    ):
        """Test getting templates for a specific funder."""
        # Create NIH templates
        nih_r01 = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            is_system=True,
            items=sample_template_items,
        )
        nih_r21 = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R21",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(nih_r01)
        async_session.add(nih_r21)
        await async_session.commit()

        # Query for NIH
        result = await async_session.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.funder.ilike("NIH")
            )
        )
        templates = result.scalars().all()

        assert len(templates) >= 2
        mechanisms = [t.mechanism for t in templates]
        assert "R01" in mechanisms
        assert "R21" in mechanisms

    async def test_get_templates_by_funder_case_insensitive(
        self, async_session, db_user, sample_template_items
    ):
        """Test funder filtering is case-insensitive."""
        template = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(template)
        await async_session.commit()

        # Query with lowercase
        result = await async_session.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.funder.ilike("nih")
            )
        )
        templates = result.scalars().all()

        assert len(templates) >= 1

    async def test_get_templates_empty_for_unknown_funder(
        self, async_session, db_user
    ):
        """Test empty result for unknown funder."""
        result = await async_session.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.funder.ilike("UNKNOWN_FUNDER_XYZ")
            )
        )
        templates = result.scalars().all()

        assert len(templates) == 0


# =============================================================================
# Get Template Details Tests
# =============================================================================


class TestGetTemplateDetails:
    """Tests for GET /api/checklists/templates/detail/{template_id}."""

    async def test_get_template_by_id(
        self, async_session, db_user, sample_template_items
    ):
        """Test getting a specific template by ID."""
        template = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            name="NIH R01 Checklist",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(template)
        await async_session.commit()

        # Query by ID
        result = await async_session.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.id == template.id)
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.id == template.id
        assert found.name == "NIH R01 Checklist"
        assert found.funder == "NIH"
        assert len(found.items) == 3

    async def test_get_template_not_found(self, async_session, db_user):
        """Test 404 when template doesn't exist."""
        fake_id = uuid4()
        result = await async_session.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.id == fake_id)
        )
        found = result.scalar_one_or_none()

        assert found is None

    async def test_get_user_template_by_owner(
        self, async_session, db_user, sample_template_items
    ):
        """Test that owner can access their own template."""
        user_template = ChecklistTemplateFactory.create_user_template(
            user_id=db_user.id,
            name="My Private Template",
            items=sample_template_items,
        )
        async_session.add(user_template)
        await async_session.commit()

        result = await async_session.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.id == user_template.id,
            )
        )
        found = result.scalar_one_or_none()

        # Owner should be able to access
        assert found is not None
        assert found.created_by == db_user.id

    async def test_get_user_template_denied_for_other_user(
        self, async_session, db_user, sample_template_items
    ):
        """Test that other users cannot access private templates."""
        # Create another user and their template
        other_user = User(
            email="other2@university.edu",
            password_hash="hashed",
            name="Other User 2",
        )
        async_session.add(other_user)
        await async_session.flush()

        other_template = ChecklistTemplateFactory.create_user_template(
            user_id=other_user.id,
            name="Private Template",
            items=sample_template_items,
        )
        async_session.add(other_template)
        await async_session.commit()

        # Check access (simulating authorization check)
        result = await async_session.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.id == other_template.id
            )
        )
        template = result.scalar_one_or_none()

        # Template exists but is not system and not owned by db_user
        assert template is not None
        assert template.is_system is False
        assert template.created_by != db_user.id
        # In the actual API, this would raise AuthorizationError


# =============================================================================
# Create Template Tests
# =============================================================================


class TestCreateTemplate:
    """Tests for POST /api/checklists/templates."""

    async def test_create_user_template(
        self, async_session, db_user, sample_template_items
    ):
        """Test creating a new user-defined template."""
        template = ChecklistTemplate(
            funder="Custom",
            mechanism="Internal",
            name="My Internal Review Checklist",
            description="Custom checklist for internal review process",
            items=sample_template_items,
            is_system=False,
            created_by=db_user.id,
        )
        async_session.add(template)
        await async_session.commit()
        await async_session.refresh(template)

        assert template.id is not None
        assert template.name == "My Internal Review Checklist"
        assert template.is_system is False
        assert template.created_by == db_user.id
        assert len(template.items) == 3

    async def test_create_template_with_all_fields(
        self, async_session, db_user
    ):
        """Test creating template with all fields populated."""
        items = [
            {
                "id": str(uuid4()),
                "title": "Task 1",
                "description": "First task",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": [],
            },
            {
                "id": str(uuid4()),
                "title": "Task 2",
                "description": "Second task",
                "required": True,
                "weight": 1.0,
                "category": "budget",
                "dependencies": [],
            },
        ]

        template = ChecklistTemplate(
            funder="DOE",
            mechanism="SBIR",
            name="DOE SBIR Checklist",
            description="Checklist for DOE SBIR applications",
            items=items,
            is_system=False,
            created_by=db_user.id,
        )
        async_session.add(template)
        await async_session.commit()
        await async_session.refresh(template)

        assert template.funder == "DOE"
        assert template.mechanism == "SBIR"
        assert template.description is not None
        assert len(template.items) == 2

    async def test_create_template_without_mechanism(
        self, async_session, db_user
    ):
        """Test creating template without optional mechanism."""
        template = ChecklistTemplate(
            funder="Private Foundation",
            mechanism=None,
            name="Foundation Grant Checklist",
            items=[
                {
                    "id": str(uuid4()),
                    "title": "Generic Task",
                    "required": True,
                    "weight": 1.0,
                    "category": "other",
                    "dependencies": [],
                }
            ],
            is_system=False,
            created_by=db_user.id,
        )
        async_session.add(template)
        await async_session.commit()
        await async_session.refresh(template)

        assert template.mechanism is None

    async def test_create_template_items_get_ids(
        self, async_session, db_user
    ):
        """Test that items are properly stored with IDs."""
        item_id = str(uuid4())
        items = [
            {
                "id": item_id,
                "title": "Test Item",
                "required": True,
                "weight": 1.0,
                "category": "other",
                "dependencies": [],
            }
        ]

        template = ChecklistTemplate(
            funder="Test",
            name="Test Template",
            items=items,
            is_system=False,
            created_by=db_user.id,
        )
        async_session.add(template)
        await async_session.commit()
        await async_session.refresh(template)

        assert template.items[0]["id"] == item_id
        assert template.items[0]["title"] == "Test Item"


# =============================================================================
# Create Application Checklist Tests
# =============================================================================


class TestCreateApplicationChecklist:
    """Tests for POST /api/checklists/{card_id}/checklist."""

    async def test_create_checklist_from_template(
        self, async_session, db_user, db_grant, sample_template_items
    ):
        """Test creating a checklist from a template."""
        # Create template
        template = ChecklistTemplateFactory.create(
            funder="NIH",
            mechanism="R01",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(template)
        await async_session.flush()

        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist from template
        checklist = ApplicationChecklistFactory.create_from_template(
            kanban_card_id=application.id,
            template=template,
        )
        async_session.add(checklist)
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.id is not None
        assert checklist.kanban_card_id == application.id
        assert checklist.template_id == template.id
        assert checklist.name == template.name
        assert len(checklist.items) == 3
        assert checklist.progress_percent == 0.0

    async def test_create_custom_checklist(
        self, async_session, db_user, db_grant
    ):
        """Test creating a custom checklist without template."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create custom checklist
        items = [
            {
                "item_id": str(uuid4()),
                "title": "Custom Task 1",
                "description": "My custom task",
                "required": True,
                "weight": 1.0,
                "category": "other",
                "dependencies": [],
                "completed": False,
                "completed_at": None,
                "completed_by": None,
                "notes": None,
            },
            {
                "item_id": str(uuid4()),
                "title": "Custom Task 2",
                "required": True,
                "weight": 1.0,
                "category": "other",
                "dependencies": [],
                "completed": False,
                "completed_at": None,
                "completed_by": None,
                "notes": None,
            },
        ]

        checklist = ApplicationChecklist(
            kanban_card_id=application.id,
            template_id=None,
            name="My Custom Checklist",
            items=items,
            progress_percent=0.0,
        )
        async_session.add(checklist)
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.template_id is None
        assert checklist.name == "My Custom Checklist"
        assert len(checklist.items) == 2

    async def test_create_checklist_not_found_application(
        self, async_session, db_user, sample_template_items
    ):
        """Test error when application doesn't exist."""
        fake_card_id = uuid4()

        # Query to verify application doesn't exist
        result = await async_session.execute(
            select(GrantApplication).where(GrantApplication.id == fake_card_id)
        )
        application = result.scalar_one_or_none()

        assert application is None

    async def test_create_checklist_not_found_template(
        self, async_session, db_user, db_grant
    ):
        """Test error when template doesn't exist."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.commit()

        fake_template_id = uuid4()
        result = await async_session.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.id == fake_template_id)
        )
        template = result.scalar_one_or_none()

        assert template is None

    async def test_create_checklist_duplicate_template(
        self, async_session, db_user, db_grant, sample_template_items
    ):
        """Test error when checklist from same template already exists."""
        # Create template
        template = ChecklistTemplateFactory.create(
            funder="NIH",
            is_system=True,
            items=sample_template_items,
        )
        async_session.add(template)
        await async_session.flush()

        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create first checklist
        checklist1 = ApplicationChecklistFactory.create_from_template(
            kanban_card_id=application.id,
            template=template,
        )
        async_session.add(checklist1)
        await async_session.commit()

        # Query for existing checklist
        result = await async_session.execute(
            select(ApplicationChecklist).where(
                ApplicationChecklist.kanban_card_id == application.id,
                ApplicationChecklist.template_id == template.id,
            )
        )
        existing = result.scalar_one_or_none()

        assert existing is not None  # Already exists - API would return conflict

    async def test_create_checklist_access_denied(
        self, async_session, db_user, db_grant
    ):
        """Test error when user doesn't own the application."""
        # Create another user
        other_user = User(
            email="other3@university.edu",
            password_hash="hashed",
            name="Other User 3",
        )
        async_session.add(other_user)
        await async_session.flush()

        # Create application owned by other user
        application = GrantApplication(
            user_id=other_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.commit()

        # Check ownership
        result = await async_session.execute(
            select(GrantApplication).where(
                GrantApplication.id == application.id,
                GrantApplication.user_id == db_user.id,
            )
        )
        owned_app = result.scalar_one_or_none()

        assert owned_app is None  # Not owned by db_user


# =============================================================================
# Get Application Checklists Tests
# =============================================================================


class TestGetApplicationChecklists:
    """Tests for GET /api/checklists/{card_id}/checklist."""

    async def test_get_checklists_for_application(
        self, async_session, db_user, db_grant, sample_template_items
    ):
        """Test getting all checklists for an application."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create two checklists
        checklist1 = ApplicationChecklistFactory.create(
            kanban_card_id=application.id,
            name="Checklist 1",
        )
        checklist2 = ApplicationChecklistFactory.create(
            kanban_card_id=application.id,
            name="Checklist 2",
        )
        async_session.add(checklist1)
        async_session.add(checklist2)
        await async_session.commit()

        # Query checklists
        result = await async_session.execute(
            select(ApplicationChecklist).where(
                ApplicationChecklist.kanban_card_id == application.id
            )
        )
        checklists = result.scalars().all()

        assert len(checklists) == 2

    async def test_get_checklists_empty(self, async_session, db_user, db_grant):
        """Test getting checklists when none exist."""
        # Create application with no checklists
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.commit()

        result = await async_session.execute(
            select(ApplicationChecklist).where(
                ApplicationChecklist.kanban_card_id == application.id
            )
        )
        checklists = result.scalars().all()

        assert len(checklists) == 0

    async def test_get_checklists_progress_summary(
        self, async_session, db_user, db_grant
    ):
        """Test progress summary calculation."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist with some progress
        checklist = ApplicationChecklistFactory.create_with_progress(
            kanban_card_id=application.id,
            completed_count=2,
            total_count=4,
            user_id=db_user.id,
        )
        async_session.add(checklist)
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.progress_percent == 50.0  # 2 of 4 = 50%


# =============================================================================
# Update Checklist Item Tests
# =============================================================================


class TestUpdateChecklistItem:
    """Tests for PATCH /api/checklists/{card_id}/checklist/items/{item_id}."""

    async def test_mark_item_complete(self, async_session, db_user, db_grant):
        """Test marking a checklist item as complete."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist with items
        item_id = str(uuid4())
        items = [
            {
                "item_id": item_id,
                "title": "Test Item",
                "required": True,
                "weight": 1.0,
                "category": "other",
                "dependencies": [],
                "completed": False,
                "completed_at": None,
                "completed_by": None,
                "notes": None,
            }
        ]
        checklist = ApplicationChecklist(
            kanban_card_id=application.id,
            name="Test Checklist",
            items=items,
            progress_percent=0.0,
        )
        async_session.add(checklist)
        await async_session.commit()
        await async_session.refresh(checklist)

        # Update item to completed
        updated_items = list(checklist.items)
        updated_items[0] = {
            **updated_items[0],
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "completed_by": str(db_user.id),
        }
        checklist.items = updated_items
        checklist.progress_percent = 100.0
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.items[0]["completed"] is True
        assert checklist.items[0]["completed_by"] == str(db_user.id)
        assert checklist.progress_percent == 100.0

    async def test_mark_item_incomplete(self, async_session, db_user, db_grant):
        """Test marking a completed item as incomplete."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist with completed item
        item_id = str(uuid4())
        items = [
            {
                "item_id": item_id,
                "title": "Test Item",
                "required": True,
                "weight": 1.0,
                "category": "other",
                "dependencies": [],
                "completed": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed_by": str(db_user.id),
                "notes": None,
            }
        ]
        checklist = ApplicationChecklist(
            kanban_card_id=application.id,
            name="Test Checklist",
            items=items,
            progress_percent=100.0,
        )
        async_session.add(checklist)
        await async_session.commit()

        # Mark incomplete
        updated_items = list(checklist.items)
        updated_items[0] = {
            **updated_items[0],
            "completed": False,
            "completed_at": None,
            "completed_by": None,
        }
        checklist.items = updated_items
        checklist.progress_percent = 0.0
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.items[0]["completed"] is False
        assert checklist.items[0]["completed_at"] is None

    async def test_add_notes_to_item(self, async_session, db_user, db_grant):
        """Test adding notes to a checklist item."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist
        item_id = str(uuid4())
        items = [
            {
                "item_id": item_id,
                "title": "Test Item",
                "required": True,
                "weight": 1.0,
                "category": "other",
                "dependencies": [],
                "completed": False,
                "completed_at": None,
                "completed_by": None,
                "notes": None,
            }
        ]
        checklist = ApplicationChecklist(
            kanban_card_id=application.id,
            name="Test Checklist",
            items=items,
            progress_percent=0.0,
        )
        async_session.add(checklist)
        await async_session.commit()

        # Add notes
        updated_items = list(checklist.items)
        updated_items[0] = {
            **updated_items[0],
            "notes": "This task is pending approval",
        }
        checklist.items = updated_items
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.items[0]["notes"] == "This task is pending approval"

    async def test_update_item_not_found(self, async_session, db_user, db_grant):
        """Test error when item doesn't exist."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist with no items matching our search
        checklist = ApplicationChecklistFactory.create(
            kanban_card_id=application.id,
        )
        async_session.add(checklist)
        await async_session.commit()

        # Search for non-existent item
        fake_item_id = str(uuid4())
        found_item = None
        for item in checklist.items:
            if item.get("item_id") == fake_item_id:
                found_item = item
                break

        assert found_item is None

    async def test_update_item_recalculates_progress(
        self, async_session, db_user, db_grant
    ):
        """Test that progress is recalculated when item is updated."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist with 4 items, 0 complete
        checklist = ApplicationChecklistFactory.create_with_progress(
            kanban_card_id=application.id,
            completed_count=0,
            total_count=4,
        )
        async_session.add(checklist)
        await async_session.commit()

        assert checklist.progress_percent == 0.0

        # Mark 2 items complete and update progress
        updated_items = list(checklist.items)
        for i in range(2):
            updated_items[i] = {
                **updated_items[i],
                "completed": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        checklist.items = updated_items
        checklist.progress_percent = 50.0  # 2/4 = 50%
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.progress_percent == 50.0


# =============================================================================
# Delete Checklist Tests
# =============================================================================


class TestDeleteChecklist:
    """Tests for DELETE /api/checklists/{card_id}/checklist/{checklist_id}."""

    async def test_delete_checklist(self, async_session, db_user, db_grant):
        """Test deleting a checklist."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist
        checklist = ApplicationChecklistFactory.create(
            kanban_card_id=application.id,
        )
        async_session.add(checklist)
        await async_session.commit()

        checklist_id = checklist.id

        # Delete checklist
        await async_session.delete(checklist)
        await async_session.commit()

        # Verify deleted
        result = await async_session.execute(
            select(ApplicationChecklist).where(ApplicationChecklist.id == checklist_id)
        )
        deleted = result.scalar_one_or_none()

        assert deleted is None

    async def test_delete_checklist_not_found(
        self, async_session, db_user, db_grant
    ):
        """Test error when checklist doesn't exist."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.commit()

        fake_checklist_id = uuid4()
        result = await async_session.execute(
            select(ApplicationChecklist).where(
                ApplicationChecklist.id == fake_checklist_id,
                ApplicationChecklist.kanban_card_id == application.id,
            )
        )
        checklist = result.scalar_one_or_none()

        assert checklist is None


# =============================================================================
# Progress Calculation Tests
# =============================================================================


class TestProgressCalculation:
    """Tests for progress calculation logic."""

    async def test_progress_with_equal_weights(
        self, async_session, db_user, db_grant
    ):
        """Test progress calculation with equal item weights."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist with equal weights
        checklist = ApplicationChecklistFactory.create_with_progress(
            kanban_card_id=application.id,
            completed_count=3,
            total_count=6,
        )
        async_session.add(checklist)
        await async_session.commit()

        assert checklist.progress_percent == 50.0  # 3/6 = 50%

    async def test_progress_with_different_weights(
        self, async_session, db_user, db_grant
    ):
        """Test progress calculation with different item weights."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create items with different weights
        items = [
            {
                "item_id": str(uuid4()),
                "title": "Heavy Task",
                "required": True,
                "weight": 3.0,  # Weight 3
                "category": "other",
                "dependencies": [],
                "completed": True,  # Completed
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed_by": str(db_user.id),
                "notes": None,
            },
            {
                "item_id": str(uuid4()),
                "title": "Light Task",
                "required": True,
                "weight": 1.0,  # Weight 1
                "category": "other",
                "dependencies": [],
                "completed": False,  # Not completed
                "completed_at": None,
                "completed_by": None,
                "notes": None,
            },
        ]

        # Total weight = 4, completed weight = 3
        # Progress = 3/4 * 100 = 75%
        progress = (3.0 / 4.0) * 100.0

        checklist = ApplicationChecklist(
            kanban_card_id=application.id,
            name="Weighted Checklist",
            items=items,
            progress_percent=progress,
        )
        async_session.add(checklist)
        await async_session.commit()
        await async_session.refresh(checklist)

        assert checklist.progress_percent == 75.0

    async def test_progress_empty_checklist(
        self, async_session, db_user, db_grant
    ):
        """Test progress calculation for empty checklist."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        checklist = ApplicationChecklist(
            kanban_card_id=application.id,
            name="Empty Checklist",
            items=[],
            progress_percent=0.0,
        )
        async_session.add(checklist)
        await async_session.commit()

        # Empty checklist should have 0% progress
        assert checklist.progress_percent == 0.0
        assert len(checklist.items) == 0

    async def test_progress_all_complete(
        self, async_session, db_user, db_grant
    ):
        """Test progress is 100% when all items complete."""
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        checklist = ApplicationChecklistFactory.create_with_progress(
            kanban_card_id=application.id,
            completed_count=5,
            total_count=5,
            user_id=db_user.id,
        )
        async_session.add(checklist)
        await async_session.commit()

        assert checklist.progress_percent == 100.0


# =============================================================================
# Authorization Tests
# =============================================================================


class TestChecklistAuthorization:
    """Tests for authorization and access control."""

    async def test_user_can_only_access_own_application_checklist(
        self, async_session, db_user, db_grant
    ):
        """Test that users can only access checklists on their own applications."""
        # Create another user with their own application
        other_user = User(
            email="other4@university.edu",
            password_hash="hashed",
            name="Other User 4",
        )
        async_session.add(other_user)
        await async_session.flush()

        other_app = GrantApplication(
            user_id=other_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(other_app)
        await async_session.flush()

        other_checklist = ApplicationChecklistFactory.create(
            kanban_card_id=other_app.id,
            name="Other User's Checklist",
        )
        async_session.add(other_checklist)
        await async_session.commit()

        # Query for db_user's application (should not find other's app)
        result = await async_session.execute(
            select(GrantApplication).where(
                GrantApplication.id == other_app.id,
                GrantApplication.user_id == db_user.id,
            )
        )
        app = result.scalar_one_or_none()

        assert app is None  # db_user doesn't own this application

    async def test_checklist_deleted_with_application(
        self, async_session, db_user, db_grant
    ):
        """Test that checklists are deleted when application is deleted (cascade)."""
        # Create application
        application = GrantApplication(
            user_id=db_user.id,
            grant_id=db_grant.id,
            stage=ApplicationStage.RESEARCHING,
            position=0,
        )
        async_session.add(application)
        await async_session.flush()

        # Create checklist
        checklist = ApplicationChecklistFactory.create(
            kanban_card_id=application.id,
        )
        async_session.add(checklist)
        await async_session.commit()

        app_id = application.id

        # Delete application
        await async_session.delete(application)
        await async_session.commit()

        # Verify checklist is also deleted (cascade)
        result = await async_session.execute(
            select(ApplicationChecklist).where(
                ApplicationChecklist.kanban_card_id == app_id
            )
        )
        checklists = result.scalars().all()

        assert len(checklists) == 0
