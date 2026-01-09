"""
Authentication API Endpoints
User registration, login, token refresh, user info, and password reset.
"""
import logging
import secrets
from datetime import timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AsyncSessionDep,
    CurrentUser,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_refresh_token,
)
from backend.core.config import settings
from backend.core.rate_limit import RateLimitAuth, RateLimitTier, RateLimitDependency
from backend.models import LabProfile, User
from backend.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)

logger = logging.getLogger(__name__)

# Password reset token settings
RESET_TOKEN_EXPIRE_SECONDS = 3600  # 1 hour
RESET_TOKEN_PREFIX = "password_reset:"

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh."""
    refresh_token: str


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password."
)
async def register(
    user_data: UserCreate,
    db: AsyncSessionDep,
    _rate_limit: RateLimitAuth = None,
) -> Token:
    """
    Register a new user account.

    - **email**: Valid email address (used for login)
    - **password**: Minimum 8 characters
    - **name**: Optional full name
    - **institution**: Optional research institution
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name,
        institution=user_data.institution,
    )

    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(new_user.id), "email": new_user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": str(new_user.id), "email": new_user.email}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Login user",
    description="Authenticate user and return JWT tokens."
)
async def login(
    credentials: UserLogin,
    db: AsyncSessionDep,
    _rate_limit: RateLimitAuth = None,
) -> Token:
    """
    Authenticate a user with email and password.

    Returns access and refresh tokens on success.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Get a new access token using a refresh token."
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSessionDep,
) -> Token:
    """
    Refresh an expired access token.

    Requires a valid refresh token.
    """
    try:
        token_data = verify_refresh_token(request.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists
    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate new tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the currently authenticated user's information."
)
async def get_me(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> UserResponse:
    """
    Get current user information.

    Requires authentication.
    """
    # Check if user has a profile
    result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        institution=current_user.institution,
        phone=current_user.phone,
        created_at=current_user.created_at,
        has_profile=profile is not None
    )


# =============================================================================
# Password Reset Endpoints
# =============================================================================


async def _get_redis_client() -> aioredis.Redis:
    """Get an async Redis client."""
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request password reset",
    description="Request a password reset email. Returns success even if email doesn't exist (security)."
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSessionDep,
    _rate_limit: RateLimitAuth = None,
) -> ForgotPasswordResponse:
    """
    Request a password reset.

    - Generates a secure reset token if the email exists
    - Stores token in Redis with 1-hour expiry
    - Queues a password reset email
    - Always returns success (prevents email enumeration)
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    response = ForgotPasswordResponse()

    if user:
        try:
            # Generate a secure reset token
            reset_token = secrets.token_urlsafe(32)

            # Store token in Redis with user ID
            redis_client = await _get_redis_client()
            redis_key = f"{RESET_TOKEN_PREFIX}{reset_token}"

            await redis_client.setex(
                redis_key,
                RESET_TOKEN_EXPIRE_SECONDS,
                str(user.id),
            )
            await redis_client.aclose()

            # Queue password reset email via Celery
            from backend.tasks.notifications import send_password_reset_email

            reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
            send_password_reset_email.delay(
                email=user.email,
                name=user.name or "User",
                reset_url=reset_url,
            )

            logger.info(f"Password reset requested for user {user.id}")

        except Exception as e:
            # Log error but don't expose it to the user
            logger.error(f"Error processing password reset: {e}", exc_info=True)

    return response


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Reset password",
    description="Reset password using a valid reset token."
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSessionDep,
) -> ResetPasswordResponse:
    """
    Reset a user's password.

    - Validates the reset token from Redis
    - Updates the user's password hash
    - Invalidates the token after use
    """
    redis_client = await _get_redis_client()
    redis_key = f"{RESET_TOKEN_PREFIX}{request.token}"

    try:
        # Get user ID from token
        user_id = await redis_client.get(redis_key)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Find user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Token exists but user doesn't - clean up and error
            await redis_client.delete(redis_key)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Update password
        user.password_hash = get_password_hash(request.new_password)
        await db.flush()

        # Invalidate the token (one-time use)
        await redis_client.delete(redis_key)

        logger.info(f"Password reset completed for user {user.id}")

        return ResetPasswordResponse(
            message="Password has been reset successfully",
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting password"
        )
    finally:
        await redis_client.aclose()
