"""
Custom Exception Classes for the GrantRadar API.

Provides standardized HTTP exceptions with consistent error messages
across all API endpoints.
"""
from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, resource: str, id: str = None):
        detail = f"{resource} not found" + (f": {id}" if id else "")
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AuthorizationError(HTTPException):
    """Exception raised when a user is not authorized to access a resource."""

    def __init__(self, message: str = "Not authorized to access this resource"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=message)


class ValidationError(HTTPException):
    """Exception raised when request validation fails."""

    def __init__(self, message: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class ConflictError(HTTPException):
    """Exception raised when a resource conflict occurs (e.g., duplicate)."""

    def __init__(self, message: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


class RateLimitError(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)
