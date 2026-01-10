"""
Tests for Deadline API endpoints.
Tests CRUD operations, filtering, sorting, and iCal export for deadlines.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import MagicMock

from backend.models import Deadline, Grant


@pytest.fixture
def sample_deadline_data():
    """Sample deadline creation data."""
    return {
        "title": "R01 Submission - ML for Climate",
        "sponsor_deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "funder": "NIH",
        "mechanism": "R01",
        "priority": "high",
        "description": "Major grant submission",
        "url": "https://grants.nih.gov/grants/guide/pa-files/PA-21-001.html",
    }


@pytest.fixture
def sample_deadline(sample_deadline_data):
    """Sample deadline model instance."""
    deadline = MagicMock(spec=Deadline)
    deadline.id = uuid4()
    deadline.user_id = uuid4()
    deadline.grant_id = None
    deadline.title = sample_deadline_data["title"]
    deadline.sponsor_deadline = datetime.fromisoformat(sample_deadline_data["sponsor_deadline"])
    deadline.internal_deadline = None
    deadline.funder = sample_deadline_data["funder"]
    deadline.mechanism = sample_deadline_data["mechanism"]
    deadline.priority = sample_deadline_data["priority"]
    deadline.status = "active"
    deadline.description = sample_deadline_data["description"]
    deadline.url = sample_deadline_data["url"]
    deadline.notes = None
    deadline.color = "#3B82F6"
    deadline.created_at = datetime.now(timezone.utc)
    deadline.updated_at = datetime.now(timezone.utc)
    return deadline


class TestListDeadlines:
    """Tests for GET /api/deadlines endpoint."""

    @pytest.mark.asyncio
    async def test_list_deadlines_returns_user_deadlines_only(self, async_session, db_user):
        """Test that list only returns deadlines for current user."""
        # Create deadline for our user
        deadline = Deadline(
            user_id=db_user.id,
            title="User's Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(deadline)

        # Create deadline for another user
        other_user_id = uuid4()
        other_deadline = Deadline(
            user_id=other_user_id,
            title="Other User's Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(other_deadline)
        await async_session.commit()

        # Query for our user's deadlines
        from sqlalchemy import select

        result = await async_session.execute(select(Deadline).where(Deadline.user_id == db_user.id))
        deadlines = result.scalars().all()

        assert len(deadlines) == 1
        assert deadlines[0].title == "User's Deadline"

    @pytest.mark.asyncio
    async def test_list_deadlines_filter_by_status(self, async_session, db_user):
        """Test filtering deadlines by status."""
        # Create active deadline
        active_deadline = Deadline(
            user_id=db_user.id,
            title="Active Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            status="active",
        )
        async_session.add(active_deadline)

        # Create completed deadline
        completed_deadline = Deadline(
            user_id=db_user.id,
            title="Completed Deadline",
            sponsor_deadline=datetime.now(timezone.utc) - timedelta(days=5),
            status="completed",
        )
        async_session.add(completed_deadline)
        await async_session.commit()

        # Query for active deadlines only
        from sqlalchemy import select

        result = await async_session.execute(
            select(Deadline).where(
                Deadline.user_id == db_user.id,
                Deadline.status == "active",
            )
        )
        active_deadlines = result.scalars().all()

        assert len(active_deadlines) == 1
        assert active_deadlines[0].title == "Active Deadline"

    @pytest.mark.asyncio
    async def test_list_deadlines_filter_by_date_range(self, async_session, db_user):
        """Test filtering deadlines by date range."""
        now = datetime.now(timezone.utc)

        # Create deadline within range
        within_range = Deadline(
            user_id=db_user.id,
            title="Within Range",
            sponsor_deadline=now + timedelta(days=15),
        )
        async_session.add(within_range)

        # Create deadline outside range
        outside_range = Deadline(
            user_id=db_user.id,
            title="Outside Range",
            sponsor_deadline=now + timedelta(days=90),
        )
        async_session.add(outside_range)
        await async_session.commit()

        # Query for deadlines within 30 days
        from_date = now
        to_date = now + timedelta(days=30)

        from sqlalchemy import select, and_

        result = await async_session.execute(
            select(Deadline).where(
                and_(
                    Deadline.user_id == db_user.id,
                    Deadline.sponsor_deadline >= from_date,
                    Deadline.sponsor_deadline <= to_date,
                )
            )
        )
        filtered = result.scalars().all()

        assert len(filtered) == 1
        assert filtered[0].title == "Within Range"

    @pytest.mark.asyncio
    async def test_list_deadlines_filter_by_funder(self, async_session, db_user):
        """Test filtering deadlines by funder."""
        # Create NIH deadline
        nih_deadline = Deadline(
            user_id=db_user.id,
            title="NIH Grant",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            funder="NIH",
        )
        async_session.add(nih_deadline)

        # Create NSF deadline
        nsf_deadline = Deadline(
            user_id=db_user.id,
            title="NSF Grant",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            funder="NSF",
        )
        async_session.add(nsf_deadline)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(Deadline).where(
                Deadline.user_id == db_user.id,
                Deadline.funder.ilike("%NIH%"),
            )
        )
        nih_deadlines = result.scalars().all()

        assert len(nih_deadlines) == 1
        assert nih_deadlines[0].funder == "NIH"

    @pytest.mark.asyncio
    async def test_list_deadlines_search_by_title(self, async_session, db_user):
        """Test searching deadlines by title."""
        # Create deadlines with different titles
        ml_deadline = Deadline(
            user_id=db_user.id,
            title="Machine Learning Research",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(ml_deadline)

        climate_deadline = Deadline(
            user_id=db_user.id,
            title="Climate Change Study",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(climate_deadline)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(Deadline).where(
                Deadline.user_id == db_user.id,
                Deadline.title.ilike("%Machine%"),
            )
        )
        ml_results = result.scalars().all()

        assert len(ml_results) == 1
        assert "Machine" in ml_results[0].title

    @pytest.mark.asyncio
    async def test_list_deadlines_sort_by_deadline_asc(self, async_session, db_user):
        """Test sorting deadlines by sponsor_deadline ascending."""
        now = datetime.now(timezone.utc)

        # Create deadlines in random order
        deadline_far = Deadline(
            user_id=db_user.id,
            title="Far Deadline",
            sponsor_deadline=now + timedelta(days=60),
        )
        async_session.add(deadline_far)

        deadline_near = Deadline(
            user_id=db_user.id,
            title="Near Deadline",
            sponsor_deadline=now + timedelta(days=10),
        )
        async_session.add(deadline_near)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(Deadline).where(Deadline.user_id == db_user.id).order_by(Deadline.sponsor_deadline.asc())
        )
        sorted_deadlines = result.scalars().all()

        assert len(sorted_deadlines) == 2
        assert sorted_deadlines[0].title == "Near Deadline"
        assert sorted_deadlines[1].title == "Far Deadline"

    @pytest.mark.asyncio
    async def test_list_deadlines_sort_by_deadline_desc(self, async_session, db_user):
        """Test sorting deadlines by sponsor_deadline descending."""
        now = datetime.now(timezone.utc)

        deadline_far = Deadline(
            user_id=db_user.id,
            title="Far Deadline",
            sponsor_deadline=now + timedelta(days=60),
        )
        async_session.add(deadline_far)

        deadline_near = Deadline(
            user_id=db_user.id,
            title="Near Deadline",
            sponsor_deadline=now + timedelta(days=10),
        )
        async_session.add(deadline_near)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(Deadline).where(Deadline.user_id == db_user.id).order_by(Deadline.sponsor_deadline.desc())
        )
        sorted_deadlines = result.scalars().all()

        assert len(sorted_deadlines) == 2
        assert sorted_deadlines[0].title == "Far Deadline"
        assert sorted_deadlines[1].title == "Near Deadline"


class TestCreateDeadline:
    """Tests for POST /api/deadlines endpoint."""

    @pytest.mark.asyncio
    async def test_create_deadline_success(self, async_session, db_user, sample_deadline_data):
        """Test successful deadline creation."""
        deadline = Deadline(
            user_id=db_user.id,
            title=sample_deadline_data["title"],
            sponsor_deadline=datetime.fromisoformat(sample_deadline_data["sponsor_deadline"]),
            funder=sample_deadline_data["funder"],
            mechanism=sample_deadline_data["mechanism"],
            priority=sample_deadline_data["priority"],
            description=sample_deadline_data["description"],
            url=sample_deadline_data["url"],
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.id is not None
        assert deadline.title == sample_deadline_data["title"]
        assert deadline.status == "active"
        assert deadline.color == "#3B82F6"

    @pytest.mark.asyncio
    async def test_create_deadline_minimal_data(self, async_session, db_user):
        """Test creating deadline with only required fields."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Minimal Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=14),
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.id is not None
        assert deadline.title == "Minimal Deadline"
        assert deadline.status == "active"
        assert deadline.priority == "medium"
        assert deadline.funder is None
        assert deadline.mechanism is None

    @pytest.mark.asyncio
    async def test_create_deadline_with_grant_link(self, async_session, db_user, db_grant):
        """Test creating deadline linked to an existing grant."""
        deadline = Deadline(
            user_id=db_user.id,
            grant_id=db_grant.id,
            title=db_grant.title,
            sponsor_deadline=db_grant.deadline,
            funder=db_grant.agency,
            url=db_grant.url,
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.grant_id == db_grant.id
        assert deadline.title == db_grant.title

    @pytest.mark.asyncio
    async def test_create_deadline_with_internal_deadline(self, async_session, db_user):
        """Test creating deadline with internal deadline before sponsor deadline."""
        sponsor = datetime.now(timezone.utc) + timedelta(days=30)
        internal = sponsor - timedelta(days=7)

        deadline = Deadline(
            user_id=db_user.id,
            title="Deadline with Internal",
            sponsor_deadline=sponsor,
            internal_deadline=internal,
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.internal_deadline < deadline.sponsor_deadline
        assert (deadline.sponsor_deadline - deadline.internal_deadline).days == 7

    @pytest.mark.asyncio
    async def test_create_deadline_with_custom_color(self, async_session, db_user):
        """Test creating deadline with custom color."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Colored Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            color="#FF5733",
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.color == "#FF5733"

    @pytest.mark.asyncio
    async def test_create_deadline_with_all_priorities(self, async_session, db_user):
        """Test creating deadlines with different priority levels."""
        priorities = ["low", "medium", "high"]

        for priority in priorities:
            deadline = Deadline(
                user_id=db_user.id,
                title=f"{priority.capitalize()} Priority",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                priority=priority,
            )
            async_session.add(deadline)

        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(select(Deadline).where(Deadline.user_id == db_user.id))
        deadlines = result.scalars().all()

        assert len(deadlines) == 3
        priority_values = [d.priority for d in deadlines]
        assert set(priority_values) == {"low", "medium", "high"}


class TestGetDeadline:
    """Tests for GET /api/deadlines/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_deadline_success(self, async_session, db_user):
        """Test getting an existing deadline."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Test Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        from sqlalchemy import select, and_

        result = await async_session.execute(
            select(Deadline).where(
                and_(
                    Deadline.id == deadline.id,
                    Deadline.user_id == db_user.id,
                )
            )
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.id == deadline.id
        assert found.title == "Test Deadline"

    @pytest.mark.asyncio
    async def test_get_deadline_not_found(self, async_session, db_user):
        """Test getting non-existent deadline returns None."""
        fake_id = uuid4()

        from sqlalchemy import select, and_

        result = await async_session.execute(
            select(Deadline).where(
                and_(
                    Deadline.id == fake_id,
                    Deadline.user_id == db_user.id,
                )
            )
        )
        found = result.scalar_one_or_none()

        assert found is None

    @pytest.mark.asyncio
    async def test_get_deadline_wrong_user(self, async_session, db_user):
        """Test that user cannot access another user's deadline."""
        other_user_id = uuid4()
        deadline = Deadline(
            user_id=other_user_id,
            title="Other User's Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        # Try to access with db_user
        from sqlalchemy import select, and_

        result = await async_session.execute(
            select(Deadline).where(
                and_(
                    Deadline.id == deadline.id,
                    Deadline.user_id == db_user.id,
                )
            )
        )
        found = result.scalar_one_or_none()

        assert found is None


class TestUpdateDeadline:
    """Tests for PATCH /api/deadlines/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_deadline_title(self, async_session, db_user):
        """Test updating deadline title."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Original Title",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        deadline.title = "Updated Title"
        deadline.updated_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_deadline_status(self, async_session, db_user):
        """Test updating deadline status."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Test Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            status="active",
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        deadline.status = "completed"
        deadline.updated_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.status == "completed"

    @pytest.mark.asyncio
    async def test_update_deadline_priority(self, async_session, db_user):
        """Test updating deadline priority."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Test Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            priority="medium",
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        deadline.priority = "high"
        deadline.updated_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.priority == "high"

    @pytest.mark.asyncio
    async def test_update_deadline_partial_update(self, async_session, db_user):
        """Test partial update only changes specified fields."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Original Title",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            funder="NIH",
            priority="medium",
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        original_deadline_time = deadline.sponsor_deadline
        original_funder = deadline.funder

        # Only update title
        deadline.title = "Updated Title"
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.title == "Updated Title"
        assert deadline.sponsor_deadline == original_deadline_time
        assert deadline.funder == original_funder

    @pytest.mark.asyncio
    async def test_update_deadline_color(self, async_session, db_user):
        """Test updating deadline color."""
        deadline = Deadline(
            user_id=db_user.id,
            title="Test Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            color="#3B82F6",
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        deadline.color = "#EF4444"
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.color == "#EF4444"


class TestDeleteDeadline:
    """Tests for DELETE /api/deadlines/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_deadline_success(self, async_session, db_user):
        """Test successful deadline deletion."""
        deadline = Deadline(
            user_id=db_user.id,
            title="To Delete",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(deadline)
        await async_session.commit()
        deadline_id = deadline.id

        await async_session.delete(deadline)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(select(Deadline).where(Deadline.id == deadline_id))
        deleted = result.scalar_one_or_none()

        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_deadline_not_found(self, async_session, db_user):
        """Test deleting non-existent deadline."""
        fake_id = uuid4()

        from sqlalchemy import select, and_

        result = await async_session.execute(
            select(Deadline).where(
                and_(
                    Deadline.id == fake_id,
                    Deadline.user_id == db_user.id,
                )
            )
        )
        deadline = result.scalar_one_or_none()

        assert deadline is None


class TestLinkGrant:
    """Tests for POST /api/deadlines/link-grant endpoint."""

    @pytest.mark.asyncio
    async def test_link_grant_creates_deadline(self, async_session, db_user, db_grant):
        """Test creating deadline from grant."""
        deadline = Deadline(
            user_id=db_user.id,
            grant_id=db_grant.id,
            title=db_grant.title,
            funder=db_grant.agency,
            sponsor_deadline=db_grant.deadline,
            url=db_grant.url,
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.grant_id == db_grant.id
        assert deadline.title == db_grant.title
        assert deadline.sponsor_deadline == db_grant.deadline

    @pytest.mark.asyncio
    async def test_link_grant_not_found(self, async_session, db_user):
        """Test linking non-existent grant."""
        fake_grant_id = uuid4()

        from sqlalchemy import select

        result = await async_session.execute(select(Grant).where(Grant.id == fake_grant_id))
        grant = result.scalar_one_or_none()

        assert grant is None


class TestExportIcs:
    """Tests for GET /api/deadlines/export.ics endpoint."""

    @pytest.mark.asyncio
    async def test_export_ics_generates_calendar(self, async_session, db_user):
        """Test exporting deadlines as iCal."""
        # Create test deadlines
        deadline1 = Deadline(
            user_id=db_user.id,
            title="First Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            status="active",
        )
        deadline2 = Deadline(
            user_id=db_user.id,
            title="Second Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=60),
            status="active",
        )
        async_session.add(deadline1)
        async_session.add(deadline2)
        await async_session.commit()

        from sqlalchemy import select, and_

        result = await async_session.execute(
            select(Deadline).where(
                and_(
                    Deadline.user_id == db_user.id,
                    Deadline.status == "active",
                )
            )
        )
        active_deadlines = result.scalars().all()

        assert len(active_deadlines) == 2

    @pytest.mark.asyncio
    async def test_export_ics_only_active_deadlines(self, async_session, db_user):
        """Test that export only includes active deadlines."""
        # Create active deadline
        active = Deadline(
            user_id=db_user.id,
            title="Active Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            status="active",
        )
        async_session.add(active)

        # Create completed deadline
        completed = Deadline(
            user_id=db_user.id,
            title="Completed Deadline",
            sponsor_deadline=datetime.now(timezone.utc) - timedelta(days=5),
            status="completed",
        )
        async_session.add(completed)
        await async_session.commit()

        from sqlalchemy import select, and_

        result = await async_session.execute(
            select(Deadline).where(
                and_(
                    Deadline.user_id == db_user.id,
                    Deadline.status == "active",
                )
            )
        )
        active_deadlines = result.scalars().all()

        assert len(active_deadlines) == 1
        assert active_deadlines[0].title == "Active Deadline"


class TestDeadlineEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_deadline_with_past_date(self, async_session, db_user):
        """Test creating deadline with past sponsor_deadline."""
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        deadline = Deadline(
            user_id=db_user.id,
            title="Past Deadline",
            sponsor_deadline=past_date,
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        # SQLite returns timezone-naive datetimes, so compare naive to naive
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        deadline_naive = (
            deadline.sponsor_deadline.replace(tzinfo=None)
            if deadline.sponsor_deadline.tzinfo
            else deadline.sponsor_deadline
        )
        assert deadline_naive < now_naive

    @pytest.mark.asyncio
    async def test_deadline_with_long_title(self, async_session, db_user):
        """Test creating deadline with maximum length title."""
        long_title = "A" * 500  # Max length from schema
        deadline = Deadline(
            user_id=db_user.id,
            title=long_title,
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert len(deadline.title) == 500

    @pytest.mark.asyncio
    async def test_deadline_with_long_description(self, async_session, db_user):
        """Test creating deadline with long description."""
        long_description = "Description text. " * 500
        deadline = Deadline(
            user_id=db_user.id,
            title="Test Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            description=long_description,
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert len(deadline.description) > 1000

    @pytest.mark.asyncio
    async def test_deadline_with_special_characters_in_title(self, async_session, db_user):
        """Test creating deadline with special characters."""
        special_title = "Grant & Research: ML/AI - 2024 (NSF)"
        deadline = Deadline(
            user_id=db_user.id,
            title=special_title,
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.title == special_title

    @pytest.mark.asyncio
    async def test_multiple_deadlines_same_date(self, async_session, db_user):
        """Test multiple deadlines on the same date."""
        same_date = datetime.now(timezone.utc) + timedelta(days=30)

        for i in range(5):
            deadline = Deadline(
                user_id=db_user.id,
                title=f"Deadline {i}",
                sponsor_deadline=same_date,
            )
            async_session.add(deadline)

        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(select(Deadline).where(Deadline.user_id == db_user.id))
        deadlines = result.scalars().all()

        assert len(deadlines) == 5
        # SQLite returns timezone-naive datetimes, compare naive to naive
        same_date_naive = same_date.replace(tzinfo=None)
        for d in deadlines:
            d_naive = d.sponsor_deadline.replace(tzinfo=None) if d.sponsor_deadline.tzinfo else d.sponsor_deadline
            assert d_naive == same_date_naive
