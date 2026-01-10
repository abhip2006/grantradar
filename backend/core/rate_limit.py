"""
Rate Limiting Module
Redis-based distributed rate limiting for FastAPI endpoints.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Annotated, Callable, Optional

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limit Configuration
# =============================================================================


class RateLimitTier(str, Enum):
    """Predefined rate limit tiers for different endpoint types."""

    AUTH = "auth"  # Login, register - strict limits
    AI = "ai"  # Chat, writing, insights - moderate limits
    SEARCH = "search"  # Search endpoints - higher limits
    STANDARD = "standard"  # Default API endpoints


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a tier."""

    requests: int  # Number of requests allowed
    window: int  # Time window in seconds

    @property
    def key_suffix(self) -> str:
        """Return a key suffix for Redis."""
        return f"{self.requests}_{self.window}"


# Default rate limit configurations
RATE_LIMIT_CONFIGS: dict[RateLimitTier, RateLimitConfig] = {
    RateLimitTier.AUTH: RateLimitConfig(
        requests=settings.rate_limit_auth_requests,
        window=settings.rate_limit_auth_window,
    ),
    RateLimitTier.AI: RateLimitConfig(
        requests=settings.rate_limit_ai_requests,
        window=settings.rate_limit_ai_window,
    ),
    RateLimitTier.SEARCH: RateLimitConfig(
        requests=settings.rate_limit_search_requests,
        window=settings.rate_limit_search_window,
    ),
    RateLimitTier.STANDARD: RateLimitConfig(
        requests=settings.rate_limit_standard_requests,
        window=settings.rate_limit_standard_window,
    ),
}


# =============================================================================
# Redis Rate Limiter
# =============================================================================


