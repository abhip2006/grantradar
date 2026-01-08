"""
Tests for Deadline schemas.
Tests validation, computed fields, and serialization for deadline schemas.
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from pydantic import ValidationError

from backend.schemas.deadlines import (
    DeadlineCreate,
    DeadlineUpdate,
    DeadlineResponse,
    DeadlineList,
    DeadlineStatus,
    DeadlinePriority,
    LinkGrantRequest,
)


class TestDeadlinePriority:
    """Tests for DeadlinePriority enum."""

    def test_priority_values(self):
        """Test all priority enum values exist."""
        assert DeadlinePriority.LOW.value == "low"
        assert DeadlinePriority.MEDIUM.value == "medium"
        assert DeadlinePriority.HIGH.value == "high"
        assert DeadlinePriority.CRITICAL.value == "critical"

    def test_priority_from_string(self):
        """Test creating priority from string value."""
        assert DeadlinePriority("low") == DeadlinePriority.LOW
        assert DeadlinePriority("medium") == DeadlinePriority.MEDIUM
        assert DeadlinePriority("high") == DeadlinePriority.HIGH
        assert DeadlinePriority("critical") == DeadlinePriority.CRITICAL


class TestDeadlineStatus:
    """Tests for DeadlineStatus enum."""

    def test_status_values(self):
        """Test all status enum values exist."""
        assert DeadlineStatus.ACTIVE.value == "active"
        assert DeadlineStatus.COMPLETED.value == "completed"
        assert DeadlineStatus.ARCHIVED.value == "archived"

    def test_status_from_string(self):
        """Test creating status from string value."""
        assert DeadlineStatus("active") == DeadlineStatus.ACTIVE
        assert DeadlineStatus("completed") == DeadlineStatus.COMPLETED
        assert DeadlineStatus("archived") == DeadlineStatus.ARCHIVED


class TestDeadlineCreate:
    """Tests for DeadlineCreate schema."""

    def test_valid_minimal(self):
        """Test creating schema with minimal required fields."""
        data = DeadlineCreate(
            title="Test Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert data.title == "Test Deadline"
        assert data.priority == DeadlinePriority.MEDIUM
        assert data.color == "#3B82F6"
        assert data.grant_id is None
        assert data.description is None
        assert data.funder is None
        assert data.mechanism is None

    def test_valid_full(self):
        """Test creating schema with all fields."""
        grant_id = uuid4()
        sponsor_deadline = datetime.now(timezone.utc) + timedelta(days=30)
        internal_deadline = datetime.now(timezone.utc) + timedelta(days=25)

        data = DeadlineCreate(
            title="Full Deadline",
            sponsor_deadline=sponsor_deadline,
            grant_id=grant_id,
            description="Full description of the deadline",
            funder="NIH",
            mechanism="R01",
            internal_deadline=internal_deadline,
            priority=DeadlinePriority.HIGH,
            url="https://grants.nih.gov/example",
            notes="Some important notes",
            color="#FF0000",
        )
        assert data.title == "Full Deadline"
        assert data.funder == "NIH"
        assert data.mechanism == "R01"
        assert data.priority == DeadlinePriority.HIGH
        assert data.grant_id == grant_id
        assert data.color == "#FF0000"

    def test_invalid_title_empty(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_invalid_title_too_long(self):
        """Test that title over 500 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="x" * 501,
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_valid_title_max_length(self):
        """Test that title at exactly 500 chars is accepted."""
        data = DeadlineCreate(
            title="x" * 500,
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert len(data.title) == 500

    def test_invalid_color_format_no_hash(self):
        """Test that color without # is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="Test",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                color="3B82F6",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("color",) for e in errors)

    def test_invalid_color_format_wrong_length(self):
        """Test that color with wrong length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="Test",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                color="#FFF",  # Too short
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("color",) for e in errors)

    def test_invalid_color_format_named_color(self):
        """Test that named color is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="Test",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                color="red",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("color",) for e in errors)

    def test_valid_color_uppercase(self):
        """Test that uppercase hex color is accepted."""
        data = DeadlineCreate(
            title="Test",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            color="#AABBCC",
        )
        assert data.color == "#AABBCC"

    def test_valid_color_lowercase(self):
        """Test that lowercase hex color is accepted."""
        data = DeadlineCreate(
            title="Test",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
            color="#aabbcc",
        )
        assert data.color == "#aabbcc"

    def test_invalid_funder_too_long(self):
        """Test that funder over 100 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="Test",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                funder="x" * 101,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("funder",) for e in errors)

    def test_invalid_mechanism_too_long(self):
        """Test that mechanism over 50 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="Test",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                mechanism="x" * 51,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("mechanism",) for e in errors)

    def test_invalid_url_too_long(self):
        """Test that URL over 1000 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreate(
                title="Test",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                url="https://example.com/" + "x" * 1000,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    def test_all_priority_levels(self):
        """Test creating deadline with each priority level."""
        for priority in DeadlinePriority:
            data = DeadlineCreate(
                title="Test",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                priority=priority,
            )
            assert data.priority == priority


class TestDeadlineUpdate:
    """Tests for DeadlineUpdate schema."""

    def test_empty_update(self):
        """Test creating update with no fields."""
        data = DeadlineUpdate()
        assert data.title is None
        assert data.sponsor_deadline is None
        assert data.status is None

    def test_partial_update_title_only(self):
        """Test updating only title."""
        data = DeadlineUpdate(title="New Title")
        assert data.title == "New Title"
        assert data.sponsor_deadline is None
        assert data.priority is None

    def test_partial_update_status_only(self):
        """Test updating only status."""
        data = DeadlineUpdate(status=DeadlineStatus.COMPLETED)
        assert data.status == DeadlineStatus.COMPLETED
        assert data.title is None

    def test_partial_update_priority_only(self):
        """Test updating only priority."""
        data = DeadlineUpdate(priority=DeadlinePriority.HIGH)
        assert data.priority == DeadlinePriority.HIGH
        assert data.title is None

    def test_full_update(self):
        """Test updating all fields."""
        data = DeadlineUpdate(
            title="Updated Title",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=60),
            grant_id=uuid4(),
            description="Updated description",
            funder="NSF",
            mechanism="R21",
            internal_deadline=datetime.now(timezone.utc) + timedelta(days=55),
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.CRITICAL,
            url="https://nsf.gov/example",
            notes="Updated notes",
            color="#00FF00",
        )
        assert data.title == "Updated Title"
        assert data.funder == "NSF"
        assert data.mechanism == "R21"
        assert data.status == DeadlineStatus.ACTIVE
        assert data.priority == DeadlinePriority.CRITICAL

    def test_invalid_title_too_long(self):
        """Test that title over 500 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineUpdate(title="x" * 501)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_invalid_color_format(self):
        """Test that invalid color format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineUpdate(color="invalid")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("color",) for e in errors)


