"""
Tests for Team Collaboration API endpoints.
Tests member management, invitations, and activity tracking.
"""
import pytest
import pytest_asyncio
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User, LabMember, TeamActivityLog


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_second_user(async_session: AsyncSession) -> User:
    """Create a second user for team testing."""
    user = User(
        id=uuid4(),
        email="team_member@university.edu",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4eqZzJMnE8mFJGSq",
        name="Dr. Team Member",
        institution="Stanford University",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def db_pending_invitation(async_session: AsyncSession, db_user: User) -> LabMember:
    """Create a pending team invitation."""
    token = secrets.token_urlsafe(32)
    member = LabMember(
        lab_owner_id=db_user.id,
        member_email="pending@university.edu",
        role="member",
        invitation_status="pending",
        invitation_token=token,
        invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        permissions={
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
        },
    )
    async_session.add(member)
    await async_session.commit()
    await async_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def db_accepted_member(
    async_session: AsyncSession, db_user: User, db_second_user: User
) -> LabMember:
    """Create an accepted team member."""
    member = LabMember(
        lab_owner_id=db_user.id,
        member_email=db_second_user.email,
        member_user_id=db_second_user.id,
        role="member",
        invitation_status="accepted",
        accepted_at=datetime.now(timezone.utc),
        permissions={
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
        },
    )
    async_session.add(member)
    await async_session.commit()
    await async_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def db_admin_member(
    async_session: AsyncSession, db_user: User, db_second_user: User
) -> LabMember:
    """Create an admin team member."""
    member = LabMember(
        lab_owner_id=db_user.id,
        member_email=db_second_user.email,
        member_user_id=db_second_user.id,
        role="admin",
        invitation_status="accepted",
        accepted_at=datetime.now(timezone.utc),
        permissions={
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": True,
            "can_invite": True,
        },
    )
    async_session.add(member)
    await async_session.commit()
    await async_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def db_viewer_member(async_session: AsyncSession, db_user: User) -> LabMember:
    """Create a viewer (read-only) team member."""
    member = LabMember(
        lab_owner_id=db_user.id,
        member_email="viewer@university.edu",
        role="viewer",
        invitation_status="accepted",
        accepted_at=datetime.now(timezone.utc),
        permissions={
            "can_view": True,
            "can_edit": False,
            "can_create": False,
            "can_delete": False,
            "can_invite": False,
        },
    )
    async_session.add(member)
    await async_session.commit()
    await async_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def db_expired_invitation(async_session: AsyncSession, db_user: User) -> LabMember:
    """Create an expired invitation."""
    token = secrets.token_urlsafe(32)
    member = LabMember(
        lab_owner_id=db_user.id,
        member_email="expired@university.edu",
        role="member",
        invitation_status="pending",
        invitation_token=token,
        invitation_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        permissions={"can_view": True, "can_edit": False, "can_create": False, "can_delete": False, "can_invite": False},
    )
    async_session.add(member)
    await async_session.commit()
    await async_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def db_multiple_members(async_session: AsyncSession, db_user: User):
    """Create multiple team members with various statuses."""
    members = []

    # Pending members
    for i in range(3):
        token = secrets.token_urlsafe(32)
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email=f"pending{i}@university.edu",
            role="member",
            invitation_status="pending",
            invitation_token=token,
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            permissions={"can_view": True, "can_edit": True, "can_create": True, "can_delete": False, "can_invite": False},
        )
        async_session.add(member)
        members.append(member)

    # Accepted members
    for i in range(2):
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email=f"accepted{i}@university.edu",
            role="member" if i == 0 else "admin",
            invitation_status="accepted",
            accepted_at=datetime.now(timezone.utc),
            permissions={"can_view": True, "can_edit": True, "can_create": True, "can_delete": i == 1, "can_invite": i == 1},
        )
        async_session.add(member)
        members.append(member)

    # Declined member
    member = LabMember(
        lab_owner_id=db_user.id,
        member_email="declined@university.edu",
        role="member",
        invitation_status="declined",
        declined_at=datetime.now(timezone.utc),
        permissions={"can_view": True, "can_edit": False, "can_create": False, "can_delete": False, "can_invite": False},
    )
    async_session.add(member)
    members.append(member)

    await async_session.commit()
    for m in members:
        await async_session.refresh(m)

    return members


@pytest_asyncio.fixture
async def db_team_activity(async_session: AsyncSession, db_user: User) -> TeamActivityLog:
    """Create a team activity log entry."""
    activity = TeamActivityLog(
        lab_owner_id=db_user.id,
        actor_id=db_user.id,
        action_type="invitation_sent",
        entity_type="member",
        entity_name="new_member@university.edu",
        metadata_={"role": "member", "invitation_id": str(uuid4())},
    )
    async_session.add(activity)
    await async_session.commit()
    await async_session.refresh(activity)
    return activity


