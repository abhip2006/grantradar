"""
API Key Management Endpoints
REST API for creating, listing, revoking, and rotating API keys.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.schemas.api_key import (
    AVAILABLE_SCOPES,
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyDeleteResponse,
    APIKeyListResponse,
    APIKeyResponse,
    APIKeyRotateResponse,
    APIKeyUpdateScopes,
    APIKeyUsageStats,
    AvailableScopesResponse,
)
from backend.services.api_key import (
    create_api_key,
    get_api_key,
    get_key_usage_stats,
    list_user_keys,
    revoke_api_key,
    rotate_api_key,
    update_api_key_scopes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="""
Create a new API key for external integrations.

**IMPORTANT**: The API key is returned ONLY in this response.
Store it securely - it cannot be recovered later!

Available scopes:
- `read:grants` - Read grant listings
- `write:grants` - Create/update grants
- `read:applications` - Read applications
- `write:applications` - Create/update applications
- `read:matches` - Read match results
- `read:profile` - Read user profile
- `write:profile` - Update user profile
- `read:analytics` - Read analytics data
- `admin:api_keys` - Manage API keys
""",
)
async def create_key(
    key_data: APIKeyCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> APIKeyCreateResponse:
    """
    Create a new API key for the current user.

    The key will be returned only once - store it securely!
    """
    api_key, plain_key = await create_api_key(
        db=db,
        user_id=current_user.id,
        name=key_data.name,
        scopes=key_data.scopes,
        expires_at=key_data.expires_at,
        rate_limit=key_data.rate_limit,
    )

    logger.info(f"User {current_user.id} created API key {api_key.id}")

    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,  # Only time we return the full key!
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes or [],
        rate_limit=api_key.rate_limit,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get(
    "",
    response_model=APIKeyListResponse,
    summary="List all API keys",
    description="List all API keys for the current user. Keys are masked - only prefix is shown.",
)
async def list_keys(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    include_inactive: bool = False,
) -> APIKeyListResponse:
    """
    List all API keys for the current user.

    The actual keys are not returned - only metadata and prefix.
    """
    keys = await list_user_keys(
        db=db,
        user_id=current_user.id,
        include_inactive=include_inactive,
    )

    return APIKeyListResponse(
        keys=[
            APIKeyResponse(
                id=key.id,
                name=key.name,
                key_prefix=key.key_prefix,
                scopes=key.scopes or [],
                rate_limit=key.rate_limit,
                request_count=key.request_count,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                is_active=key.is_active,
                created_at=key.created_at,
            )
            for key in keys
        ],
        total=len(keys),
    )


@router.get(
    "/scopes",
    response_model=AvailableScopesResponse,
    summary="List available scopes",
    description="Get a list of all available permission scopes for API keys.",
)
async def list_available_scopes() -> AvailableScopesResponse:
    """Get a list of all available API key scopes."""
    return AvailableScopesResponse(scopes=AVAILABLE_SCOPES)


@router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
    summary="Get API key details",
    description="Get details for a specific API key (without the actual key value).",
)
async def get_key_details(
    key_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> APIKeyResponse:
    """Get details for a specific API key."""
    api_key = await get_api_key(db, key_id, current_user.id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes or [],
        rate_limit=api_key.rate_limit,
        request_count=api_key.request_count,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )


@router.delete(
    "/{key_id}",
    response_model=APIKeyDeleteResponse,
    summary="Revoke an API key",
    description="Revoke (deactivate) an API key. This cannot be undone.",
)
async def revoke_key(
    key_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> APIKeyDeleteResponse:
    """
    Revoke an API key.

    The key will be deactivated and cannot be used for authentication.
    This action cannot be undone.
    """
    success = await revoke_api_key(db, key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    logger.info(f"User {current_user.id} revoked API key {key_id}")

    return APIKeyDeleteResponse(
        success=True,
        message="API key has been revoked",
        id=key_id,
    )


@router.post(
    "/{key_id}/rotate",
    response_model=APIKeyRotateResponse,
    summary="Rotate an API key",
    description="""
Rotate an API key - creates a new key with the same settings and revokes the old one.

**IMPORTANT**: The new API key is returned ONLY in this response.
Store it securely - it cannot be recovered later!
""",
)
async def rotate_key(
    key_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> APIKeyRotateResponse:
    """
    Rotate an API key.

    Creates a new key with the same name, scopes, and settings.
    The old key is immediately revoked.
    """
    result = await rotate_api_key(db, key_id, current_user.id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    new_key, plain_key = result

    logger.info(f"User {current_user.id} rotated API key {key_id} -> {new_key.id}")

    return APIKeyRotateResponse(
        id=new_key.id,
        name=new_key.name,
        key=plain_key,
        key_prefix=new_key.key_prefix,
        scopes=new_key.scopes or [],
        rate_limit=new_key.rate_limit,
        expires_at=new_key.expires_at,
        created_at=new_key.created_at,
        old_key_id=key_id,
    )


@router.get(
    "/{key_id}/usage",
    response_model=APIKeyUsageStats,
    summary="Get API key usage statistics",
    description="Get usage statistics for a specific API key.",
)
async def get_key_usage(
    key_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> APIKeyUsageStats:
    """Get usage statistics for an API key."""
    stats = await get_key_usage_stats(db, key_id, current_user.id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return APIKeyUsageStats(
        id=UUID(stats["id"]),
        name=stats["name"],
        key_prefix=stats["key_prefix"],
        total_requests=stats["total_requests"],
        rate_limit=stats["rate_limit"],
        last_used_at=stats["last_used_at"],
        created_at=stats["created_at"],
        expires_at=stats["expires_at"],
        is_active=stats["is_active"],
        scopes=stats["scopes"],
    )


@router.patch(
    "/{key_id}/scopes",
    response_model=APIKeyResponse,
    summary="Update API key scopes",
    description="Update the permission scopes for an API key.",
)
async def update_key_scopes(
    key_id: UUID,
    scope_update: APIKeyUpdateScopes,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> APIKeyResponse:
    """Update the scopes for an API key."""
    api_key = await update_api_key_scopes(
        db=db,
        api_key_id=key_id,
        user_id=current_user.id,
        scopes=scope_update.scopes,
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    logger.info(f"User {current_user.id} updated scopes for API key {key_id}")

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes or [],
        rate_limit=api_key.rate_limit,
        request_count=api_key.request_count,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )
