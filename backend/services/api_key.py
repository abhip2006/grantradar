"""
API Key Service
Functions for creating, validating, and managing API keys.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.api_key import APIKey

logger = logging.getLogger(__name__)

# API key prefix for identification
API_KEY_PREFIX = "gr_"


def _generate_api_key() -> str:
    """
    Generate a new random API key.

    Format: gr_<32 random bytes as hex>
    Total length: 67 characters
    """
    random_bytes = secrets.token_hex(32)
    return f"{API_KEY_PREFIX}{random_bytes}"


def _hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.

    Args:
        api_key: The plain text API key

    Returns:
        SHA-256 hash of the key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def _get_key_prefix(api_key: str) -> str:
    """
    Extract the display prefix from an API key.

    Args:
        api_key: The full API key

    Returns:
        First 8 characters of the key (after the gr_ prefix)
    """
    # Skip the "gr_" prefix and take next 8 chars
    return api_key[3:11] if len(api_key) > 11 else api_key[:8]


async def create_api_key(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    scopes: Optional[List[str]] = None,
    expires_at: Optional[datetime] = None,
    rate_limit: int = 1000,
) -> tuple[APIKey, str]:
    """
    Create a new API key for a user.

    The plain text key is returned only once during creation.
    Store it securely - it cannot be recovered later.

    Args:
        db: Database session
        user_id: ID of the user creating the key
        name: Friendly name for the key
        scopes: List of permission scopes
        expires_at: Optional expiration datetime
        rate_limit: Maximum requests per hour (default: 1000)

    Returns:
        Tuple of (APIKey model instance, plain text key)
    """
    # Generate the key
    plain_key = _generate_api_key()
    key_hash = _hash_api_key(plain_key)
    key_prefix = _get_key_prefix(plain_key)

    # Create the database record
    api_key = APIKey(
        user_id=user_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes or [],
        expires_at=expires_at,
        rate_limit=rate_limit,
        is_active=True,
    )

    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    logger.info(f"Created API key {api_key.id} for user {user_id}")

    # Return both the model and the plain key (only chance to see it)
    return api_key, plain_key


async def validate_api_key(
    db: AsyncSession,
    api_key: str,
    required_scopes: Optional[List[str]] = None,
) -> Optional[APIKey]:
    """
    Validate an API key and check scopes.

    Args:
        db: Database session
        api_key: The plain text API key to validate
        required_scopes: Optional list of required scopes

    Returns:
        APIKey model if valid, None otherwise
    """
    # Hash the provided key
    key_hash = _hash_api_key(api_key)

    # Query for matching active key
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )
    )
    api_key_record = result.scalar_one_or_none()

    if not api_key_record:
        logger.debug("API key validation failed: key not found or inactive")
        return None

    # Check expiration
    if api_key_record.expires_at:
        if api_key_record.expires_at < datetime.now(timezone.utc):
            logger.debug(f"API key {api_key_record.id} has expired")
            return None

    # Check required scopes
    if required_scopes:
        key_scopes = set(api_key_record.scopes or [])
        required = set(required_scopes)
        if not required.issubset(key_scopes):
            missing = required - key_scopes
            logger.debug(
                f"API key {api_key_record.id} missing required scopes: {missing}"
            )
            return None

    return api_key_record


async def update_last_used(
    db: AsyncSession,
    api_key_id: UUID,
) -> None:
    """
    Update the last_used_at timestamp and increment request count.

    Args:
        db: Database session
        api_key_id: ID of the API key to update
    """
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key_id)
        .values(
            last_used_at=datetime.now(timezone.utc),
            request_count=APIKey.request_count + 1,
        )
    )
    await db.flush()


async def revoke_api_key(
    db: AsyncSession,
    api_key_id: UUID,
    user_id: UUID,
) -> bool:
    """
    Revoke (deactivate) an API key.

    Args:
        db: Database session
        api_key_id: ID of the API key to revoke
        user_id: ID of the owning user (for authorization)

    Returns:
        True if key was revoked, False if not found or unauthorized
    """
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == api_key_id,
                APIKey.user_id == user_id,
            )
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        return False

    api_key.is_active = False
    await db.flush()

    logger.info(f"Revoked API key {api_key_id} for user {user_id}")
    return True


async def list_user_keys(
    db: AsyncSession,
    user_id: UUID,
    include_inactive: bool = False,
) -> List[APIKey]:
    """
    List all API keys for a user.

    The key_hash is not returned - only metadata and prefix.

    Args:
        db: Database session
        user_id: ID of the user
        include_inactive: Whether to include revoked keys

    Returns:
        List of APIKey models (without key_hash exposure)
    """
    query = select(APIKey).where(APIKey.user_id == user_id)

    if not include_inactive:
        query = query.where(APIKey.is_active == True)

    query = query.order_by(APIKey.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_api_key(
    db: AsyncSession,
    api_key_id: UUID,
    user_id: UUID,
) -> Optional[APIKey]:
    """
    Get a specific API key by ID.

    Args:
        db: Database session
        api_key_id: ID of the API key
        user_id: ID of the owning user (for authorization)

    Returns:
        APIKey model if found and authorized, None otherwise
    """
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == api_key_id,
                APIKey.user_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def rotate_api_key(
    db: AsyncSession,
    api_key_id: UUID,
    user_id: UUID,
) -> Optional[tuple[APIKey, str]]:
    """
    Rotate an API key - create new key with same settings, revoke old.

    Args:
        db: Database session
        api_key_id: ID of the API key to rotate
        user_id: ID of the owning user (for authorization)

    Returns:
        Tuple of (new APIKey, plain text key) or None if not found
    """
    # Get the existing key
    existing_key = await get_api_key(db, api_key_id, user_id)
    if not existing_key:
        return None

    # Create a new key with same settings
    new_key, plain_key = await create_api_key(
        db=db,
        user_id=user_id,
        name=existing_key.name,
        scopes=existing_key.scopes,
        expires_at=existing_key.expires_at,
        rate_limit=existing_key.rate_limit,
    )

    # Revoke the old key
    existing_key.is_active = False
    await db.flush()

    logger.info(f"Rotated API key {api_key_id} -> {new_key.id} for user {user_id}")

    return new_key, plain_key


async def get_key_usage_stats(
    db: AsyncSession,
    api_key_id: UUID,
    user_id: UUID,
) -> Optional[dict]:
    """
    Get usage statistics for an API key.

    Args:
        db: Database session
        api_key_id: ID of the API key
        user_id: ID of the owning user (for authorization)

    Returns:
        Usage statistics dict or None if not found
    """
    api_key = await get_api_key(db, api_key_id, user_id)
    if not api_key:
        return None

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "total_requests": api_key.request_count,
        "rate_limit": api_key.rate_limit,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "created_at": api_key.created_at.isoformat(),
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "is_active": api_key.is_active,
        "scopes": api_key.scopes or [],
    }


async def update_api_key_scopes(
    db: AsyncSession,
    api_key_id: UUID,
    user_id: UUID,
    scopes: List[str],
) -> Optional[APIKey]:
    """
    Update the scopes of an API key.

    Args:
        db: Database session
        api_key_id: ID of the API key
        user_id: ID of the owning user (for authorization)
        scopes: New list of scopes

    Returns:
        Updated APIKey or None if not found
    """
    api_key = await get_api_key(db, api_key_id, user_id)
    if not api_key:
        return None

    api_key.scopes = scopes
    await db.flush()
    await db.refresh(api_key)

    logger.info(f"Updated scopes for API key {api_key_id}")
    return api_key


# Available scopes for API keys
AVAILABLE_SCOPES = [
    # Grant scopes
    "read:grants",
    "write:grants",
    # Application scopes
    "read:applications",
    "write:applications",
    # Match scopes
    "read:matches",
    # Profile scopes
    "read:profile",
    "write:profile",
    # Analytics scopes
    "read:analytics",
    # Admin scopes
    "admin:api_keys",
]


def validate_scopes(scopes: List[str]) -> bool:
    """
    Validate that all provided scopes are valid.

    Args:
        scopes: List of scopes to validate

    Returns:
        True if all scopes are valid
    """
    return all(scope in AVAILABLE_SCOPES for scope in scopes)
