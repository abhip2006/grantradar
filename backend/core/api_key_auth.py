"""
API Key Authentication Dependency
FastAPI dependency for validating API key authentication from X-API-Key header.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated, Any, List, Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.api_key import APIKey
from backend.services.api_key import update_last_used, validate_api_key

if TYPE_CHECKING:
    from backend.models import User

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """
    FastAPI dependency for API key authentication.

    Usage:
        @router.get("/endpoint")
        async def my_endpoint(
            api_key: APIKey = Depends(APIKeyAuth(scopes=["read:grants"]))
        ):
            # api_key is the validated APIKey model
            pass
    """

    def __init__(self, scopes: Optional[List[str]] = None):
        """
        Initialize API key auth dependency.

        Args:
            scopes: Optional list of required scopes
        """
        self.scopes = scopes

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        api_key_value: str = Security(api_key_header),
    ) -> APIKey:
        """
        Validate the API key and return the APIKey model.

        Args:
            request: FastAPI request object
            db: Database session
            api_key_value: The API key from the X-API-Key header

        Returns:
            Validated APIKey model

        Raises:
            HTTPException: If API key is invalid, expired, or missing scopes
        """
        if not api_key_value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is required",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Validate the API key
        api_key = await validate_api_key(
            db=db,
            api_key=api_key_value,
            required_scopes=self.scopes,
        )

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Check rate limit (simple check - could be enhanced with Redis)
        # For now, we just track usage
        await update_last_used(db, api_key.id)

        # Store API key info in request state for logging/analytics
        request.state.api_key_id = api_key.id
        request.state.api_key_user_id = api_key.user_id

        logger.debug(f"API key {api_key.key_prefix}... authenticated for user {api_key.user_id}")

        return api_key


class APIKeyOrBearerAuth:
    """
    FastAPI dependency that accepts either API key or Bearer token.

    Tries API key first, then falls back to Bearer token authentication.
    Useful for endpoints that need to support both external integrations
    and web app users.

    Usage:
        @router.get("/endpoint")
        async def my_endpoint(
            auth: tuple[Optional[APIKey], Optional[User]] = Depends(
                APIKeyOrBearerAuth(scopes=["read:grants"])
            )
        ):
            api_key, user = auth
            if api_key:
                # Authenticated via API key
                pass
            elif user:
                # Authenticated via Bearer token
                pass
    """

    def __init__(self, scopes: Optional[List[str]] = None):
        """
        Initialize auth dependency.

        Args:
            scopes: Optional list of required scopes (only checked for API keys)
        """
        self.scopes = scopes

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        api_key_value: Optional[str] = Security(api_key_header),
    ) -> tuple[Optional[APIKey], Optional["User"]]:
        """
        Validate either API key or Bearer token.

        Returns:
            Tuple of (APIKey or None, User or None)
        """
        # Try API key first
        if api_key_value:
            api_key = await validate_api_key(
                db=db,
                api_key=api_key_value,
                required_scopes=self.scopes,
            )
            if api_key:
                await update_last_used(db, api_key.id)
                request.state.api_key_id = api_key.id
                request.state.api_key_user_id = api_key.user_id
                return (api_key, None)

        # Fall back to Bearer token
        from fastapi.security import HTTPBearer

        # Try to get Bearer token
        bearer = HTTPBearer(auto_error=False)
        credentials = await bearer(request)
        if credentials:
            from backend.api.deps import decode_token
            from jose import JWTError
            from sqlalchemy import select

            try:
                from backend.models import User as UserModel

                token_data = decode_token(credentials.credentials)
                if token_data.exp and token_data.exp >= datetime.now(timezone.utc):
                    result = await db.execute(select(UserModel).where(UserModel.id == token_data.user_id))
                    user = result.scalar_one_or_none()
                    if user:
                        return (None, user)
            except JWTError:
                pass

        # Neither authentication method succeeded
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API key or Bearer token required",
            headers={"WWW-Authenticate": "ApiKey, Bearer"},
        )


async def get_api_key_user(
    api_key: APIKey = Depends(APIKeyAuth()),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get the User associated with an API key.

    Useful when you need both the API key and the user info.

    Args:
        api_key: The validated API key
        db: Database session

    Returns:
        User model associated with the API key
    """
    from sqlalchemy import select
    from backend.models import User as UserModel

    result = await db.execute(select(UserModel).where(UserModel.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key user not found",
        )

    return user


def require_scopes(*scopes: str):
    """
    Create an API key auth dependency that requires specific scopes.

    Usage:
        @router.get("/grants")
        async def list_grants(
            api_key: APIKey = Depends(require_scopes("read:grants"))
        ):
            pass

    Args:
        *scopes: Required scopes

    Returns:
        APIKeyAuth dependency configured with the required scopes
    """
    return APIKeyAuth(scopes=list(scopes))


# Convenience type aliases
APIKeyDep = Annotated[APIKey, Depends(APIKeyAuth())]
APIKeyReadGrants = Annotated[APIKey, Depends(APIKeyAuth(scopes=["read:grants"]))]
APIKeyWriteGrants = Annotated[APIKey, Depends(APIKeyAuth(scopes=["write:grants"]))]
APIKeyReadApplications = Annotated[APIKey, Depends(APIKeyAuth(scopes=["read:applications"]))]
APIKeyWriteApplications = Annotated[APIKey, Depends(APIKeyAuth(scopes=["write:applications"]))]
APIKeyAdmin = Annotated[APIKey, Depends(APIKeyAuth(scopes=["admin:api_keys"]))]
