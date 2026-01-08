"""
Template Schemas
Pydantic models for template API.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateVariable(BaseModel):
    """Variable definition for a template."""
    name: str
    type: str = "text"  # text, number, date, select
    description: Optional[str] = None
    default: Optional[str] = None
    options: Optional[List[str]] = None  # For select type
    required: bool = True


class TemplateCategoryResponse(BaseModel):
    """Template category with count."""
    id: UUID
    name: str
    description: Optional[str] = None
    display_order: int
    template_count: int = 0


class TemplateCreate(BaseModel):
    """Create a new template."""
    category_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    content: str = Field(..., min_length=1)
    variables: Optional[List[Dict[str, Any]]] = None
    is_public: Optional[bool] = False


class TemplateUpdate(BaseModel):
    """Update a template."""
    category_id: Optional[UUID] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    content: Optional[str] = Field(None, min_length=1)
    variables: Optional[List[Dict[str, Any]]] = None
    is_public: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Template response."""
    id: UUID
    user_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    content: str
    variables: List[Dict[str, Any]] = []
    is_public: bool
    is_system: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Paginated template list."""
    items: List[TemplateResponse]
    total: int


class TemplateRenderRequest(BaseModel):
    """Request to render a template."""
    variables: Dict[str, Any]


class TemplateRenderResponse(BaseModel):
    """Rendered template content."""
    rendered_content: str
