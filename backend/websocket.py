"""
GrantRadar WebSocket Server
Socket.io server integrated with FastAPI for real-time notifications.

Features:
- JWT authentication on connection
- User rooms for private updates
- Redis pub/sub for horizontal scaling
- Reconnection handling
- Connection state tracking
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import redis.asyncio as redis
import socketio
from jose import JWTError, jwt

from backend.core.config import settings
from backend.core.events import (
    DeadlineReminderEvent,
    GrantUpdateEvent,
    NewMatchEvent,
    StatsUpdateEvent,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Redis Pub/Sub Channels
# =============================================================================


class PubSubChannels:
    """Redis pub/sub channel names for WebSocket events."""

    # Pattern: ws:user:{user_id}
    USER_PREFIX = "ws:user:"

    # Broadcast channels
    BROADCAST = "ws:broadcast"

    # Event-specific patterns
    NEW_MATCH = "ws:event:new_match"
    DEADLINE_SOON = "ws:event:deadline_soon"
    GRANT_UPDATE = "ws:event:grant_update"
    STATS_UPDATE = "ws:event:stats_update"

    @classmethod
    def user_channel(cls, user_id: str | UUID) -> str:
        """Get the pub/sub channel for a specific user."""
        return f"{cls.USER_PREFIX}{str(user_id)}"


# =============================================================================
# Connection State Manager
# =============================================================================


class ConnectionStateManager:
    """
    Tracks WebSocket connection states across the server.

    Maintains:
    - Connected user IDs and their session IDs (sids)
    - Last activity timestamps
    - Connection metadata
    """

    def __init__(self):
        # Maps user_id -> set of session IDs (sids)
        self._user_sessions: dict[str, set[str]] = {}
        # Maps sid -> user_id
        self._session_users: dict[str, str] = {}
        # Maps sid -> connection metadata
        self._session_metadata: dict[str, dict[str, Any]] = {}

    def add_connection(
        self,
        sid: str,
        user_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Register a new connection."""
        self._session_users[sid] = user_id

        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(sid)

        self._session_metadata[sid] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        logger.info(
            f"Connection added: sid={sid}, user_id={user_id}, "
            f"total_sessions={len(self._user_sessions.get(user_id, []))}"
        )

    def remove_connection(self, sid: str) -> Optional[str]:
        """
        Remove a connection and return the associated user_id.

        Returns:
            The user_id if found, None otherwise.
        """
        user_id = self._session_users.pop(sid, None)

        if user_id and user_id in self._user_sessions:
            self._user_sessions[user_id].discard(sid)
            if not self._user_sessions[user_id]:
                del self._user_sessions[user_id]

        self._session_metadata.pop(sid, None)

        if user_id:
            logger.info(
                f"Connection removed: sid={sid}, user_id={user_id}, "
                f"remaining_sessions={len(self._user_sessions.get(user_id, []))}"
            )

        return user_id

    def get_user_id(self, sid: str) -> Optional[str]:
        """Get the user_id for a session."""
        return self._session_users.get(sid)

    def get_user_sessions(self, user_id: str) -> set[str]:
        """Get all session IDs for a user."""
        return self._user_sessions.get(user_id, set()).copy()

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return user_id in self._user_sessions and len(self._user_sessions[user_id]) > 0

    def update_activity(self, sid: str) -> None:
        """Update the last activity timestamp for a session."""
        if sid in self._session_metadata:
            self._session_metadata[sid]["last_activity"] = datetime.utcnow().isoformat()

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self._session_users),
            "unique_users": len(self._user_sessions),
            "connections_by_user": {user_id: len(sids) for user_id, sids in self._user_sessions.items()},
        }


# =============================================================================
# JWT Authentication
# =============================================================================


