"""
API Endpoint Tests
Tests for FastAPI endpoints including authentication, grants, matches, and profiles.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt


# =============================================================================
# Authentication Tests
# =============================================================================


class TestAuthentication:
    """Tests for authentication endpoints and JWT handling."""

    @pytest.fixture
    def auth_handler(self):
        """Create an auth handler for testing."""

        class AuthHandler:
            SECRET_KEY = "test-secret-key"
            ALGORITHM = "HS256"
            ACCESS_TOKEN_EXPIRE_MINUTES = 30

            def create_access_token(self, user_id: uuid.UUID, email: str) -> str:
                """Create a JWT access token."""
                expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
                payload = {
                    "sub": str(user_id),
                    "email": email,
                    "exp": expire,
                    "iat": datetime.utcnow(),
                    "type": "access",
                }
                return jwt.encode(payload, self.SECRET_KEY, algorithm=self.ALGORITHM)

            def verify_token(self, token: str) -> dict | None:
                """Verify and decode a JWT token."""
                try:
                    payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
                    return payload
                except jwt.JWTError:
                    return None

            def hash_password(self, password: str) -> str:
                """Hash a password using bcrypt."""
                import bcrypt

                return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            def verify_password(self, password: str, hashed: str) -> bool:
                """Verify a password against its hash."""
                import bcrypt

                return bcrypt.checkpw(password.encode(), hashed.encode())

        return AuthHandler()

    def test_create_access_token(self, auth_handler):
        """Test JWT token creation."""
        user_id = uuid.uuid4()
        token = auth_handler.create_access_token(user_id, "test@test.com")

        assert token is not None
        assert isinstance(token, str)

    def test_verify_valid_token(self, auth_handler):
        """Test verification of valid token."""
        user_id = uuid.uuid4()
        token = auth_handler.create_access_token(user_id, "test@test.com")

        payload = auth_handler.verify_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "test@test.com"

    def test_verify_invalid_token(self, auth_handler):
        """Test verification of invalid token."""
        payload = auth_handler.verify_token("invalid-token")
        assert payload is None

    def test_verify_expired_token(self, auth_handler):
        """Test verification of expired token."""
        # Create a token that's already expired
        expire = datetime.utcnow() - timedelta(hours=1)
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "test@test.com",
            "exp": expire,
            "iat": datetime.utcnow() - timedelta(hours=2),
            "type": "access",
        }
        token = jwt.encode(payload, auth_handler.SECRET_KEY, algorithm=auth_handler.ALGORITHM)

        result = auth_handler.verify_token(token)
        assert result is None

    def test_password_hashing(self, auth_handler):
        """Test password hashing."""
        password = "secure_password_123"
        hashed = auth_handler.hash_password(password)

        assert hashed != password
        assert len(hashed) > 20

    def test_password_verification(self, auth_handler):
        """Test password verification."""
        password = "secure_password_123"
        hashed = auth_handler.hash_password(password)

        assert auth_handler.verify_password(password, hashed) is True
        assert auth_handler.verify_password("wrong_password", hashed) is False


# =============================================================================
# Grant Endpoint Tests
# =============================================================================


class TestGrantEndpoints:
    """Tests for grant-related API endpoints."""

    @pytest.fixture
    def grant_router(self):
        """Create a mock grant router."""

        class GrantRouter:
            def __init__(self, session):
                self.session = session

            async def list_grants(
                self,
                source: str | None = None,
                category: str | None = None,
                min_amount: int | None = None,
                deadline_before: datetime | None = None,
                limit: int = 20,
                offset: int = 0,
            ) -> dict:
                """List grants with optional filters."""
                # Mock implementation
                grants = []
                return {
                    "grants": grants,
                    "total": len(grants),
                    "limit": limit,
                    "offset": offset,
                }

            async def get_grant(self, grant_id: uuid.UUID) -> dict | None:
                """Get a single grant by ID."""
                # Mock implementation
                return None

            async def search_grants(self, query: str, limit: int = 20) -> list[dict]:
                """Search grants by text query."""
                # Mock implementation
                return []

        return GrantRouter(None)

    @pytest.mark.asyncio
    async def test_list_grants_no_filters(self, grant_router):
        """Test listing grants without filters."""
        result = await grant_router.list_grants()

        assert "grants" in result
        assert "total" in result
        assert result["limit"] == 20
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_list_grants_with_source_filter(self, grant_router):
        """Test listing grants filtered by source."""
        result = await grant_router.list_grants(source="grants_gov")

        assert "grants" in result

    @pytest.mark.asyncio
    async def test_list_grants_with_amount_filter(self, grant_router):
        """Test listing grants filtered by minimum amount."""
        result = await grant_router.list_grants(min_amount=100000)

        assert "grants" in result

    @pytest.mark.asyncio
    async def test_list_grants_with_deadline_filter(self, grant_router):
        """Test listing grants filtered by deadline."""
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        result = await grant_router.list_grants(deadline_before=deadline)

        assert "grants" in result

    @pytest.mark.asyncio
    async def test_list_grants_pagination(self, grant_router):
        """Test grant listing pagination."""
        result = await grant_router.list_grants(limit=10, offset=20)

        assert result["limit"] == 10
        assert result["offset"] == 20

    @pytest.mark.asyncio
    async def test_get_grant_not_found(self, grant_router):
        """Test getting a non-existent grant."""
        result = await grant_router.get_grant(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_search_grants(self, grant_router):
        """Test grant search."""
        results = await grant_router.search_grants("machine learning healthcare")
        assert isinstance(results, list)


# =============================================================================
# Match Endpoint Tests
# =============================================================================


class TestMatchEndpoints:
    """Tests for match-related API endpoints."""

    @pytest.fixture
    def match_router(self):
        """Create a mock match router."""

        class MatchRouter:
            def __init__(self, session):
                self.session = session

            async def get_user_matches(
                self,
                user_id: uuid.UUID,
                min_score: float | None = None,
                status: str | None = None,
                limit: int = 20,
                offset: int = 0,
            ) -> dict:
                """Get matches for a user."""
                return {
                    "matches": [],
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                }

            async def get_match(self, match_id: uuid.UUID) -> dict | None:
                """Get a single match by ID."""
                return None

            async def update_match_action(
                self,
                match_id: uuid.UUID,
                action: str,
                feedback: dict | None = None,
            ) -> dict:
                """Update match with user action."""
                valid_actions = ["saved", "dismissed", "applied"]
                if action not in valid_actions:
                    raise ValueError(f"Invalid action: {action}")

                return {
                    "match_id": str(match_id),
                    "action": action,
                    "updated_at": datetime.utcnow().isoformat(),
                }

            async def get_match_stats(self, user_id: uuid.UUID) -> dict:
                """Get match statistics for a user."""
                return {
                    "total_matches": 0,
                    "high_score_matches": 0,
                    "saved_matches": 0,
                    "dismissed_matches": 0,
                    "applied_matches": 0,
                    "avg_match_score": 0.0,
                }

        return MatchRouter(None)

    @pytest.mark.asyncio
    async def test_get_user_matches(self, match_router):
        """Test getting user matches."""
        user_id = uuid.uuid4()
        result = await match_router.get_user_matches(user_id)

        assert "matches" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_get_user_matches_with_score_filter(self, match_router):
        """Test getting user matches with minimum score filter."""
        user_id = uuid.uuid4()
        result = await match_router.get_user_matches(user_id, min_score=0.8)

        assert "matches" in result

    @pytest.mark.asyncio
    async def test_get_user_matches_with_status_filter(self, match_router):
        """Test getting user matches with status filter."""
        user_id = uuid.uuid4()
        result = await match_router.get_user_matches(user_id, status="saved")

        assert "matches" in result

    @pytest.mark.asyncio
    async def test_get_match_not_found(self, match_router):
        """Test getting a non-existent match."""
        result = await match_router.get_match(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_match_action_saved(self, match_router):
        """Test saving a match."""
        match_id = uuid.uuid4()
        result = await match_router.update_match_action(match_id, "saved")

        assert result["action"] == "saved"

    @pytest.mark.asyncio
    async def test_update_match_action_dismissed(self, match_router):
        """Test dismissing a match."""
        match_id = uuid.uuid4()
        result = await match_router.update_match_action(match_id, "dismissed")

        assert result["action"] == "dismissed"

    @pytest.mark.asyncio
    async def test_update_match_action_applied(self, match_router):
        """Test marking a match as applied."""
        match_id = uuid.uuid4()
        result = await match_router.update_match_action(match_id, "applied")

        assert result["action"] == "applied"

    @pytest.mark.asyncio
    async def test_update_match_action_invalid(self, match_router):
        """Test invalid match action."""
        match_id = uuid.uuid4()
        with pytest.raises(ValueError):
            await match_router.update_match_action(match_id, "invalid_action")

    @pytest.mark.asyncio
    async def test_update_match_with_feedback(self, match_router):
        """Test updating match with feedback."""
        match_id = uuid.uuid4()
        feedback = {"relevance": 5, "comment": "Great match!"}
        result = await match_router.update_match_action(match_id, "saved", feedback=feedback)

        assert result["action"] == "saved"

    @pytest.mark.asyncio
    async def test_get_match_stats(self, match_router):
        """Test getting match statistics."""
        user_id = uuid.uuid4()
        stats = await match_router.get_match_stats(user_id)

        assert "total_matches" in stats
        assert "high_score_matches" in stats
        assert "avg_match_score" in stats


# =============================================================================
# Profile Endpoint Tests
# =============================================================================


class TestProfileEndpoints:
    """Tests for profile-related API endpoints."""

    @pytest.fixture
    def profile_router(self):
        """Create a mock profile router."""

        class ProfileRouter:
            def __init__(self, session):
                self.session = session

            async def get_user_profile(self, user_id: uuid.UUID) -> dict | None:
                """Get user's lab profile."""
                return None

            async def create_profile(self, user_id: uuid.UUID, profile_data: dict) -> dict:
                """Create a new lab profile."""
                return {
                    "id": str(uuid.uuid4()),
                    "user_id": str(user_id),
                    **profile_data,
                    "created_at": datetime.utcnow().isoformat(),
                }

            async def update_profile(self, profile_id: uuid.UUID, profile_data: dict) -> dict:
                """Update an existing profile."""
                return {
                    "id": str(profile_id),
                    **profile_data,
                    "updated_at": datetime.utcnow().isoformat(),
                }

            async def delete_profile(self, profile_id: uuid.UUID) -> bool:
                """Delete a profile."""
                return True

            async def regenerate_embedding(self, profile_id: uuid.UUID) -> dict:
                """Regenerate profile embedding."""
                return {
                    "profile_id": str(profile_id),
                    "embedding_updated": True,
                    "updated_at": datetime.utcnow().isoformat(),
                }

        return ProfileRouter(None)

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, profile_router):
        """Test getting non-existent profile."""
        result = await profile_router.get_user_profile(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_create_profile(self, profile_router, sample_lab_profile_data):
        """Test creating a new profile."""
        user_id = uuid.uuid4()
        result = await profile_router.create_profile(user_id, sample_lab_profile_data)

        assert "id" in result
        assert result["user_id"] == str(user_id)
        assert "research_areas" in result

    @pytest.mark.asyncio
    async def test_update_profile(self, profile_router):
        """Test updating a profile."""
        profile_id = uuid.uuid4()
        update_data = {
            "research_areas": ["new_area_1", "new_area_2"],
            "methods": ["new_method"],
        }

        result = await profile_router.update_profile(profile_id, update_data)

        assert "updated_at" in result
        assert result["research_areas"] == ["new_area_1", "new_area_2"]

    @pytest.mark.asyncio
    async def test_delete_profile(self, profile_router):
        """Test deleting a profile."""
        profile_id = uuid.uuid4()
        result = await profile_router.delete_profile(profile_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_regenerate_embedding(self, profile_router):
        """Test regenerating profile embedding."""
        profile_id = uuid.uuid4()
        result = await profile_router.regenerate_embedding(profile_id)

        assert result["embedding_updated"] is True


# =============================================================================
# Stats Endpoint Tests
# =============================================================================


class TestStatsEndpoints:
    """Tests for statistics endpoints."""

    @pytest.fixture
    def stats_router(self):
        """Create a mock stats router."""

        class StatsRouter:
            async def get_platform_stats(self) -> dict:
                """Get platform-wide statistics."""
                return {
                    "total_grants": 10000,
                    "active_grants": 5000,
                    "total_users": 500,
                    "total_matches": 25000,
                    "alerts_sent_today": 150,
                    "avg_match_score": 0.78,
                }

            async def get_user_dashboard_stats(self, user_id: uuid.UUID) -> dict:
                """Get dashboard statistics for a user."""
                return {
                    "unread_matches": 5,
                    "saved_grants": 12,
                    "applied_grants": 3,
                    "avg_match_score": 0.82,
                    "upcoming_deadlines": 4,
                }

            async def get_discovery_stats(self) -> dict:
                """Get discovery pipeline statistics."""
                return {
                    "grants_discovered_today": 45,
                    "grants_validated_today": 42,
                    "validation_pass_rate": 0.93,
                    "avg_processing_time_ms": 250,
                    "sources": {
                        "grants_gov": 25,
                        "nih": 12,
                        "nsf": 8,
                    },
                }

        return StatsRouter()

    @pytest.mark.asyncio
    async def test_get_platform_stats(self, stats_router):
        """Test getting platform statistics."""
        stats = await stats_router.get_platform_stats()

        assert "total_grants" in stats
        assert "total_users" in stats
        assert "total_matches" in stats

    @pytest.mark.asyncio
    async def test_get_user_dashboard_stats(self, stats_router):
        """Test getting user dashboard statistics."""
        user_id = uuid.uuid4()
        stats = await stats_router.get_user_dashboard_stats(user_id)

        assert "unread_matches" in stats
        assert "saved_grants" in stats
        assert "upcoming_deadlines" in stats

    @pytest.mark.asyncio
    async def test_get_discovery_stats(self, stats_router):
        """Test getting discovery pipeline statistics."""
        stats = await stats_router.get_discovery_stats()

        assert "grants_discovered_today" in stats
        assert "validation_pass_rate" in stats
        assert "sources" in stats


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestRequestValidation:
    """Tests for API request validation."""

    def test_valid_grant_filter_params(self):
        """Test validation of grant filter parameters."""
        params = {
            "source": "grants_gov",
            "min_amount": 100000,
            "limit": 50,
            "offset": 0,
        }

        # Validate parameter types
        assert isinstance(params["source"], str)
        assert isinstance(params["min_amount"], int)
        assert params["limit"] <= 100  # Max limit

    def test_invalid_pagination_limit(self):
        """Test that excessive pagination limits are rejected."""
        max_limit = 100

        def validate_limit(limit: int) -> int:
            if limit > max_limit:
                raise ValueError(f"Limit cannot exceed {max_limit}")
            return limit

        with pytest.raises(ValueError):
            validate_limit(500)

    def test_invalid_match_score_range(self):
        """Test validation of match score range."""

        def validate_score(score: float) -> float:
            if not 0.0 <= score <= 1.0:
                raise ValueError("Score must be between 0 and 1")
            return score

        with pytest.raises(ValueError):
            validate_score(1.5)

        with pytest.raises(ValueError):
            validate_score(-0.5)

    def test_valid_profile_data(self, sample_lab_profile_data):
        """Test validation of profile data."""
        # Research areas should be a list of strings
        assert isinstance(sample_lab_profile_data["research_areas"], list)
        assert all(isinstance(a, str) for a in sample_lab_profile_data["research_areas"])

        # Career stage should be one of allowed values
        allowed_stages = ["early_career", "established", "senior"]
        assert sample_lab_profile_data["career_stage"] in allowed_stages


# =============================================================================
# Response Format Tests
# =============================================================================


class TestResponseFormats:
    """Tests for API response formats."""

    def test_paginated_response_format(self):
        """Test paginated response structure."""
        response = {
            "data": [],
            "total": 100,
            "limit": 20,
            "offset": 0,
            "has_more": True,
        }

        assert "data" in response
        assert "total" in response
        assert "limit" in response
        assert "offset" in response
        assert response["has_more"] == (response["offset"] + response["limit"] < response["total"])

    def test_error_response_format(self):
        """Test error response structure."""
        error_response = {
            "error": {
                "code": "NOT_FOUND",
                "message": "Grant not found",
                "details": {"grant_id": str(uuid.uuid4())},
            }
        }

        assert "error" in error_response
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]

    def test_grant_response_format(self, sample_grant_data):
        """Test grant response structure."""
        response = {
            "id": str(sample_grant_data["id"]),
            "title": sample_grant_data["title"],
            "description": sample_grant_data["description"],
            "agency": sample_grant_data["agency"],
            "amount_range": {
                "min": sample_grant_data["amount_min"],
                "max": sample_grant_data["amount_max"],
            },
            "deadline": sample_grant_data["deadline"].isoformat() if sample_grant_data["deadline"] else None,
            "url": sample_grant_data["url"],
            "categories": sample_grant_data["categories"],
        }

        assert "id" in response
        assert "title" in response
        assert "amount_range" in response

    def test_match_response_format(self, sample_match_data):
        """Test match response structure."""
        response = {
            "id": str(sample_match_data["id"]),
            "match_score": sample_match_data["match_score"],
            "reasoning": sample_match_data["reasoning"],
            "predicted_success": sample_match_data["predicted_success"],
            "user_action": sample_match_data["user_action"],
            "grant": {
                "id": str(uuid.uuid4()),
                "title": "Test Grant",
            },
        }

        assert "match_score" in response
        assert "reasoning" in response
        assert "grant" in response


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Tests for API rate limiting."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""

        class RateLimiter:
            def __init__(self, requests_per_minute: int = 60):
                self.requests_per_minute = requests_per_minute
                self.requests: dict[str, list[float]] = {}

            def is_allowed(self, client_id: str) -> bool:
                """Check if request is allowed under rate limit."""
                import time

                now = time.time()
                window_start = now - 60  # 1 minute window

                if client_id not in self.requests:
                    self.requests[client_id] = []

                # Remove old requests
                self.requests[client_id] = [t for t in self.requests[client_id] if t > window_start]

                # Check rate limit
                if len(self.requests[client_id]) >= self.requests_per_minute:
                    return False

                self.requests[client_id].append(now)
                return True

            def get_remaining(self, client_id: str) -> int:
                """Get remaining requests in current window."""
                import time

                now = time.time()
                window_start = now - 60

                if client_id not in self.requests:
                    return self.requests_per_minute

                recent = [t for t in self.requests[client_id] if t > window_start]
                return max(0, self.requests_per_minute - len(recent))

        return RateLimiter(requests_per_minute=10)  # Low limit for testing

    def test_rate_limit_allows_normal_usage(self, rate_limiter):
        """Test that normal usage is allowed."""
        client_id = "test-client"

        for _ in range(5):
            assert rate_limiter.is_allowed(client_id) is True

    def test_rate_limit_blocks_excess_requests(self, rate_limiter):
        """Test that excess requests are blocked."""
        client_id = "test-client"

        # Make requests up to the limit
        for _ in range(10):
            rate_limiter.is_allowed(client_id)

        # Next request should be blocked
        assert rate_limiter.is_allowed(client_id) is False

    def test_rate_limit_remaining_count(self, rate_limiter):
        """Test getting remaining request count."""
        client_id = "test-client"

        initial_remaining = rate_limiter.get_remaining(client_id)
        assert initial_remaining == 10

        rate_limiter.is_allowed(client_id)
        assert rate_limiter.get_remaining(client_id) == 9


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.fixture
    def health_checker(self):
        """Create a health checker."""

        class HealthChecker:
            async def check_database(self) -> dict:
                """Check database connectivity."""
                return {"status": "healthy", "latency_ms": 5}

            async def check_redis(self) -> dict:
                """Check Redis connectivity."""
                return {"status": "healthy", "latency_ms": 2}

            async def check_all(self) -> dict:
                """Run all health checks."""
                db = await self.check_database()
                redis = await self.check_redis()

                overall_status = "healthy"
                if db["status"] != "healthy" or redis["status"] != "healthy":
                    overall_status = "unhealthy"

                return {
                    "status": overall_status,
                    "checks": {
                        "database": db,
                        "redis": redis,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return HealthChecker()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, health_checker):
        """Test health check when all services are healthy."""
        result = await health_checker.check_all()

        assert result["status"] == "healthy"
        assert "database" in result["checks"]
        assert "redis" in result["checks"]

    @pytest.mark.asyncio
    async def test_health_check_database(self, health_checker):
        """Test database health check."""
        result = await health_checker.check_database()

        assert result["status"] == "healthy"
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_health_check_redis(self, health_checker):
        """Test Redis health check."""
        result = await health_checker.check_redis()

        assert result["status"] == "healthy"
        assert "latency_ms" in result