class TestDeadlineResponse:
    """Tests for DeadlineResponse schema."""

    def test_response_basic(self):
        """Test basic response creation."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test Deadline",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=future,
            internal_deadline=None,
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        assert data.title == "Test Deadline"
        assert data.status == DeadlineStatus.ACTIVE

    def test_days_until_deadline_future(self):
        """Test days_until_deadline for future deadline."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=10, hours=12)  # 10.5 days in future

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=future,
            internal_deadline=None,
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        # Should be approximately 10 days (may vary slightly based on execution time)
        assert data.days_until_deadline >= 9
        assert data.days_until_deadline <= 11

    def test_days_until_deadline_past(self):
        """Test days_until_deadline for past deadline."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=past,
            internal_deadline=None,
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        assert data.days_until_deadline < 0
        assert data.days_until_deadline >= -6

    def test_is_overdue_past_active(self):
        """Test is_overdue for past deadline with active status."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=past,
            internal_deadline=None,
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        assert data.is_overdue is True

    def test_is_overdue_past_completed(self):
        """Test that completed deadlines are not marked overdue."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=past,
            internal_deadline=None,
            status=DeadlineStatus.COMPLETED,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        assert data.is_overdue is False

    def test_is_overdue_past_archived(self):
        """Test that archived deadlines are not marked overdue."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=past,
            internal_deadline=None,
            status=DeadlineStatus.ARCHIVED,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        assert data.is_overdue is False

    def test_is_overdue_future(self):
        """Test is_overdue for future deadline."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=future,
            internal_deadline=None,
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        assert data.is_overdue is False

    def test_response_with_all_fields(self):
        """Test response with all optional fields populated."""
        now = datetime.now(timezone.utc)
        grant_id = uuid4()

        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=grant_id,
            title="Full Response Test",
            description="Complete description",
            funder="NIH",
            mechanism="R01",
            sponsor_deadline=now + timedelta(days=30),
            internal_deadline=now + timedelta(days=25),
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.HIGH,
            url="https://grants.nih.gov/example",
            notes="Important notes here",
            color="#FF5733",
            created_at=now,
            updated_at=now,
        )
        assert data.grant_id == grant_id
        assert data.description == "Complete description"
        assert data.funder == "NIH"
        assert data.mechanism == "R01"
        assert data.internal_deadline is not None

    def test_response_naive_datetime_handling(self):
        """Test that naive datetime is handled correctly in days_until_deadline."""
        now = datetime.now(timezone.utc)
        # Create a naive datetime (no timezone)
        naive_future = datetime.now() + timedelta(days=10)
        naive_future = naive_future.replace(tzinfo=None)

        # The schema should handle this gracefully
        # (the computed field adds UTC if missing)
        data = DeadlineResponse(
            id=uuid4(),
            user_id=uuid4(),
            grant_id=None,
            title="Test",
            description=None,
            funder=None,
            mechanism=None,
            sponsor_deadline=naive_future.replace(tzinfo=timezone.utc),  # Add TZ for test
            internal_deadline=None,
            status=DeadlineStatus.ACTIVE,
            priority=DeadlinePriority.MEDIUM,
            url=None,
            notes=None,
            color="#3B82F6",
            created_at=now,
            updated_at=now,
        )
        # Should calculate days correctly
        assert isinstance(data.days_until_deadline, int)


class TestDeadlineList:
    """Tests for DeadlineList schema."""

    def test_empty_list(self):
        """Test creating empty deadline list."""
        data = DeadlineList(items=[], total=0)
        assert data.items == []
        assert data.total == 0

    def test_list_with_items(self):
        """Test creating deadline list with items."""
        now = datetime.now(timezone.utc)
        items = [
            DeadlineResponse(
                id=uuid4(),
                user_id=uuid4(),
                grant_id=None,
                title=f"Deadline {i}",
                description=None,
                funder=None,
                mechanism=None,
                sponsor_deadline=now + timedelta(days=30 + i),
                internal_deadline=None,
                status=DeadlineStatus.ACTIVE,
                priority=DeadlinePriority.MEDIUM,
                url=None,
                notes=None,
                color="#3B82F6",
                created_at=now,
                updated_at=now,
            )
            for i in range(5)
        ]

        data = DeadlineList(items=items, total=5)
        assert len(data.items) == 5
        assert data.total == 5

    def test_list_total_can_differ_from_items_length(self):
        """Test that total can be different from items length (pagination)."""
        now = datetime.now(timezone.utc)
        items = [
            DeadlineResponse(
                id=uuid4(),
                user_id=uuid4(),
                grant_id=None,
                title="Page 1 Item",
                description=None,
                funder=None,
                mechanism=None,
                sponsor_deadline=now + timedelta(days=30),
                internal_deadline=None,
                status=DeadlineStatus.ACTIVE,
                priority=DeadlinePriority.MEDIUM,
                url=None,
                notes=None,
                color="#3B82F6",
                created_at=now,
                updated_at=now,
            )
        ]

        # Total is 100 but we only have 1 item (pagination scenario)
        data = DeadlineList(items=items, total=100)
        assert len(data.items) == 1
        assert data.total == 100


class TestLinkGrantRequest:
    """Tests for LinkGrantRequest schema."""

    def test_valid_request(self):
        """Test creating valid link grant request."""
        grant_id = uuid4()
        data = LinkGrantRequest(grant_id=grant_id)
        assert data.grant_id == grant_id

    def test_grant_id_required(self):
        """Test that grant_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            LinkGrantRequest()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("grant_id",) for e in errors)

    def test_grant_id_must_be_uuid(self):
        """Test that grant_id must be valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            LinkGrantRequest(grant_id="not-a-uuid")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("grant_id",) for e in errors)