class JWTAuthenticator:
    """
    Handles JWT token validation for WebSocket connections.

    Tokens can be provided via:
    - Query parameter: ?token=<jwt>
    - Auth header in handshake
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self._secret_key = secret_key
        self._algorithm = algorithm

    def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        """
        Verify a JWT token and return the payload.

        Args:
            token: JWT token string.

        Returns:
            Token payload if valid, None otherwise.
        """
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

    def extract_user_id(self, payload: dict[str, Any]) -> Optional[str]:
        """Extract user_id from token payload."""
        # Support various claim names
        for key in ["sub", "user_id", "uid", "id"]:
            if key in payload:
                return str(payload[key])
        return None


# =============================================================================
# Socket.IO Server
# =============================================================================


class GrantRadarWebSocket:
    """
    Socket.IO server for GrantRadar real-time notifications.

    Events emitted to clients:
    - 'new_match': When a grant is matched to a user
    - 'deadline_soon': Deadline reminder (3 days before)
    - 'grant_update': When a saved grant is updated
    - 'stats_update': Dashboard counter updates

    Internal events:
    - 'connect': Client connection
    - 'disconnect': Client disconnection
    - 'ping': Keep-alive ping
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        cors_allowed_origins: Optional[list[str]] = None,
    ):
        """
        Initialize the WebSocket server.

        Args:
            redis_url: Redis URL for pub/sub. Defaults to settings.redis_url.
            cors_allowed_origins: Allowed CORS origins. Defaults to frontend URL.
        """
        self._redis_url = redis_url or settings.redis_url
        self._cors_origins = cors_allowed_origins or [
            settings.frontend_url,
            "http://localhost:5173",
            "http://localhost:3000",
        ]

        # Initialize Socket.IO with Redis adapter for horizontal scaling
        self._mgr = socketio.AsyncRedisManager(self._redis_url)
        self._sio = socketio.AsyncServer(
            async_mode="asgi",
            client_manager=self._mgr,
            cors_allowed_origins=self._cors_origins,
            logger=True,
            engineio_logger=settings.debug,
        )

        # Create ASGI app
        self._app = socketio.ASGIApp(
            self._sio,
            socketio_path="/ws/socket.io",
        )

        # State management
        self._state = ConnectionStateManager()
        self._auth = JWTAuthenticator(settings.secret_key)

        # Redis pub/sub subscriber
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._listener_task: Optional[asyncio.Task] = None

        # Register event handlers
        self._register_handlers()

    @property
    def sio(self) -> socketio.AsyncServer:
        """Get the underlying Socket.IO server."""
        return self._sio

    @property
    def app(self) -> socketio.ASGIApp:
        """Get the ASGI application for mounting."""
        return self._app

    @property
    def state(self) -> ConnectionStateManager:
        """Get the connection state manager."""
        return self._state

    def _register_handlers(self) -> None:
        """Register Socket.IO event handlers."""

        @self._sio.event
        async def connect(sid: str, environ: dict, auth: Optional[dict] = None):
            """Handle client connection."""
            logger.info(f"Connection attempt: sid={sid}")

            # Extract token from query params or auth dict
            token = None

            # Try auth dict first (Socket.IO v4 style)
            if auth and isinstance(auth, dict):
                token = auth.get("token")

            # Fall back to query parameters
            if not token:
                query_string = environ.get("QUERY_STRING", "")
                params = dict(p.split("=", 1) for p in query_string.split("&") if "=" in p)
                token = params.get("token")

            # Verify token
            if not token:
                logger.warning(f"Connection rejected: no token provided, sid={sid}")
                raise socketio.exceptions.ConnectionRefusedError("Authentication required")

            payload = self._auth.verify_token(token)
            if not payload:
                logger.warning(f"Connection rejected: invalid token, sid={sid}")
                raise socketio.exceptions.ConnectionRefusedError("Invalid token")

            user_id = self._auth.extract_user_id(payload)
            if not user_id:
                logger.warning(f"Connection rejected: no user_id in token, sid={sid}")
                raise socketio.exceptions.ConnectionRefusedError("Invalid token: no user_id")

            # Register connection
            self._state.add_connection(
                sid=sid,
                user_id=user_id,
                metadata={
                    "user_agent": environ.get("HTTP_USER_AGENT"),
                    "remote_addr": environ.get("REMOTE_ADDR"),
                },
            )

            # Join user's private room
            await self._sio.enter_room(sid, f"user:{user_id}")

            logger.info(f"Connection established: sid={sid}, user_id={user_id}")

            # Send acknowledgment
            await self._sio.emit(
                "connected",
                {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
                room=sid,
            )

            return True

        @self._sio.event
        async def disconnect(sid: str):
            """Handle client disconnection."""
            user_id = self._state.remove_connection(sid)

            if user_id:
                # Leave user room
                await self._sio.leave_room(sid, f"user:{user_id}")
                logger.info(f"Disconnected: sid={sid}, user_id={user_id}")
            else:
                logger.info(f"Disconnected: sid={sid} (unknown user)")

        @self._sio.event
        async def ping(sid: str):
            """Handle keep-alive ping."""
            self._state.update_activity(sid)
            await self._sio.emit("pong", {"timestamp": datetime.utcnow().isoformat()}, room=sid)

        @self._sio.event
        async def subscribe(sid: str, data: dict):
            """Handle subscription to specific event types."""
            user_id = self._state.get_user_id(sid)
            if not user_id:
                return {"error": "Not authenticated"}

            event_type = data.get("event_type")
            if event_type:
                # Join event-specific room
                await self._sio.enter_room(sid, f"event:{event_type}")
                logger.info(f"User {user_id} subscribed to event type: {event_type}")
                return {"subscribed": event_type}

            return {"error": "No event_type specified"}

        @self._sio.event
        async def unsubscribe(sid: str, data: dict):
            """Handle unsubscription from event types."""
            event_type = data.get("event_type")
            if event_type:
                await self._sio.leave_room(sid, f"event:{event_type}")
                return {"unsubscribed": event_type}
            return {"error": "No event_type specified"}

    async def start_pubsub_listener(self) -> None:
        """
        Start listening to Redis pub/sub channels for cross-process events.

        This enables horizontal scaling where multiple WebSocket server
        instances can communicate through Redis.
        """
        if self._redis is not None:
            return

        logger.info("Starting Redis pub/sub listener")

        self._redis = redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        self._pubsub = self._redis.pubsub()

        # Subscribe to pattern channels
        await self._pubsub.psubscribe(f"{PubSubChannels.USER_PREFIX}*")
        await self._pubsub.subscribe(
            PubSubChannels.BROADCAST,
            PubSubChannels.NEW_MATCH,
            PubSubChannels.DEADLINE_SOON,
            PubSubChannels.GRANT_UPDATE,
            PubSubChannels.STATS_UPDATE,
        )

        # Start listener task
        self._listener_task = asyncio.create_task(self._pubsub_listener())
        logger.info("Redis pub/sub listener started")

    async def stop_pubsub_listener(self) -> None:
        """Stop the Redis pub/sub listener."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.punsubscribe()
            await self._pubsub.aclose()
            self._pubsub = None

        if self._redis:
            await self._redis.aclose()
            self._redis = None

        logger.info("Redis pub/sub listener stopped")

    async def _pubsub_listener(self) -> None:
        """Listen for messages from Redis pub/sub and emit to clients."""
        if not self._pubsub:
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] not in ("message", "pmessage"):
                    continue

                try:
                    await self._handle_pubsub_message(message)
                except Exception as e:
                    logger.error(f"Error handling pub/sub message: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Pub/sub listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Pub/sub listener error: {e}", exc_info=True)

    async def _handle_pubsub_message(self, message: dict) -> None:
        """Process a message from Redis pub/sub."""
        channel = message.get("channel") or message.get("pattern", "")
        data_str = message.get("data", "{}")

        try:
            data = json.loads(data_str) if isinstance(data_str, str) else data_str
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in pub/sub message: {data_str[:100]}")
            return

        event_type = data.get("event_type", "message")
        payload = data.get("payload", data)
        target_user = data.get("user_id")

        # Handle user-specific messages
        if channel.startswith(PubSubChannels.USER_PREFIX):
            user_id = channel[len(PubSubChannels.USER_PREFIX) :]
            room = f"user:{user_id}"
            await self._sio.emit(event_type, payload, room=room)
            logger.debug(f"Emitted {event_type} to user {user_id}")
            return

        # Handle broadcast messages
        if channel == PubSubChannels.BROADCAST:
            await self._sio.emit(event_type, payload)
            logger.debug(f"Broadcast {event_type} to all clients")
            return

        # Handle event-specific channels
        if target_user:
            room = f"user:{target_user}"
            await self._sio.emit(event_type, payload, room=room)
            logger.debug(f"Emitted {event_type} to user {target_user}")
        else:
            # Emit to subscribers of this event type
            await self._sio.emit(event_type, payload, room=f"event:{event_type}")
            logger.debug(f"Emitted {event_type} to event subscribers")

    # =========================================================================
    # Event Emission Methods (called by NotificationService)
    # =========================================================================

    async def emit_new_match(
        self,
        user_id: str | UUID,
        event: "NewMatchEvent",
    ) -> None:
        """
        Emit a new match notification to a user.

        Args:
            user_id: Target user ID.
            event: NewMatchEvent with match details.
        """
        room = f"user:{str(user_id)}"
        await self._sio.emit(
            "new_match",
            event.model_dump(mode="json"),
            room=room,
        )
        logger.info(f"Emitted new_match to user {user_id}: grant={event.grant_id}")

    async def emit_deadline_reminder(
        self,
        user_id: str | UUID,
        event: "DeadlineReminderEvent",
    ) -> None:
        """
        Emit a deadline reminder to a user.

        Args:
            user_id: Target user ID.
            event: DeadlineReminderEvent with deadline details.
        """
        room = f"user:{str(user_id)}"
        await self._sio.emit(
            "deadline_soon",
            event.model_dump(mode="json"),
            room=room,
        )
        logger.info(
            f"Emitted deadline_soon to user {user_id}: grant={event.grant_id}, days_remaining={event.days_remaining}"
        )

    async def emit_grant_update(
        self,
        user_id: str | UUID,
        event: "GrantUpdateEvent",
    ) -> None:
        """
        Emit a grant update notification to a user.

        Args:
            user_id: Target user ID.
            event: GrantUpdateEvent with update details.
        """
        room = f"user:{str(user_id)}"
        await self._sio.emit(
            "grant_update",
            event.model_dump(mode="json"),
            room=room,
        )
        logger.info(f"Emitted grant_update to user {user_id}: grant={event.grant_id}, type={event.update_type}")

    async def emit_stats_update(
        self,
        user_id: str | UUID,
        event: "StatsUpdateEvent",
    ) -> None:
        """
        Emit dashboard stats update to a user.

        Args:
            user_id: Target user ID.
            event: StatsUpdateEvent with counter updates.
        """
        room = f"user:{str(user_id)}"
        await self._sio.emit(
            "stats_update",
            event.model_dump(mode="json"),
            room=room,
        )
        logger.debug(f"Emitted stats_update to user {user_id}")

    async def emit_to_user(
        self,
        user_id: str | UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """
        Emit a custom event to a specific user.

        Args:
            user_id: Target user ID.
            event_type: Name of the event.
            data: Event payload.
        """
        room = f"user:{str(user_id)}"
        await self._sio.emit(event_type, data, room=room)
        logger.debug(f"Emitted {event_type} to user {user_id}")

    async def broadcast(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """
        Broadcast an event to all connected clients.

        Args:
            event_type: Name of the event.
            data: Event payload.
        """
        await self._sio.emit(event_type, data)
        logger.debug(f"Broadcast {event_type} to all clients")


# =============================================================================
# Global WebSocket Instance
# =============================================================================

_websocket_server: Optional[GrantRadarWebSocket] = None


def get_websocket_server() -> GrantRadarWebSocket:
    """
    Get or create the global WebSocket server instance.

    Returns:
        GrantRadarWebSocket instance.
    """
    global _websocket_server

    if _websocket_server is None:
        _websocket_server = GrantRadarWebSocket()

    return _websocket_server


async def start_websocket_server() -> GrantRadarWebSocket:
    """
    Initialize and start the WebSocket server.

    Call this during application startup.

    Returns:
        Started GrantRadarWebSocket instance.
    """
    ws = get_websocket_server()
    await ws.start_pubsub_listener()
    return ws


async def stop_websocket_server() -> None:
    """
    Stop the WebSocket server.

    Call this during application shutdown.
    """
    global _websocket_server

    if _websocket_server is not None:
        await _websocket_server.stop_pubsub_listener()
        _websocket_server = None


def mount_websocket(app: Any) -> None:
    """
    Mount the WebSocket server on a FastAPI application.

    Usage:
        from fastapi import FastAPI
        from backend.websocket import mount_websocket

        app = FastAPI()
        mount_websocket(app)

    Args:
        app: FastAPI application instance.
    """
    ws = get_websocket_server()
    app.mount("/ws", ws.app)
    logger.info("WebSocket server mounted at /ws")


__all__ = [
    "GrantRadarWebSocket",
    "ConnectionStateManager",
    "JWTAuthenticator",
    "PubSubChannels",
    "get_websocket_server",
    "start_websocket_server",
    "stop_websocket_server",
    "mount_websocket",
]
