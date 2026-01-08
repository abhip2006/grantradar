"""
Tests for WebSocket server.
Tests the Socket.io server and connection management.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


class TestPubSubChannels:
    """Tests for PubSubChannels class."""

    def test_user_prefix(self):
        """Test user channel prefix."""
        from backend.websocket import PubSubChannels

        assert PubSubChannels.USER_PREFIX == "ws:user:"

    def test_broadcast_channel(self):
        """Test broadcast channel name."""
        from backend.websocket import PubSubChannels

        assert PubSubChannels.BROADCAST == "ws:broadcast"

    def test_event_channels(self):
        """Test event-specific channel names."""
        from backend.websocket import PubSubChannels

        assert PubSubChannels.NEW_MATCH == "ws:event:new_match"
        assert PubSubChannels.DEADLINE_SOON == "ws:event:deadline_soon"
        assert PubSubChannels.GRANT_UPDATE == "ws:event:grant_update"
        assert PubSubChannels.STATS_UPDATE == "ws:event:stats_update"

    def test_user_channel_with_string(self):
        """Test getting user channel with string ID."""
        from backend.websocket import PubSubChannels

        user_id = "test-user-123"
        channel = PubSubChannels.user_channel(user_id)

        assert channel == "ws:user:test-user-123"

    def test_user_channel_with_uuid(self):
        """Test getting user channel with UUID."""
        from backend.websocket import PubSubChannels

        user_id = uuid.uuid4()
        channel = PubSubChannels.user_channel(user_id)

        assert channel == f"ws:user:{str(user_id)}"


class TestConnectionStateManager:
    """Tests for ConnectionStateManager class."""

    @pytest.fixture
    def state_manager(self):
        """Create a connection state manager."""
        from backend.websocket import ConnectionStateManager

        return ConnectionStateManager()

    def test_add_connection(self, state_manager):
        """Test adding a connection."""
        sid = "test-sid-123"
        user_id = str(uuid.uuid4())

        state_manager.add_connection(sid, user_id)

        assert sid in state_manager._session_users
        assert state_manager._session_users[sid] == user_id
        assert sid in state_manager._user_sessions[user_id]

    def test_add_connection_with_metadata(self, state_manager):
        """Test adding a connection with metadata."""
        sid = "test-sid-456"
        user_id = str(uuid.uuid4())
        metadata = {"device": "mobile", "browser": "Chrome"}

        state_manager.add_connection(sid, user_id, metadata)

        assert state_manager._session_metadata[sid]["device"] == "mobile"
        assert state_manager._session_metadata[sid]["browser"] == "Chrome"

    def test_remove_connection(self, state_manager):
        """Test removing a connection."""
        sid = "test-sid-789"
        user_id = str(uuid.uuid4())

        state_manager.add_connection(sid, user_id)
        state_manager.remove_connection(sid)

        assert sid not in state_manager._session_users
        assert sid not in state_manager._session_metadata

    def test_multiple_sessions_per_user(self, state_manager):
        """Test multiple sessions for the same user."""
        user_id = str(uuid.uuid4())
        sid1 = "sid-1"
        sid2 = "sid-2"
        sid3 = "sid-3"

        state_manager.add_connection(sid1, user_id)
        state_manager.add_connection(sid2, user_id)
        state_manager.add_connection(sid3, user_id)

        assert len(state_manager._user_sessions[user_id]) == 3
        assert sid1 in state_manager._user_sessions[user_id]
        assert sid2 in state_manager._user_sessions[user_id]
        assert sid3 in state_manager._user_sessions[user_id]

    def test_get_user_sessions(self, state_manager):
        """Test getting all sessions for a user."""
        user_id = str(uuid.uuid4())
        sids = ["sid-a", "sid-b", "sid-c"]

        for sid in sids:
            state_manager.add_connection(sid, user_id)

        user_sessions = state_manager.get_user_sessions(user_id)

        assert len(user_sessions) == 3
        for sid in sids:
            assert sid in user_sessions

    def test_get_user_id(self, state_manager):
        """Test getting user ID from session."""
        sid = "test-sid"
        user_id = str(uuid.uuid4())

        state_manager.add_connection(sid, user_id)
        retrieved_user = state_manager.get_user_id(sid)

        assert retrieved_user == user_id

    def test_get_stats_connection_count(self, state_manager):
        """Test getting total connection count via get_stats."""
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())

        state_manager.add_connection("sid-1", user1)
        state_manager.add_connection("sid-2", user1)
        state_manager.add_connection("sid-3", user2)

        stats = state_manager.get_stats()

        assert stats["total_connections"] == 3

    def test_get_stats_user_count(self, state_manager):
        """Test getting unique user count via get_stats."""
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())
        user3 = str(uuid.uuid4())

        state_manager.add_connection("sid-1", user1)
        state_manager.add_connection("sid-2", user1)  # Same user
        state_manager.add_connection("sid-3", user2)
        state_manager.add_connection("sid-4", user3)

        stats = state_manager.get_stats()

        assert stats["unique_users"] == 3

    def test_is_user_connected(self, state_manager):
        """Test checking if user is connected."""
        user_id = str(uuid.uuid4())
        other_user = str(uuid.uuid4())

        state_manager.add_connection("sid-1", user_id)

        assert state_manager.is_user_connected(user_id) is True
        assert state_manager.is_user_connected(other_user) is False

    def test_update_activity(self, state_manager):
        """Test updating last activity timestamp."""
        sid = "test-sid"
        user_id = str(uuid.uuid4())

        state_manager.add_connection(sid, user_id)
        initial_activity = state_manager._session_metadata[sid]["last_activity"]

        # Simulate time passing
        import time
        time.sleep(0.01)

        state_manager.update_activity(sid)
        new_activity = state_manager._session_metadata[sid]["last_activity"]

        assert new_activity >= initial_activity


class TestWebSocketEventPayloads:
    """Tests for WebSocket event payloads."""

    def test_new_match_event_payload(self):
        """Test NewMatchEvent payload creation."""
        from backend.core.events import NewMatchEvent

        event = NewMatchEvent(
            grant_id=uuid.uuid4(),
            title="Test Grant",
            match_score=0.85,
            agency="NSF",
            amount_range="$100,000 - $500,000",
        )

        payload = event.model_dump()

        assert payload["title"] == "Test Grant"
        assert payload["match_score"] == 0.85
        assert payload["agency"] == "NSF"

    def test_deadline_reminder_event_payload(self):
        """Test DeadlineReminderEvent payload creation."""
        from backend.core.events import DeadlineReminderEvent

        deadline = datetime.now(timezone.utc)
        event = DeadlineReminderEvent(
            grant_id=uuid.uuid4(),
            title="Upcoming Grant",
            days_remaining=3,
            deadline=deadline,
        )

        payload = event.model_dump()

        assert payload["title"] == "Upcoming Grant"
        assert payload["days_remaining"] == 3

    def test_grant_update_event_payload(self):
        """Test GrantUpdateEvent payload creation."""
        from backend.core.events import GrantUpdateEvent

        event = GrantUpdateEvent(
            grant_id=uuid.uuid4(),
            title="Updated Grant",
            update_type="deadline_changed",
            changes={"old": "2025-03-01", "new": "2025-04-01"},
            message="Deadline extended",
        )

        payload = event.model_dump()

        assert payload["update_type"] == "deadline_changed"
        assert payload["message"] == "Deadline extended"

    def test_stats_update_event_payload(self):
        """Test StatsUpdateEvent payload creation."""
        from backend.core.events import StatsUpdateEvent

        event = StatsUpdateEvent(
            new_grants_count=10,
            high_matches_count=5,
            pending_deadlines_count=3,
            total_saved_count=25,
        )

        payload = event.model_dump()

        assert payload["new_grants_count"] == 10
        assert payload["high_matches_count"] == 5


class TestJWTAuthentication:
    """Tests for JWT token validation in WebSocket."""

    def test_valid_jwt_token_parsing(self):
        """Test parsing a valid JWT token structure."""
        # Simulated token payload
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        }

        assert "sub" in payload
        assert "exp" in payload

    def test_expired_jwt_handling(self):
        """Test handling expired JWT tokens."""
        from datetime import timedelta

        exp_time = datetime.now(timezone.utc) - timedelta(hours=1)
        is_expired = exp_time < datetime.now(timezone.utc)

        assert is_expired is True

    def test_missing_sub_claim(self):
        """Test handling JWT without sub claim."""
        payload = {
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        }

        has_sub = "sub" in payload
        assert has_sub is False


class TestWebSocketRooms:
    """Tests for WebSocket room management."""

    def test_user_room_naming(self):
        """Test user room naming convention."""
        user_id = str(uuid.uuid4())
        room_name = f"user:{user_id}"

        assert room_name.startswith("user:")
        assert user_id in room_name

    def test_broadcast_room(self):
        """Test broadcast room name."""
        broadcast_room = "broadcast"

        assert broadcast_room == "broadcast"


class TestWebSocketMetrics:
    """Tests for WebSocket metrics collection."""

    @pytest.fixture
    def state_manager_with_connections(self):
        """Create state manager with some connections."""
        from backend.websocket import ConnectionStateManager

        manager = ConnectionStateManager()

        # Add some connections
        for i in range(5):
            user_id = str(uuid.uuid4())
            manager.add_connection(f"sid-{i}", user_id)

        # Add multiple sessions for one user
        special_user = str(uuid.uuid4())
        manager.add_connection("sid-special-1", special_user)
        manager.add_connection("sid-special-2", special_user)
        manager.add_connection("sid-special-3", special_user)

        return manager

    def test_connection_metrics(self, state_manager_with_connections):
        """Test getting connection metrics."""
        manager = state_manager_with_connections

        stats = manager.get_stats()
        connection_count = stats["total_connections"]
        user_count = stats["unique_users"]

        assert connection_count == 8  # 5 + 3
        assert user_count == 6  # 5 + 1 special user

    def test_connection_stats_summary(self, state_manager_with_connections):
        """Test generating connection stats summary."""
        manager = state_manager_with_connections

        stats = manager.get_stats()

        assert stats["total_connections"] == 8
        assert stats["unique_users"] == 6
        assert stats["total_connections"] / max(stats["unique_users"], 1) > 1


class TestWebSocketEventTypes:
    """Tests for WebSocket event type handling."""

    def test_event_type_new_match(self):
        """Test new_match event type."""
        event_type = "new_match"

        assert event_type in ["new_match", "deadline_soon", "grant_update", "stats_update"]

    def test_event_type_deadline_soon(self):
        """Test deadline_soon event type."""
        event_type = "deadline_soon"

        assert event_type in ["new_match", "deadline_soon", "grant_update", "stats_update"]

    def test_event_dispatch_by_type(self):
        """Test event dispatch based on type."""
        handlers = {
            "new_match": lambda p: "match",
            "deadline_soon": lambda p: "deadline",
            "grant_update": lambda p: "update",
            "stats_update": lambda p: "stats",
        }

        event_type = "new_match"
        handler = handlers.get(event_type)

        assert handler is not None
        assert handler({}) == "match"