@pytest_asyncio.fixture
async def db_multiple_activities(async_session: AsyncSession, db_user: User):
    """Create multiple team activity log entries."""
    activities = []
    action_types = [
        "invitation_sent",
        "invitation_accepted",
        "role_changed",
        "member_removed",
        "permissions_updated",
    ]

    for i, action_type in enumerate(action_types):
        activity = TeamActivityLog(
            lab_owner_id=db_user.id,
            actor_id=db_user.id,
            action_type=action_type,
            entity_type="member",
            entity_name=f"member{i}@university.edu",
            metadata_={"detail": f"Activity {i}"},
            created_at=datetime.now(timezone.utc) - timedelta(hours=i),
        )
        async_session.add(activity)
        activities.append(activity)

    await async_session.commit()
    for a in activities:
        await async_session.refresh(a)

    return activities


# =============================================================================
# Member Listing Tests
# =============================================================================


class TestListTeamMembers:
    """Tests for GET /api/team endpoint."""

    @pytest.mark.asyncio
    async def test_list_members_empty(self, async_session: AsyncSession, db_user: User):
        """Test listing members when team is empty."""
        result = await async_session.execute(
            select(LabMember).where(LabMember.lab_owner_id == db_user.id)
        )
        members = result.scalars().all()
        assert len(members) == 0

    @pytest.mark.asyncio
    async def test_list_members_with_pending(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_pending_invitation: LabMember,
    ):
        """Test listing members includes pending invitations."""
        result = await async_session.execute(
            select(LabMember).where(LabMember.lab_owner_id == db_user.id)
        )
        members = result.scalars().all()
        assert len(members) == 1
        assert members[0].invitation_status == "pending"

    @pytest.mark.asyncio
    async def test_list_members_exclude_pending(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_multiple_members,
    ):
        """Test filtering to exclude pending invitations."""
        result = await async_session.execute(
            select(LabMember).where(
                LabMember.lab_owner_id == db_user.id,
                LabMember.invitation_status != "pending",
            )
        )
        members = result.scalars().all()
        # 2 accepted + 1 declined = 3
        assert len(members) == 3

    @pytest.mark.asyncio
    async def test_list_members_counts(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_multiple_members,
    ):
        """Test member count aggregation."""
        # Get counts
        total_result = await async_session.execute(
            select(func.count(LabMember.id)).where(
                LabMember.lab_owner_id == db_user.id
            )
        )
        total = total_result.scalar()

        pending_result = await async_session.execute(
            select(func.count(LabMember.id)).where(
                LabMember.lab_owner_id == db_user.id,
                LabMember.invitation_status == "pending",
            )
        )
        pending_count = pending_result.scalar()

        active_result = await async_session.execute(
            select(func.count(LabMember.id)).where(
                LabMember.lab_owner_id == db_user.id,
                LabMember.invitation_status == "accepted",
            )
        )
        active_count = active_result.scalar()

        assert total == 6
        assert pending_count == 3
        assert active_count == 2


# =============================================================================
# Invitation Tests
# =============================================================================


class TestSendInvitation:
    """Tests for POST /api/team/invite endpoint."""

    @pytest.mark.asyncio
    async def test_create_invitation_success(
        self, async_session: AsyncSession, db_user: User
    ):
        """Test creating a new invitation."""
        token = secrets.token_urlsafe(32)
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email="new@university.edu",
            role="member",
            invitation_status="pending",
            invitation_token=token,
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            permissions={"can_view": True, "can_edit": True, "can_create": True, "can_delete": False, "can_invite": False},
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.id is not None
        assert member.invitation_status == "pending"
        assert member.invitation_token == token
        assert member.invitation_expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_create_invitation_as_admin(
        self, async_session: AsyncSession, db_user: User
    ):
        """Test creating an admin invitation."""
        token = secrets.token_urlsafe(32)
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email="admin@university.edu",
            role="admin",
            invitation_status="pending",
            invitation_token=token,
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            permissions={"can_view": True, "can_edit": True, "can_create": True, "can_delete": True, "can_invite": True},
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.role == "admin"
        assert member.permissions["can_delete"] is True
        assert member.permissions["can_invite"] is True

    @pytest.mark.asyncio
    async def test_create_invitation_as_viewer(
        self, async_session: AsyncSession, db_user: User
    ):
        """Test creating a viewer invitation."""
        token = secrets.token_urlsafe(32)
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email="viewer@university.edu",
            role="viewer",
            invitation_status="pending",
            invitation_token=token,
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            permissions={"can_view": True, "can_edit": False, "can_create": False, "can_delete": False, "can_invite": False},
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.role == "viewer"
        assert member.permissions["can_edit"] is False
        assert member.permissions["can_create"] is False