class RedisRateLimiter:
    """
    Redis-based sliding window rate limiter.

    Uses a sorted set to track request timestamps, allowing for
    accurate sliding window rate limiting across distributed workers.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def is_rate_limited(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """
        Check if a key is rate limited using sliding window.

        Args:
            key: Unique identifier (e.g., "rate_limit:auth:user_123" or "rate_limit:auth:ip_1.2.3.4")
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_limited, remaining_requests, retry_after_seconds)
        """
        redis = await self.get_redis()
        now = time.time()
        window_start = now - window

        # Use a pipeline for atomic operations
        pipe = redis.pipeline()

        # Remove expired entries
        pipe.zremrangebyscore(key, "-inf", window_start)

        # Count current entries
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry on the key
        pipe.expire(key, window + 1)

        # Get the oldest timestamp in the window for retry-after calculation
        pipe.zrange(key, 0, 0, withscores=True)

        results = await pipe.execute()

        current_count = results[1]
        oldest_entries = results[4]

        remaining = max(0, limit - current_count - 1)  # -1 for the request we just added
        is_limited = current_count >= limit

        # Calculate retry-after based on when the oldest request will expire
        retry_after = 0
        if is_limited and oldest_entries:
            oldest_timestamp = oldest_entries[0][1]
            retry_after = int(window - (now - oldest_timestamp)) + 1

        return is_limited, remaining, retry_after

    async def get_usage(self, key: str, window: int) -> int:
        """Get current usage count for a key."""
        redis = await self.get_redis()
        now = time.time()
        window_start = now - window

        # Clean up and count
        await redis.zremrangebyscore(key, "-inf", window_start)
        return await redis.zcard(key)


# =============================================================================
# In-Memory Fallback Rate Limiter
# =============================================================================


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for fallback when Redis is unavailable.

    Uses a sliding window algorithm with dict-based storage.
    Note: This only works for single-instance deployments and should
    only be used as a fallback, not as the primary rate limiter.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Cleanup every 60 seconds

    def _cleanup_if_needed(self) -> None:
        """Periodically clean up old entries to prevent memory leaks."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        keys_to_delete = []

        for key, timestamps in self._requests.items():
            # Remove entries older than 1 hour
            self._requests[key] = [ts for ts in timestamps if now - ts < 3600]
            if not self._requests[key]:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._requests[key]

    async def is_rate_limited(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """
        Check if a key is rate limited.

        Returns:
            Tuple of (is_limited, remaining_requests, retry_after_seconds)
        """
        self._cleanup_if_needed()
        now = time.time()
        window_start = now - window

        # Get or create timestamp list for this key
        if key not in self._requests:
            self._requests[key] = []

        # Remove expired entries
        self._requests[key] = [ts for ts in self._requests[key] if ts > window_start]

        current_count = len(self._requests[key])

        # Check if rate limited
        if current_count >= limit:
            # Calculate retry-after based on oldest entry
            if self._requests[key]:
                oldest = min(self._requests[key])
                retry_after = int(window - (now - oldest)) + 1
            else:
                retry_after = window
            return True, 0, retry_after

        # Add current request
        self._requests[key].append(now)
        remaining = max(0, limit - current_count - 1)

        return False, remaining, 0


# Global rate limiter instances
_rate_limiter: Optional[RedisRateLimiter] = None
_fallback_limiter: Optional[InMemoryRateLimiter] = None
_redis_available: bool = True  # Track Redis availability


async def get_rate_limiter() -> RedisRateLimiter:
    """Get the global Redis rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter(settings.redis_url)
    return _rate_limiter


def get_fallback_limiter() -> InMemoryRateLimiter:
    """Get the global in-memory fallback rate limiter."""
    global _fallback_limiter
    if _fallback_limiter is None:
        _fallback_limiter = InMemoryRateLimiter()
    return _fallback_limiter


async def close_rate_limiter() -> None:
    """Close the global rate limiter."""
    global _rate_limiter, _fallback_limiter
    if _rate_limiter:
        await _rate_limiter.close()
        _rate_limiter = None
    _fallback_limiter = None


# =============================================================================
# Helper Functions
# =============================================================================


def get_client_identifier(request: Request) -> tuple[Optional[str], str]:
    """
    Extract client identifier from request.

    Returns:
        Tuple of (user_id, ip_address)
        user_id may be None if not authenticated
    """
    # Try to get user_id from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)

    # Get IP address (handle proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (client IP)
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"

    return user_id, ip_address


def build_rate_limit_key(
    tier: RateLimitTier,
    user_id: Optional[str],
    ip_address: str,
) -> str:
    """Build Redis key for rate limiting."""
    # Prefer user_id for authenticated requests, fall back to IP
    identifier = f"user_{user_id}" if user_id else f"ip_{ip_address}"
    return f"rate_limit:{tier.value}:{identifier}"


# =============================================================================
# Rate Limit Dependency
# =============================================================================


class RateLimitDependency:
    """
    FastAPI dependency for rate limiting.

    Usage:
        @router.get("/search")
        async def search(
            _: Annotated[None, Depends(RateLimitDependency(RateLimitTier.SEARCH))]
        ):
            ...
    """

    def __init__(
        self,
        tier: RateLimitTier = RateLimitTier.STANDARD,
        requests: Optional[int] = None,
        window: Optional[int] = None,
    ):
        """
        Initialize rate limit dependency.

        Args:
            tier: Predefined rate limit tier
            requests: Override number of requests (uses tier default if None)
            window: Override time window in seconds (uses tier default if None)
        """
        self.tier = tier
        self.requests = requests
        self.window = window

    async def __call__(self, request: Request) -> None:
        """Check rate limit for the request."""
        # Skip rate limiting in development if disabled
        if settings.rate_limit_enabled is False:
            return

        # Get rate limit configuration
        config = RATE_LIMIT_CONFIGS[self.tier]
        limit = self.requests or config.requests
        window = self.window or config.window

        # Get client identifier
        user_id, ip_address = get_client_identifier(request)

        # Build rate limit key
        key = build_rate_limit_key(self.tier, user_id, ip_address)

        global _redis_available

        try:
            # Try Redis first
            limiter = await get_rate_limiter()
            is_limited, remaining, retry_after = await limiter.is_rate_limited(key, limit, window)
            _redis_available = True

            # Store rate limit info in request state for response headers
            request.state.rate_limit_limit = limit
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit_reset = int(time.time()) + window

            if is_limited:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Too many requests. Please retry after {retry_after} seconds.",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(request.state.rate_limit_reset),
                    },
                )
        except HTTPException:
            raise
        except Exception as e:
            # Redis unavailable - use in-memory fallback
            if _redis_available:
                logger.warning(f"Redis rate limiting unavailable, using in-memory fallback: {e}")
                _redis_available = False

            try:
                # SECURITY: Always enforce rate limiting, even when Redis is down
                fallback = get_fallback_limiter()
                is_limited, remaining, retry_after = await fallback.is_rate_limited(key, limit, window)

                request.state.rate_limit_limit = limit
                request.state.rate_limit_remaining = remaining
                request.state.rate_limit_reset = int(time.time()) + window

                if is_limited:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "rate_limit_exceeded",
                            "message": f"Too many requests. Please retry after {retry_after} seconds.",
                            "retry_after": retry_after,
                        },
                        headers={
                            "Retry-After": str(retry_after),
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(request.state.rate_limit_reset),
                        },
                    )
            except HTTPException:
                raise
            except Exception as fallback_error:
                # If even fallback fails, log but still enforce strict limit
                logger.error(f"Fallback rate limiting failed: {fallback_error}")
                # In case of complete failure, apply a strict limit
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_error",
                        "message": "Rate limiting temporarily unavailable. Please try again.",
                        "retry_after": 60,
                    },
                    headers={"Retry-After": "60"},
                )


# Convenience type aliases
RateLimitAuth = Annotated[None, Depends(RateLimitDependency(RateLimitTier.AUTH))]
RateLimitAI = Annotated[None, Depends(RateLimitDependency(RateLimitTier.AI))]
RateLimitSearch = Annotated[None, Depends(RateLimitDependency(RateLimitTier.SEARCH))]
RateLimitStandard = Annotated[None, Depends(RateLimitDependency(RateLimitTier.STANDARD))]


def rate_limit(
    tier: RateLimitTier = RateLimitTier.STANDARD,
    requests: Optional[int] = None,
    window: Optional[int] = None,
) -> Callable:
    """
    Rate limit decorator for route handlers.

    Usage:
        @router.get("/search")
        @rate_limit(RateLimitTier.SEARCH)
        async def search():
            ...

        # Or with custom limits:
        @router.get("/custom")
        @rate_limit(requests=10, window=60)
        async def custom():
            ...
    """
    dependency = RateLimitDependency(tier=tier, requests=requests, window=window)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            await dependency(request)
            return await func(*args, request=request, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Rate Limit Middleware
# =============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limit headers to responses.

    This middleware adds X-RateLimit-* headers to responses when
    rate limiting information is available in request.state.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        # Add rate limit headers if available
        if hasattr(request.state, "rate_limit_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Remaining"] = str(getattr(request.state, "rate_limit_remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(getattr(request.state, "rate_limit_reset", 0))

        return response


# =============================================================================
# Exception Handler
# =============================================================================


async def rate_limit_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """
    Custom exception handler for rate limit errors.

    Ensures proper 429 response format with Retry-After header.
    """
    if exc.status_code != status.HTTP_429_TOO_MANY_REQUESTS:
        raise exc

    headers = dict(exc.headers) if exc.headers else {}

    # Ensure Retry-After header is present
    if "Retry-After" not in headers:
        retry_after = 60  # Default retry after
        if isinstance(exc.detail, dict):
            retry_after = exc.detail.get("retry_after", 60)
        headers["Retry-After"] = str(retry_after)

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": True,
            "message": exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", "Rate limit exceeded"),
            "status_code": 429,
            "retry_after": int(headers["Retry-After"]),
        },
        headers=headers,
    )
