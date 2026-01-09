"""
Checklist schemas for request/response models.
Provides Pydantic models for checklist management API endpoints.
"""
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator

from backend.schemas.common import PaginatedResponse, PaginationInfo
from backend.schemas.jsonb_types import ChecklistItemDict


class ChecklistItemCategory(str, Enum):
    """Categories for checklist items."""

    ADMINISTRATIVE = "administrative"
    SCIENTIFIC = "scientific"
    BUDGET = "budget"
    PERSONNEL = "personnel"
    COMPLIANCE = "compliance"
    DOCUMENTS = "documents"
    REVIEW = "review"
    OTHER = "other"


# =============================================================================
# Checklist Item Schemas
# =============================================================================


class ChecklistItemBase(BaseModel):
    """Base schema for a checklist item."""

    id: str = Field(..., description="Unique identifier for the item within the checklist")
    title: str = Field(..., min_length=1, max_length=500, description="Item title")
    description: Optional[str] = Field(None, description="Detailed description of the item")
    required: bool = Field(True, description="Whether this item is required for completion")
    weight: float = Field(1.0, ge=0.0, le=10.0, description="Weight for progress calculation")
    category: ChecklistItemCategory = Field(
        ChecklistItemCategory.OTHER,
        description="Category of the checklist item",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="IDs of items that must be completed before this one",
    )


class ChecklistItemCreate(BaseModel):
    """Schema for creating a new checklist item."""

    title: str = Field(..., min_length=1, max_length=500, description="Item title")
    description: Optional[str] = Field(None, description="Detailed description of the item")
    required: bool = Field(True, description="Whether this item is required for completion")
    weight: float = Field(1.0, ge=0.0, le=10.0, description="Weight for progress calculation")
    category: ChecklistItemCategory = Field(
        ChecklistItemCategory.OTHER,
        description="Category of the checklist item",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="IDs of items that must be completed before this one",
    )


class ChecklistItemStatus(BaseModel):
    """Schema for a checklist item with completion status."""

    item_id: str = Field(..., description="Reference to the checklist item")
    title: str = Field(..., description="Item title")
    description: Optional[str] = Field(None, description="Item description")
    required: bool = Field(True, description="Whether this item is required")
    weight: float = Field(1.0, description="Weight for progress calculation")
    category: ChecklistItemCategory = Field(
        ChecklistItemCategory.OTHER,
        description="Item category",
    )
    dependencies: List[str] = Field(default_factory=list, description="Dependency item IDs")
    completed: bool = Field(False, description="Whether the item is completed")
    completed_at: Optional[datetime] = Field(None, description="When the item was completed")
    completed_by: Optional[UUID] = Field(None, description="User who completed the item")
    notes: Optional[str] = Field(None, description="Notes about completion")


class ChecklistItemUpdate(BaseModel):
    """Schema for updating a checklist item's status."""

    completed: Optional[bool] = Field(None, description="Mark item as completed/incomplete")
    notes: Optional[str] = Field(None, max_length=2000, description="Notes about completion")


# =============================================================================
# Checklist Template Schemas
# =============================================================================


class ChecklistTemplateBase(BaseModel):
    """Base schema for checklist templates."""

    funder: str = Field(..., min_length=1, max_length=100, description="Funding organization")
    mechanism: Optional[str] = Field(None, max_length=50, description="Grant mechanism type")
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")


class ChecklistTemplateCreate(ChecklistTemplateBase):
    """Schema for creating a checklist template."""

    items: List[ChecklistItemCreate] = Field(
        default_factory=list,
        description="Checklist items",
    )

    @field_validator("items")
    @classmethod
    def validate_items_structure(cls, v: List[ChecklistItemCreate]) -> List[ChecklistItemCreate]:
        """Validate that items conform to ChecklistItemDict structure."""
        if not v:
            return v

        # Validate item IDs are unique (if they will be assigned)
        # Additional validation can be added here
        seen_titles = set()
        for item in v:
            if item.title in seen_titles:
                raise ValueError(f"Duplicate item title found: {item.title}")
            seen_titles.add(item.title)

        return v


class ChecklistTemplateResponse(ChecklistTemplateBase):
    """Schema for checklist template response."""

    id: UUID = Field(..., description="Template ID")
    items: List[ChecklistItemBase] = Field(..., description="Checklist items")
    is_system: bool = Field(..., description="Whether this is a system template")
    created_by: Optional[UUID] = Field(None, description="User who created the template")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @computed_field
    @property
    def total_items(self) -> int:
        """Total number of items in the checklist."""
        return len(self.items)

    @computed_field
    @property
    def required_items(self) -> int:
        """Number of required items in the checklist."""
        return sum(1 for item in self.items if item.required)

    class Config:
        from_attributes = True


class ChecklistTemplateList(BaseModel):
    """Schema for list of checklist templates (standard paginated format)."""

    data: List[ChecklistTemplateResponse] = Field(..., description="List of templates")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[ChecklistTemplateResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


# =============================================================================
# Application Checklist Schemas
# =============================================================================


class ApplicationChecklistCreate(BaseModel):
    """Schema for creating a checklist for an application."""

    template_id: Optional[UUID] = Field(
        None,
        description="ID of template to use (if not creating custom)",
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Custom checklist name (required if no template_id)",
    )
    items: Optional[List[ChecklistItemCreate]] = Field(
        None,
        description="Custom checklist items (required if no template_id)",
    )


class ApplicationChecklistResponse(BaseModel):
    """Schema for application checklist response."""

    id: UUID = Field(..., description="Checklist ID")
    kanban_card_id: UUID = Field(..., description="Associated application/card ID")
    template_id: Optional[UUID] = Field(None, description="Source template ID")
    name: str = Field(..., description="Checklist name")
    items: List[ChecklistItemStatus] = Field(..., description="Checklist items with status")
    progress_percent: float = Field(..., description="Completion percentage (0-100)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @computed_field
    @property
    def total_items(self) -> int:
        """Total number of items."""
        return len(self.items)

    @computed_field
    @property
    def completed_items(self) -> int:
        """Number of completed items."""
        return sum(1 for item in self.items if item.completed)

    @computed_field
    @property
    def required_items(self) -> int:
        """Number of required items."""
        return sum(1 for item in self.items if item.required)

    @computed_field
    @property
    def required_completed(self) -> int:
        """Number of required items that are completed."""
        return sum(1 for item in self.items if item.required and item.completed)

    @computed_field
    @property
    def all_required_complete(self) -> bool:
        """Whether all required items are completed."""
        return self.required_completed == self.required_items

    class Config:
        from_attributes = True


class ApplicationChecklistList(BaseModel):
    """Schema for list of application checklists (standard paginated format)."""

    data: List[ApplicationChecklistResponse] = Field(..., description="List of checklists")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[ApplicationChecklistResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


class ChecklistProgressSummary(BaseModel):
    """Summary of checklist progress for a card."""

    total_checklists: int = Field(..., description="Total number of checklists")
    overall_progress: float = Field(..., description="Average progress across all checklists")
    all_complete: bool = Field(..., description="Whether all checklists are 100% complete")
    checklists: List[ApplicationChecklistResponse] = Field(..., description="Individual checklists")


# =============================================================================
# Funder Templates Response
# =============================================================================


class FunderTemplatesResponse(BaseModel):
    """Schema for templates grouped by funder."""

    funder: str = Field(..., description="Funder name")
    templates: List[ChecklistTemplateResponse] = Field(..., description="Templates for this funder")
    total: int = Field(..., description="Number of templates for this funder")