class TestAcceptInvitation:
    """Tests for POST /api/team/invite/accept endpoint."""

    @pytest.mark.asyncio
    async def test_accept_invitation_success(
        self,
        async_session: AsyncSession,
        db_pending_invitation: LabMember,
        db_second_user: User,
    ):
        """Test accepting a valid invitation."""
        # Accept the invitation
        db_pending_invitation.invitation_status = "accepted"
        db_pending_invitation.accepted_at = datetime.now(timezone.utc)
        db_pending_invitation.member_user_id = db_second_user.id
        db_pending_invitation.invitation_token = None  # Clear token after use

        await async_session.commit()
        await async_session.refresh(db_pending_invitation)

        assert db_pending_invitation.invitation_status == "accepted"
        assert db_pending_invitation.accepted_at is not None
        assert db_pending_invitation.member_user_id == db_second_user.id
        assert db_pending_invitation.invitation_token is None

    @pytest.mark.asyncio
    async def test_accept_expired_invitation(
        self,
        async_session: AsyncSession,
        db_expired_invitation: LabMember,
    ):
        """Test that expired invitation cannot be accepted normally."""
        # Verify invitation is expired
        assert db_expired_invitation.invitation_expires_at < datetime.now(timezone.utc)
        assert db_expired_invitation.invitation_status == "pending"


class TestDeclineInvitation:
    """Tests for POST /api/team/invite/decline endpoint."""

    @pytest.mark.asyncio
    async def test_decline_invitation_success(
        self,
        async_session: AsyncSession,
        db_pending_invitation: LabMember,
    ):
        """Test declining an invitation."""
        db_pending_invitation.invitation_status = "declined"
        db_pending_invitation.declined_at = datetime.now(timezone.utc)
        db_pending_invitation.invitation_token = None

        await async_session.commit()
        await async_session.refresh(db_pending_invitation)

        assert db_pending_invitation.invitation_status == "declined"
        assert db_pending_invitation.declined_at is not None


class TestResendInvitation:
    """Tests for POST /api/team/invite/resend/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_resend_invitation_new_token(
        self,
        async_session: AsyncSession,
        db_pending_invitation: LabMember,
    ):
        """Test resending an invitation generates a new token."""
        old_token = db_pending_invitation.invitation_token
        old_expiry = db_pending_invitation.invitation_expires_at

        # Generate new token
        new_token = secrets.token_urlsafe(32)
        db_pending_invitation.invitation_token = new_token
        db_pending_invitation.invitation_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        await async_session.commit()
        await async_session.refresh(db_pending_invitation)

        assert db_pending_invitation.invitation_token != old_token
        assert db_pending_invitation.invitation_expires_at > old_expiry


class TestCancelInvitation:
    """Tests for DELETE /api/team/invite/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_invitation_success(
        self,
        async_session: AsyncSession,
        db_pending_invitation: LabMember,
    ):
        """Test cancelling a pending invitation."""
        db_pending_invitation.invitation_status = "cancelled"
        db_pending_invitation.invitation_token = None

        await async_session.commit()
        await async_session.refresh(db_pending_invitation)

        assert db_pending_invitation.invitation_status == "cancelled"


# =============================================================================
# Member Management Tests
# =============================================================================


class TestUpdateMember:
    """Tests for PATCH /api/team/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_member_role(
        self,
        async_session: AsyncSession,
        db_accepted_member: LabMember,
    ):
        """Test updating a member's role."""
        db_accepted_member.role = "admin"
        db_accepted_member.permissions = {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": True,
            "can_invite": True,
        }

        await async_session.commit()
        await async_session.refresh(db_accepted_member)

        assert db_accepted_member.role == "admin"
        assert db_accepted_member.permissions["can_delete"] is True
        assert db_accepted_member.permissions["can_invite"] is True

    @pytest.mark.asyncio
    async def test_update_member_permissions(
        self,
        async_session: AsyncSession,
        db_accepted_member: LabMember,
    ):
        """Test updating a member's permissions."""
        db_accepted_member.permissions = {
            "can_view": True,
            "can_edit": False,  # Changed
            "can_create": False,  # Changed
            "can_delete": False,
            "can_invite": False,
        }

        await async_session.commit()
        await async_session.refresh(db_accepted_member)

        assert db_accepted_member.permissions["can_edit"] is False
        assert db_accepted_member.permissions["can_create"] is False


class TestRemoveMember:
    """Tests for DELETE /api/team/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_member_success(
        self,
        async_session: AsyncSession,
        db_accepted_member: LabMember,
    ):
        """Test removing a team member."""
        member_id = db_accepted_member.id

        await async_session.delete(db_accepted_member)
        await async_session.commit()

        result = await async_session.execute(
            select(LabMember).where(LabMember.id == member_id)
        )
        assert result.scalar_one_or_none() is None


# =============================================================================
# Team Stats Tests
# =============================================================================


class TestTeamStats:
    """Tests for GET /api/team/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_team_stats(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_multiple_members,
    ):
        """Test getting team statistics."""
        # Total members
        total_result = await async_session.execute(
            select(func.count(LabMember.id)).where(
                LabMember.lab_owner_id == db_user.id
            )
        )
        total = total_result.scalar()

        # Pending invitations
        pending_result = await async_session.execute(
            select(func.count(LabMember.id)).where(
                LabMember.lab_owner_id == db_user.id,
                LabMember.invitation_status == "pending",
            )
        )
        pending = pending_result.scalar()

        # Declined invitations
        declined_result = await async_session.execute(
            select(func.count(LabMember.id)).where(
                LabMember.lab_owner_id == db_user.id,
                LabMember.invitation_status == "declined",
            )
        )
        declined = declined_result.scalar()

        assert total == 6
        assert pending == 3
        assert declined == 1


# =============================================================================
# Activity Feed Tests
# =============================================================================


class TestTeamActivity:
    """Tests for GET /api/team/activity endpoint."""

    @pytest.mark.asyncio
    async def test_get_activities(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_multiple_activities,
    ):
        """Test getting team activity feed."""
        result = await async_session.execute(
            select(TeamActivityLog)
            .where(TeamActivityLog.lab_owner_id == db_user.id)
            .order_by(TeamActivityLog.created_at.desc())
        )
        activities = result.scalars().all()

        assert len(activities) == 5

    @pytest.mark.asyncio
    async def test_filter_activities_by_action_type(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_multiple_activities,
    ):
        """Test filtering activities by action type."""
        result = await async_session.execute(
            select(TeamActivityLog).where(
                TeamActivityLog.lab_owner_id == db_user.id,
                TeamActivityLog.action_type == "invitation_sent",
            )
        )
        activities = result.scalars().all()

        assert len(activities) == 1
        assert activities[0].action_type == "invitation_sent"

    @pytest.mark.asyncio
    async def test_filter_activities_by_entity_type(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_multiple_activities,
    ):
        """Test filtering activities by entity type."""
        result = await async_session.execute(
            select(TeamActivityLog).where(
                TeamActivityLog.lab_owner_id == db_user.id,
                TeamActivityLog.entity_type == "member",
            )
        )
        activities = result.scalars().all()

        assert len(activities) == 5  # All activities are for members

    @pytest.mark.asyncio
    async def test_create_activity_log(
        self,
        async_session: AsyncSession,
        db_user: User,
    ):
        """Test creating an activity log entry."""
        activity = TeamActivityLog(
            lab_owner_id=db_user.id,
            actor_id=db_user.id,
            action_type="invitation_sent",
            entity_type="member",
            entity_name="new@university.edu",
            metadata_={"role": "member"},
        )
        async_session.add(activity)
        await async_session.commit()
        await async_session.refresh(activity)

        assert activity.id is not None
        assert activity.action_type == "invitation_sent"
        assert activity.metadata_["role"] == "member"


# =============================================================================
# Permission Tests
# =============================================================================


