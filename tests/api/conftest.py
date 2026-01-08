"""
API test fixtures.
Fixtures for testing deadline API endpoints and other API tests.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.models import Deadline, Grant, User


@pytest_asyncio.fixture
async def db_deadline(async_session, db_user):
    """Create a test deadline in the database."""
    deadline = Deadline(
        user_id=db_user.id,
        title="Test API Deadline",
        description="A test deadline for API testing",
        funder="NIH",
        mechanism="R01",
        sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        internal_deadline=datetime.now(timezone.utc) + timedelta(days=25),
        status="active",
        priority="high",
        url="https://grants.nih.gov/test",
        notes="Test notes",
        color="#3B82F6",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


@pytest_asyncio.fixture
async def db_deadlines_varied(async_session, db_user):
    """Create a varied set of deadlines for testing filters and sorting."""
    now = datetime.now(timezone.utc)
    deadlines = []

    # Create deadlines with different statuses
    for status in ["active", "completed", "archived"]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"{status.capitalize()} Deadline",
            sponsor_deadline=now + timedelta(days=30),
            status=status,
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    # Create deadlines with different priorities
    for priority in ["low", "medium", "high"]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"{priority.capitalize()} Priority Deadline",
            sponsor_deadline=now + timedelta(days=45),
            priority=priority,
            status="active",
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    # Create deadlines with different funders
    for funder in ["NIH", "NSF", "DOE"]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"{funder} Grant Deadline",
            sponsor_deadline=now + timedelta(days=60),
            funder=funder,
            status="active",
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    # Create deadlines at different times
    for days in [7, 14, 30, 60, 90]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"Deadline in {days} days",
            sponsor_deadline=now + timedelta(days=days),
            status="active",
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    await async_session.commit()

    for deadline in deadlines:
        await async_session.refresh(deadline)

    return deadlines


@pytest_asyncio.fixture
async def db_deadline_with_grant(async_session, db_user, db_grant):
    """Create a deadline linked to a grant."""
    deadline = Deadline(
        user_id=db_user.id,
        grant_id=db_grant.id,
        title=db_grant.title,
        funder=db_grant.agency,
        sponsor_deadline=db_grant.deadline,
        url=db_grant.url,
        status="active",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


@pytest_asyncio.fixture
async def db_overdue_deadline(async_session, db_user):
    """Create an overdue deadline for testing."""
    deadline = Deadline(
        user_id=db_user.id,
        title="Overdue Deadline",
        sponsor_deadline=datetime.now(timezone.utc) - timedelta(days=5),
        status="active",
        priority="high",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


@pytest_asyncio.fixture
async def db_urgent_deadline(async_session, db_user):
    """Create an urgent deadline (within 7 days) for testing."""
    deadline = Deadline(
        user_id=db_user.id,
        title="Urgent Deadline",
        sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=3),
        status="active",
        priority="high",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline
