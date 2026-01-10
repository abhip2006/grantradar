"""
Document Component Library Schemas
Pydantic models for component library API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import PaginationInfo


class ComponentCategory(str, Enum):
    """Categories for document components."""

    FACILITIES = "facilities"
    EQUIPMENT = "equipment"
    BIOSKETCH = "biosketch"
    BOILERPLATE = "boilerplate"
    INSTITUTION = "institution"
    OTHER = "other"


# =============================================================================
# Document Component Schemas
# =============================================================================


class ComponentBase(BaseModel):
    """Base schema for document components."""

    category: ComponentCategory
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Component metadata. See ComponentMetadataDict for expected structure.",
    )
    tags: Optional[List[str]] = None

    @field_validator("metadata")
    @classmethod
    def validate_metadata_structure(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate that metadata conforms to ComponentMetadataDict structure."""
        if v is None:
            return v

        # Optional: Validate known metadata fields if present
        # Allow additional keys for flexibility but this documents expected structure

        return v


class ComponentCreate(ComponentBase):
    """Create a new document component."""

    pass


class ComponentUpdate(BaseModel):
    """Update a document component."""

    category: Optional[ComponentCategory] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ComponentResponse(BaseModel):
    """Document component response."""

    id: UUID
    user_id: UUID
    category: str
    name: str
    description: Optional[str] = None
    content: str
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    version: int
    is_current: bool
    parent_id: Optional[UUID] = None
    is_archived: bool
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComponentListResponse(BaseModel):
    """Paginated component list (standard paginated format)."""

    data: List[ComponentResponse] = Field(..., description="List of components")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[ComponentResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


class ComponentVersionResponse(BaseModel):
    """Component version history item."""

    id: UUID
    version: int
    name: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Component Usage Schemas
# =============================================================================


class ComponentUsageCreate(BaseModel):
    """Record component usage in an application."""

    section: Optional[str] = Field(None, max_length=100)


class ComponentUsageResponse(BaseModel):
    """Component usage record response."""

    id: UUID
    component_id: UUID
    kanban_card_id: UUID
    section: Optional[str] = None
    inserted_by: Optional[UUID] = None
    used_at: datetime
    component_name: Optional[str] = None
    component_category: Optional[str] = None

    class Config:
        from_attributes = True


class ComponentUsageListResponse(BaseModel):
    """List of component usages (standard paginated format)."""

    data: List[ComponentUsageResponse] = Field(..., description="List of component usages")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[ComponentUsageResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


# =============================================================================
# Document Version Schemas
# =============================================================================


class VersionCreate(BaseModel):
    """Create a new document version snapshot."""

    section: Optional[str] = Field(None, max_length=100)
    content: str = Field(..., min_length=1)
    snapshot_name: Optional[str] = Field(None, max_length=255)
    change_summary: Optional[str] = Field(None, max_length=1000)


class VersionResponse(BaseModel):
    """Document version response."""

    id: UUID
    kanban_card_id: UUID
    section: Optional[str] = None
    version_number: int
    content: str
    snapshot_name: Optional[str] = None
    change_summary: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    created_by: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    """Paginated version list (standard paginated format)."""

    data: List[VersionResponse] = Field(..., description="List of versions")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[VersionResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


class VersionCompareResponse(BaseModel):
    """Response for comparing two versions."""

    version_a: VersionResponse
    version_b: VersionResponse
    # Diff information could be computed and added here


# =============================================================================
# Category Schemas
# =============================================================================


class CategoryCount(BaseModel):
    """Category with component count."""

    category: str
    count: int
    description: Optional[str] = None


class CategoryListResponse(BaseModel):
    """List of categories with counts."""

    categories: List[CategoryCount]


# =============================================================================
# Summary/Stats Schemas
# =============================================================================


class ComponentStats(BaseModel):
    """Statistics about user's component library."""

    total_components: int
    by_category: Dict[str, int]
    total_usages: int
    most_used_components: List[ComponentResponse]
