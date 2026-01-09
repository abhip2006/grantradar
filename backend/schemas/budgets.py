"""
Budget Schemas
Pydantic models for budget template API.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Category Schemas
# =============================================================================

class BudgetCategoryInfo(BaseModel):
    """Information about a budget category."""
    code: str
    name: str
    description: str
    is_direct_cost: bool = True
    typical_percentage_min: float
    typical_percentage_max: float


class CategoryAllocation(BaseModel):
    """Allocation for a single budget category."""
    percentage: float = Field(..., ge=0, le=100)
    total_amount: int = Field(..., ge=0)
    annual_amount: int = Field(..., ge=0)
    typical_range: Optional[Dict[str, float]] = None


# =============================================================================
# Template Schemas
# =============================================================================

class MechanismTemplateResponse(BaseModel):
    """Budget template for a grant mechanism."""
    mechanism_code: str
    mechanism_name: str
    agency: str
    typical_annual_budget_min: int
    typical_annual_budget_max: int
    typical_duration_years: int
    modular_budget: bool
    modular_increment: Optional[int] = None
    max_annual_direct: Optional[int] = None
    category_allocations: Dict[str, Dict[str, float]]
    notes: List[str]
    validation_rules: List[Dict[str, Any]]


class TemplateListResponse(BaseModel):
    """List of available budget templates."""
    templates: List[MechanismTemplateResponse]
    total: int


# =============================================================================
# Budget Generation Schemas
# =============================================================================

class BudgetGenerateRequest(BaseModel):
    """Request to generate a budget breakdown."""
    mechanism_code: str = Field(..., description="Grant mechanism code (e.g., 'R01', 'CAREER')")
    total_direct_costs: int = Field(..., ge=1000, description="Total direct costs in dollars")
    duration_years: int = Field(1, ge=1, le=10, description="Number of years for the budget")
    fa_rate: Optional[float] = Field(None, ge=0, le=1, description="F&A rate (0-1), uses default if not provided")
    custom_allocations: Optional[Dict[str, float]] = Field(None, description="Custom category allocations (percentages)")


class BudgetBreakdownResponse(BaseModel):
    """Generated budget breakdown."""
    mechanism: str
    mechanism_name: str
    agency: str
    total_direct_costs: int
    annual_direct_costs: int
    duration_years: int
    categories: Dict[str, CategoryAllocation]
    fa_rate: float
    mtdc: int
    indirect_costs: int
    total_budget: int
    annual_total_budget: int
    notes: List[str]
    modular_budget: bool
    modular_increment: Optional[int] = None


# =============================================================================
# Budget Validation Schemas
# =============================================================================

class BudgetValidateRequest(BaseModel):
    """Request to validate a budget."""
    mechanism_code: str = Field(..., description="Grant mechanism code")
    total_direct_costs: int = Field(..., ge=0)
    duration_years: int = Field(1, ge=1, le=10)
    categories: Dict[str, Dict[str, Any]] = Field(..., description="Category allocations with percentage and amounts")


class ValidationIssue(BaseModel):
    """A validation error or warning."""
    rule: Optional[str] = None
    category: Optional[str] = None
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None


class BudgetValidationResponse(BaseModel):
    """Budget validation results."""
    is_valid: bool
    mechanism: str
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    template_notes: List[str]


# =============================================================================
# User Budget Schemas
# =============================================================================

class BudgetLineItem(BaseModel):
    """Individual line item in a budget."""
    category: str
    subcategory: Optional[str] = None
    description: str
    amount: int = Field(..., ge=0)
    justification: Optional[str] = None
    notes: Optional[str] = None


class BudgetYear(BaseModel):
    """Budget for a single year."""
    year: int = Field(..., ge=1, le=10)
    line_items: List[BudgetLineItem]
    total_direct: int = Field(..., ge=0)
    indirect_costs: int = Field(0, ge=0)
    total: int = Field(..., ge=0)


class UserBudgetData(BaseModel):
    """Complete user budget data."""
    mechanism_code: Optional[str] = None
    fa_rate: float = Field(0.5, ge=0, le=1)
    duration_years: int = Field(1, ge=1, le=10)
    years: List[BudgetYear]
    notes: Optional[str] = None
    status: str = Field("draft", description="Budget status: draft, review, final")


class UserBudgetCreate(BaseModel):
    """Create a new user budget."""
    grant_id: Optional[UUID] = None
    match_id: Optional[UUID] = None
    budget_data: UserBudgetData


class UserBudgetUpdate(BaseModel):
    """Update an existing user budget."""
    budget_data: Optional[UserBudgetData] = None
    notes: Optional[str] = None


class UserBudgetResponse(BaseModel):
    """User budget response."""
    id: UUID
    user_id: UUID
    grant_id: Optional[UUID] = None
    match_id: Optional[UUID] = None
    budget_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBudgetListResponse(BaseModel):
    """List of user budgets."""
    items: List[UserBudgetResponse]
    total: int


# =============================================================================
# Salary Cap Schemas
# =============================================================================

class SalaryCapResponse(BaseModel):
    """Salary cap information."""
    fiscal_year: int
    cap_amount: int
    agency: str
    notes: str


class FringeRatesResponse(BaseModel):
    """Fringe benefit rates."""
    faculty: float
    postdoc: float
    graduate_student: float
    staff: float
    default: float


class RatesResponse(BaseModel):
    """F&A and fringe rates."""
    fa_rates: Dict[str, float]
    fringe_rates: FringeRatesResponse
    current_salary_cap: SalaryCapResponse