class TestPermissions:
    """Tests for role-based permissions."""

    @pytest.mark.asyncio
    async def test_admin_permissions(
        self,
        async_session: AsyncSession,
        db_admin_member: LabMember,
    ):
        """Test admin role has full permissions."""
        assert db_admin_member.permissions["can_view"] is True
        assert db_admin_member.permissions["can_edit"] is True
        assert db_admin_member.permissions["can_create"] is True
        assert db_admin_member.permissions["can_delete"] is True
        assert db_admin_member.permissions["can_invite"] is True

    @pytest.mark.asyncio
    async def test_member_permissions(
        self,
        async_session: AsyncSession,
        db_accepted_member: LabMember,
    ):
        """Test member role has appropriate permissions."""
        assert db_accepted_member.permissions["can_view"] is True
        assert db_accepted_member.permissions["can_edit"] is True
        assert db_accepted_member.permissions["can_create"] is True
        assert db_accepted_member.permissions["can_delete"] is False
        assert db_accepted_member.permissions["can_invite"] is False

    @pytest.mark.asyncio
    async def test_viewer_permissions(
        self,
        async_session: AsyncSession,
        db_viewer_member: LabMember,
    ):
        """Test viewer role has read-only permissions."""
        assert db_viewer_member.permissions["can_view"] is True
        assert db_viewer_member.permissions["can_edit"] is False
        assert db_viewer_member.permissions["can_create"] is False
        assert db_viewer_member.permissions["can_delete"] is False
        assert db_viewer_member.permissions["can_invite"] is False


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_invitation_token_uniqueness(
        self, async_session: AsyncSession, db_user: User
    ):
        """Test that invitation tokens are unique."""
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)

        member1 = LabMember(
            lab_owner_id=db_user.id,
            member_email="unique1@university.edu",
            role="member",
            invitation_status="pending",
            invitation_token=token1,
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        member2 = LabMember(
            lab_owner_id=db_user.id,
            member_email="unique2@university.edu",
            role="member",
            invitation_status="pending",
            invitation_token=token2,
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        async_session.add(member1)
        async_session.add(member2)
        await async_session.commit()

        assert member1.invitation_token != member2.invitation_token

    @pytest.mark.asyncio
    async def test_member_not_found(self, async_session: AsyncSession):
        """Test querying for non-existent member."""
        result = await async_session.execute(
            select(LabMember).where(LabMember.id == uuid4())
        )
        member = result.scalar_one_or_none()
        assert member is None

    @pytest.mark.asyncio
    async def test_cascade_delete_activities(
        self,
        async_session: AsyncSession,
        db_user: User,
        db_team_activity: TeamActivityLog,
    ):
        """Test that activities are cascade deleted with user."""
        activity_id = db_team_activity.id
        user_id = db_user.id

        # Delete the user (lab owner)
        await async_session.delete(db_user)
        await async_session.commit()

        # Activity should be deleted
        result = await async_session.execute(
            select(TeamActivityLog).where(TeamActivityLog.id == activity_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_member_with_null_permissions(
        self, async_session: AsyncSession, db_user: User
    ):
        """Test member with null permissions field."""
        member = LabMember(
            lab_owner_id=db_user.id,
            member_email="noperm@university.edu",
            role="member",
            invitation_status="pending",
            permissions=None,
        )
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)

        assert member.permissions is None

    @pytest.mark.asyncio
    async def test_activity_with_no_actor(
        self, async_session: AsyncSession, db_user: User
    ):
        """Test activity log entry with no actor (system action)."""
        activity = TeamActivityLog(
            lab_owner_id=db_user.id,
            actor_id=None,  # System action
            action_type="invitation_expired",
            entity_type="member",
            entity_name="expired@university.edu",
        )
        async_session.add(activity)
        await async_session.commit()
        await async_session.refresh(activity)

        assert activity.actor_id is None
        assert activity.action_type == "invitation_expired"


# =============================================================================
# Role Transitions Tests
# =============================================================================


class TestRoleTransitions:
    """Tests for transitioning between roles."""

    @pytest.mark.asyncio
    async def test_promote_member_to_admin(
        self,
        async_session: AsyncSession,
        db_accepted_member: LabMember,
    ):
        """Test promoting a member to admin."""
        original_role = db_accepted_member.role
        assert original_role == "member"

        db_accepted_member.role = "admin"
        db_accepted_member.permissions = {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": True,
            "can_invite": True,
        }

        await async_session.commit()
        await async_session.refresh(db_accepted_member)

        assert db_accepted_member.role == "admin"

    @pytest.mark.asyncio
    async def test_demote_admin_to_member(
        self,
        async_session: AsyncSession,
        db_admin_member: LabMember,
    ):
        """Test demoting an admin to member."""
        original_role = db_admin_member.role
        assert original_role == "admin"

        db_admin_member.role = "member"
        db_admin_member.permissions = {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
        }

        await async_session.commit()
        await async_session.refresh(db_admin_member)

        assert db_admin_member.role == "member"
        assert db_admin_member.permissions["can_delete"] is False

    @pytest.mark.asyncio
    async def test_demote_to_viewer(
        self,
        async_session: AsyncSession,
        db_accepted_member: LabMember,
    ):
        """Test demoting a member to viewer."""
        db_accepted_member.role = "viewer"
        db_accepted_member.permissions = {
            "can_view": True,
            "can_edit": False,
            "can_create": False,
            "can_delete": False,
            "can_invite": False,
        }

        await async_session.commit()
        await async_session.refresh(db_accepted_member)

        assert db_accepted_member.role == "viewer"
        assert db_accepted_member.permissions["can_edit"] is False
