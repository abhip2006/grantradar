"""
Common schemas for standardized API responses.
Provides base classes for consistent pagination across all list endpoints.
"""
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginationInfo(BaseModel):
    """Pagination metadata for list responses."""
    total: int = Field(..., description="Total number of items")
    offset: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether more items exist beyond this page")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response format for all list endpoints.

    All list endpoints should return this format for consistency:
    {
        "data": [...],
        "pagination": {
            "total": int,
            "offset": int,
            "limit": int,
            "has_more": bool
        }
    }
    """
    data: List[T] = Field(..., description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


def create_paginated_response(
    items: List,
    total: int,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    """
    Helper function to create a paginated response dictionary.

    Args:
        items: List of items to include in response
        total: Total count of all items (not just this page)
        offset: Number of items skipped
        limit: Maximum items requested per page

    Returns:
        Dictionary with 'data' and 'pagination' keys
    """
    return {
        "data": items,
        "pagination": {
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + len(items)) < total,
        }
    }


__all__ = [
    "PaginationInfo",
    "PaginatedResponse",
    "create_paginated_response",
]
