"""
Standardized API response schemas.

Provides consistent response wrappers for all API endpoints.
Re-exports pagination schemas from common.py for convenience.
"""
from typing import Generic, TypeVar, List

from pydantic import BaseModel, Field

# Re-export pagination schemas from common.py
from backend.schemas.common import PaginationInfo, PaginatedResponse, create_paginated_response

T = TypeVar('T')


class PaginationMeta(BaseModel):
    """
    Pagination metadata.

    Alias for PaginationInfo for backwards compatibility.
    """
    total: int = Field(..., description="Total number of items")
    offset: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether more items exist beyond this page")


class SingleResponse(BaseModel, Generic[T]):
    """
    Standard single item response wrapper.

    Use this for endpoints that return a single resource:
    {
        "data": {...}
    }
    """
    data: T = Field(..., description="The requested resource")


class SuccessResponse(BaseModel):
    """
    Standard success response for operations.

    Use this for endpoints that perform actions without returning data:
    {
        "success": true,
        "message": "Operation completed successfully"
    }
    """
    success: bool = Field(default=True, description="Whether the operation was successful")
    message: str = Field(..., description="Description of the operation result")


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    FastAPI automatically generates this for HTTPException responses:
    {
        "detail": "Error message"
    }
    """
    detail: str = Field(..., description="Error message describing what went wrong")


class ErrorDetail(BaseModel):
    """
    Detailed error information for validation errors.

    Used in validation error responses:
    {
        "detail": [
            {"loc": ["body", "field"], "msg": "error message", "type": "error_type"}
        ]
    }
    """
    loc: List[str] = Field(..., description="Location of the error (path to the field)")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type identifier")


class ValidationErrorResponse(BaseModel):
    """
    Standard validation error response.

    FastAPI automatically generates this for RequestValidationError:
    {
        "detail": [
            {"loc": ["body", "field"], "msg": "error message", "type": "error_type"}
        ]
    }
    """
    detail: List[ErrorDetail] = Field(..., description="List of validation errors")


__all__ = [
    # Re-exported from common.py
    "PaginationInfo",
    "PaginatedResponse",
    "create_paginated_response",
    # New response schemas
    "PaginationMeta",
    "SingleResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    "ValidationErrorResponse",
]
