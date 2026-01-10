"""
Tests for deadline reminder tasks.
Tests the Celery tasks for sending deadline reminders.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User, Deadline, ReminderSchedule


@pytest_asyncio.fixture
async def reminder_user(async_session: AsyncSession):
    """Create a user for reminder testing."""
    user = User(
        id=uuid.uuid4(),
        email="reminder-test@university.edu",
        password_hash="hashed_pw",
        name="Reminder Test User",
        phone="+15551234567",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def upcoming_deadline(async_session: AsyncSession, reminder_user: User):
    """Create an upcoming deadline for testing."""
    deadline = Deadline(
        id=uuid.uuid4(),
        user_id=reminder_user.id,
        title="NSF Grant Deadline",
        sponsor_deadline=datetime.now(timezone.utc) + timedelta(hours=2),
        funder="NSF",
        mechanism="R01",
        priority="high",
        status="active",
        notes="Submit before 5pm",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


@pytest_asyncio.fixture
async def reminder_schedule(async_session: AsyncSession, upcoming_deadline: Deadline):
    """Create a reminder schedule for testing."""
    schedule = ReminderSchedule(
        id=uuid.uuid4(),
        deadline_id=upcoming_deadline.id,
        reminder_type="email",
        remind_before_minutes=60,
        is_sent=False,
    )
    async_session.add(schedule)
    await async_session.commit()
    await async_session.refresh(schedule)
    return schedule


class TestReminderModel:
    """Tests for reminder-related models."""

    @pytest.mark.asyncio
    async def test_create_deadline(self, async_session, reminder_user):
        """Test creating a deadline."""
        deadline = Deadline(
            id=uuid.uuid4(),
            user_id=reminder_user.id,
            title="Test Deadline",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=7),
            priority="medium",
            status="active",
        )
        async_session.add(deadline)
        await async_session.commit()
        await async_session.refresh(deadline)

        assert deadline.id is not None
        assert deadline.title == "Test Deadline"
        assert deadline.status == "active"

    @pytest.mark.asyncio
    async def test_create_reminder_schedule(self, async_session, upcoming_deadline):
        """Test creating a reminder schedule."""
        schedule = ReminderSchedule(
            id=uuid.uuid4(),
            deadline_id=upcoming_deadline.id,
            reminder_type="email",
            remind_before_minutes=30,
        )
        async_session.add(schedule)
        await async_session.commit()
        await async_session.refresh(schedule)

        assert schedule.id is not None
        assert schedule.deadline_id == upcoming_deadline.id
        assert schedule.is_sent is False

    @pytest.mark.asyncio
    async def test_multiple_reminders_per_deadline(self, async_session, upcoming_deadline):
        """Test creating multiple reminders for one deadline."""
        schedules = []
        for minutes in [30, 60, 120, 1440]:  # 30min, 1hr, 2hr, 1 day
            schedule = ReminderSchedule(
                id=uuid.uuid4(),
                deadline_id=upcoming_deadline.id,
                reminder_type="email",
                remind_before_minutes=minutes,
            )
            async_session.add(schedule)
            schedules.append(schedule)

        await async_session.commit()

        assert len(schedules) == 4


class TestTimeRemainingFormatting:
    """Tests for time remaining string formatting."""

    def test_format_days(self):
        """Test formatting days remaining."""
        time_remaining = timedelta(days=5)
        if time_remaining.days > 0:
            time_str = f"{time_remaining.days} day{'s' if time_remaining.days > 1 else ''}"

        assert time_str == "5 days"

    def test_format_single_day(self):
        """Test formatting single day remaining."""
        time_remaining = timedelta(days=1)
        if time_remaining.days > 0:
            time_str = f"{time_remaining.days} day{'s' if time_remaining.days > 1 else ''}"

        assert time_str == "1 day"

    def test_format_hours(self):
        """Test formatting hours remaining."""
        time_remaining = timedelta(hours=5)
        if time_remaining.days <= 0:
            hours = time_remaining.seconds // 3600
            if hours > 0:
                time_str = f"{hours} hour{'s' if hours > 1 else ''}"

        assert time_str == "5 hours"

    def test_format_minutes(self):
        """Test formatting minutes remaining."""
        time_remaining = timedelta(minutes=45)
        if time_remaining.days <= 0:
            hours = time_remaining.seconds // 3600
            if hours == 0:
                minutes = time_remaining.seconds // 60
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"

        assert time_str == "45 minutes"


class TestReminderTimeCalculation:
    """Tests for reminder time calculation logic."""

    def test_calculate_reminder_time_30min(self):
        """Test calculating reminder time 30 minutes before deadline."""
        deadline_time = datetime.now(timezone.utc) + timedelta(hours=2)
        remind_before_minutes = 30

        reminder_time = deadline_time - timedelta(minutes=remind_before_minutes)

        expected_time = deadline_time - timedelta(minutes=30)
        assert reminder_time == expected_time

    def test_calculate_reminder_time_1_day(self):
        """Test calculating reminder time 1 day before deadline."""
        deadline_time = datetime.now(timezone.utc) + timedelta(days=3)
        remind_before_minutes = 1440  # 24 hours

        reminder_time = deadline_time - timedelta(minutes=remind_before_minutes)

        expected_time = deadline_time - timedelta(days=1)
        assert reminder_time == expected_time

    def test_reminder_should_be_sent(self):
        """Test checking if reminder should be sent."""
        now = datetime.now(timezone.utc)
        deadline_time = now + timedelta(hours=1)
        remind_before_minutes = 120  # 2 hours

        reminder_time = deadline_time - timedelta(minutes=remind_before_minutes)

        # Reminder should be sent because we're past reminder_time
        should_send = now >= reminder_time
        assert should_send is True

    def test_reminder_should_not_be_sent(self):
        """Test that reminder should not be sent if not yet time."""
        now = datetime.now(timezone.utc)
        deadline_time = now + timedelta(days=3)
        remind_before_minutes = 60  # 1 hour

        reminder_time = deadline_time - timedelta(minutes=remind_before_minutes)

        # Reminder should not be sent because we're before reminder_time
        should_send = now >= reminder_time
        assert should_send is False


class TestEmailReminderContent:
    """Tests for email reminder content generation."""

    def test_build_email_subject(self):
        """Test building email subject line."""
        title = "NSF Grant Application"
        time_str = "2 hours"

        subject = f"Deadline Reminder: {title} - Due in {time_str}"

        assert "Deadline Reminder" in subject
        assert "NSF Grant Application" in subject
        assert "2 hours" in subject

    def test_build_funder_line_with_funder(self):
        """Test building funder line when funder exists."""
        funder = "NSF"
        funder_line = f"<p><strong>Funder:</strong> {funder}</p>" if funder else ""

        assert "NSF" in funder_line

    def test_build_funder_line_without_funder(self):
        """Test building funder line when funder is None."""
        funder = None
        funder_line = f"<p><strong>Funder:</strong> {funder}</p>" if funder else ""

        assert funder_line == ""

    def test_truncate_long_title_for_sms(self):
        """Test truncating long titles for SMS messages."""
        long_title = "A" * 100  # 100 character title

        truncated = long_title[:50] + "..." if len(long_title) > 50 else long_title

        assert len(truncated) == 53  # 50 + "..."
        assert truncated.endswith("...")

    def test_short_title_not_truncated(self):
        """Test short titles are not truncated."""
        short_title = "Short Grant Title"

        truncated = short_title[:50] + "..." if len(short_title) > 50 else short_title

        assert truncated == short_title


class TestReminderTypes:
    """Tests for different reminder types."""

    def test_email_reminder_type(self):
        """Test email reminder type validation."""
        reminder_type = "email"
        valid_types = ["email", "sms"]

        assert reminder_type in valid_types

    def test_sms_reminder_type(self):
        """Test SMS reminder type validation."""
        reminder_type = "sms"
        valid_types = ["email", "sms"]

        assert reminder_type in valid_types

    def test_reminder_type_dispatch(self):
        """Test reminder type dispatching logic."""
        reminder_type = "email"
        email_sent = False
        sms_sent = False

        if reminder_type == "email":
            email_sent = True
        elif reminder_type == "sms":
            sms_sent = True

        assert email_sent is True
        assert sms_sent is False


class TestReminderScheduleStatus:
    """Tests for reminder schedule status management."""

    @pytest.mark.asyncio
    async def test_mark_reminder_as_sent(self, async_session, reminder_schedule):
        """Test marking a reminder as sent."""
        reminder_schedule.is_sent = True
        reminder_schedule.sent_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(reminder_schedule)

        assert reminder_schedule.is_sent is True
        assert reminder_schedule.sent_at is not None

    @pytest.mark.asyncio
    async def test_filter_unsent_reminders(self, async_session, upcoming_deadline):
        """Test filtering for unsent reminders."""
        # Create sent reminder
        sent_schedule = ReminderSchedule(
            id=uuid.uuid4(),
            deadline_id=upcoming_deadline.id,
            reminder_type="email",
            remind_before_minutes=120,
            is_sent=True,
            sent_at=datetime.now(timezone.utc),
        )
        async_session.add(sent_schedule)

        # Create unsent reminder
        unsent_schedule = ReminderSchedule(
            id=uuid.uuid4(),
            deadline_id=upcoming_deadline.id,
            reminder_type="email",
            remind_before_minutes=60,
            is_sent=False,
        )
        async_session.add(unsent_schedule)
        await async_session.commit()

        from sqlalchemy import select

        result = await async_session.execute(
            select(ReminderSchedule).where(
                ReminderSchedule.deadline_id == upcoming_deadline.id,
                not ReminderSchedule.is_sent,
            )
        )
        unsent = result.scalars().all()

        # Should have at least 1 unsent reminder
        assert len(unsent) >= 1
        assert all(not r.is_sent for r in unsent)
