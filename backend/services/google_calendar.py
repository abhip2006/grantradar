"""
Google Calendar Service
Handles OAuth flow and calendar event management.
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarService:
    """Service for Google Calendar OAuth and API operations."""

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = f"{settings.backend_url}/api/integrations/calendar/google/callback"
        self.scopes = [
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]

    def get_authorization_url(self, user_id: str) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            user_id: The user ID to embed in the state parameter.

        Returns:
            The Google OAuth authorization URL.
        """
        # Create state with user_id for callback
        state = self._create_state(user_id)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
            "state": state,
        }

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def _create_state(self, user_id: str) -> str:
        """
        Create OAuth state parameter with user_id.

        Uses HMAC-style signature for validation.

        Args:
            user_id: The user ID to embed.

        Returns:
            State string in format "user_id:signature".
        """
        # Simple encoding - in production use signed tokens
        signature = hashlib.sha256(
            f"{user_id}{settings.secret_key}".encode()
        ).hexdigest()[:16]
        return f"{user_id}:{signature}"

    def _verify_state(self, state: str) -> Optional[str]:
        """
        Verify OAuth state and extract user_id.

        Args:
            state: The state parameter from OAuth callback.

        Returns:
            The user_id if valid, None otherwise.
        """
        try:
            user_id, sig = state.split(":")
            expected_sig = hashlib.sha256(
                f"{user_id}{settings.secret_key}".encode()
            ).hexdigest()[:16]
            if sig == expected_sig:
                return user_id
        except (ValueError, AttributeError):
            pass
        return None

    def handle_callback(self, code: str, state: str) -> tuple[str, dict]:
        """
        Handle OAuth callback - exchange code for tokens.

        Args:
            code: Authorization code from Google.
            state: State parameter for verification.

        Returns:
            Tuple of (user_id, tokens_dict).

        Raises:
            ValueError: If state is invalid or token exchange fails.
        """
        # Verify state
        user_id = self._verify_state(state)
        if not user_id:
            raise ValueError("Invalid OAuth state")

        # Exchange code for tokens
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            tokens = response.json()

        return user_id, tokens

    async def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: The refresh token.

        Returns:
            Dict containing new access token and expiry.

        Raises:
            ValueError: If token refresh fails.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                raise ValueError(f"Token refresh failed: {response.status_code}")

            return response.json()

    async def sync_deadlines(
        self,
        integration: Any,  # CalendarIntegration model
        deadlines: list,  # List of Deadline models
        db: Any,  # AsyncSession
    ) -> int:
        """
        Sync deadlines to Google Calendar.

        Creates or updates calendar events for each deadline.

        Args:
            integration: The CalendarIntegration record.
            deadlines: List of Deadline models to sync.
            db: Database session for updating tokens.

        Returns:
            Number of events synced successfully.
        """
        # Check if token needs refresh
        if integration.token_expires_at < datetime.now(timezone.utc):
            logger.info("Access token expired, refreshing...")
            tokens = await self.refresh_token(integration.refresh_token)
            integration.access_token = tokens["access_token"]
            integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=tokens["expires_in"]
            )
            # Token will be saved when db.commit() is called

        synced = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            for deadline in deadlines:
                try:
                    # Create event
                    event = self._deadline_to_event(deadline)

                    # Check if event already exists (by searching for our custom ID)
                    existing_event_id = await self._find_existing_event(
                        client, integration, deadline.id
                    )

                    if existing_event_id:
                        # Update existing event
                        response = await client.put(
                            f"{GOOGLE_CALENDAR_API}/calendars/{integration.calendar_id}/events/{existing_event_id}",
                            headers={
                                "Authorization": f"Bearer {integration.access_token}",
                                "Content-Type": "application/json",
                            },
                            json=event,
                        )
                    else:
                        # Create new event
                        response = await client.post(
                            f"{GOOGLE_CALENDAR_API}/calendars/{integration.calendar_id}/events",
                            headers={
                                "Authorization": f"Bearer {integration.access_token}",
                                "Content-Type": "application/json",
                            },
                            json=event,
                        )

                    if response.status_code in (200, 201):
                        synced += 1
                        logger.info(f"Synced deadline {deadline.id} to Google Calendar")
                    else:
                        logger.warning(
                            f"Failed to sync deadline {deadline.id}: {response.text}"
                        )

                except Exception as e:
                    logger.error(f"Error syncing deadline {deadline.id}: {e}")

        return synced

    async def _find_existing_event(
        self,
        client: httpx.AsyncClient,
        integration: Any,
        deadline_id: Any,
    ) -> Optional[str]:
        """
        Find an existing calendar event for a deadline.

        Searches for events with our custom extended property.

        Args:
            client: HTTP client.
            integration: Calendar integration.
            deadline_id: Deadline UUID.

        Returns:
            Google event ID if found, None otherwise.
        """
        try:
            # Search using private extended properties
            response = await client.get(
                f"{GOOGLE_CALENDAR_API}/calendars/{integration.calendar_id}/events",
                headers={
                    "Authorization": f"Bearer {integration.access_token}",
                },
                params={
                    "privateExtendedProperty": f"grantradar_deadline_id={deadline_id}",
                    "maxResults": 1,
                },
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items:
                    return items[0].get("id")
        except Exception as e:
            logger.warning(f"Error searching for existing event: {e}")

        return None

    def _deadline_to_event(self, deadline: Any) -> dict:
        """
        Convert a Deadline model to Google Calendar event format.

        Args:
            deadline: The Deadline model.

        Returns:
            Google Calendar event dict.
        """
        # Use sponsor_deadline as the event date
        event_date = deadline.sponsor_deadline

        # Build description
        description_parts = [f"Grant Deadline: {deadline.title}"]
        if deadline.funder:
            description_parts.append(f"Funder: {deadline.funder}")
        if deadline.mechanism:
            description_parts.append(f"Mechanism: {deadline.mechanism}")
        description_parts.append(f"Priority: {deadline.priority}")
        if deadline.notes:
            description_parts.append(f"\n{deadline.notes}")
        description_parts.append(f"\nView in GrantRadar: {settings.frontend_url}/deadlines")

        return {
            "summary": f"[GrantRadar] {deadline.title}",
            "description": "\n".join(description_parts),
            "start": {
                "dateTime": event_date.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": (event_date + timedelta(hours=1)).isoformat(),
                "timeZone": "UTC",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},  # 1 day before
                    {"method": "popup", "minutes": 60},  # 1 hour before
                ],
            },
            "colorId": self._priority_to_color(deadline.priority),
            # Store deadline ID in extended properties for updates
            "extendedProperties": {
                "private": {
                    "grantradar_deadline_id": str(deadline.id),
                }
            },
        }

    def _priority_to_color(self, priority: str) -> str:
        """
        Map priority to Google Calendar color ID.

        Args:
            priority: Priority level string.

        Returns:
            Google Calendar color ID.
        """
        color_map = {
            "low": "7",  # Peacock (cyan)
            "medium": "5",  # Banana (yellow)
            "high": "6",  # Tangerine (orange)
            "critical": "11",  # Tomato (red)
        }
        return color_map.get(priority, "5")

    async def delete_event(
        self,
        integration: Any,
        deadline_id: Any,
    ) -> bool:
        """
        Delete a calendar event for a deadline.

        Args:
            integration: Calendar integration.
            deadline_id: Deadline UUID.

        Returns:
            True if deleted successfully.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Find the event first
            event_id = await self._find_existing_event(client, integration, deadline_id)
            if not event_id:
                return False

            response = await client.delete(
                f"{GOOGLE_CALENDAR_API}/calendars/{integration.calendar_id}/events/{event_id}",
                headers={
                    "Authorization": f"Bearer {integration.access_token}",
                },
            )

            return response.status_code in (200, 204)

    async def get_calendars(self, access_token: str) -> list[dict]:
        """
        Get list of user's calendars.

        Args:
            access_token: OAuth access token.

        Returns:
            List of calendar dicts with id, summary, primary.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GOOGLE_CALENDAR_API}/users/me/calendarList",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            if response.status_code != 200:
                return []

            data = response.json()
            calendars = []
            for item in data.get("items", []):
                calendars.append(
                    {
                        "id": item.get("id"),
                        "summary": item.get("summary"),
                        "primary": item.get("primary", False),
                    }
                )

            return calendars
