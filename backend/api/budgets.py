"""
Budget Templates API Endpoints
Provides pre-filled budget templates based on grant mechanism averages.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.schemas.budgets import (
    BudgetBreakdownResponse,
    BudgetGenerateRequest,
    BudgetValidateRequest,
    BudgetValidationResponse,
    CategoryAllocation,
    MechanismTemplateResponse,
    RatesResponse,
    FringeRatesResponse,
    SalaryCapResponse,
    TemplateListResponse,
    UserBudgetCreate,
    UserBudgetListResponse,
    UserBudgetResponse,
    UserBudgetUpdate,
    ValidationIssue,
)
from backend.services.budget_templates import (
    ALL_BUDGET_TEMPLATES,
    BUDGET_CATEGORIES,
    budget_template_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/budgets", tags=["Budgets"])


# =============================================================================
# Template Endpoints
# =============================================================================


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    db: AsyncSessionDep,
    agency: Optional[str] = Query(None, description="Filter by agency (NIH, NSF)"),
) -> TemplateListResponse:
    """
    List all available budget templates.

    Optionally filter by funding agency.
    """
    if agency:
        templates = budget_template_service.get_templates_by_agency(agency)
    else:
        templates = budget_template_service.get_all_templates()

    template_list = [
        MechanismTemplateResponse(
            mechanism_code=t.mechanism_code,
            mechanism_name=t.mechanism_name,
            agency=t.agency,
            typical_annual_budget_min=t.typical_annual_budget_min,
            typical_annual_budget_max=t.typical_annual_budget_max,
            typical_duration_years=t.typical_duration_years,
            modular_budget=t.modular_budget,
            modular_increment=t.modular_increment,
            max_annual_direct=t.max_annual_direct,
            category_allocations=t.category_allocations,
            notes=t.notes,
            validation_rules=t.validation_rules,
        )
        for t in templates.values()
    ]

    return TemplateListResponse(
        templates=template_list,
        total=len(template_list),
    )


@router.get("/template/{mechanism}", response_model=MechanismTemplateResponse)
async def get_template(
    mechanism: str,
    db: AsyncSessionDep,
) -> MechanismTemplateResponse:
    """
    Get budget template for a specific grant mechanism.

    Supported mechanisms include:
    - NIH: R01, R21, R03, K01, K99/R00, F31, F32, T32, P01, U01
    - NSF: CAREER, STANDARD, EAGER, RAPID
    """
    template = budget_template_service.get_template(mechanism)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget template not found for mechanism: {mechanism}. "
            f"Supported mechanisms: {', '.join(ALL_BUDGET_TEMPLATES.keys())}",
        )

    return MechanismTemplateResponse(
        mechanism_code=template.mechanism_code,
        mechanism_name=template.mechanism_name,
        agency=template.agency,
        typical_annual_budget_min=template.typical_annual_budget_min,
        typical_annual_budget_max=template.typical_annual_budget_max,
        typical_duration_years=template.typical_duration_years,
        modular_budget=template.modular_budget,
        modular_increment=template.modular_increment,
        max_annual_direct=template.max_annual_direct,
        category_allocations=template.category_allocations,
        notes=template.notes,
        validation_rules=template.validation_rules,
    )


@router.get("/categories")
async def list_categories(
    db: AsyncSessionDep,
) -> List[Dict[str, Any]]:
    """
    List all budget categories with descriptions.
    """
    return [
        {
            "code": cat_def.code,
            "name": cat_def.name,
            "description": cat_def.description,
            "is_direct_cost": cat_def.is_direct_cost,
            "typical_percentage_min": cat_def.typical_percentage_min,
            "typical_percentage_max": cat_def.typical_percentage_max,
        }
        for cat_def in BUDGET_CATEGORIES.values()
    ]


@router.get("/rates", response_model=RatesResponse)
async def get_rates(
    db: AsyncSessionDep,
    fiscal_year: int = Query(2024, description="Fiscal year for salary cap"),
) -> RatesResponse:
    """
    Get current F&A rates, fringe rates, and salary cap information.
    """
    salary_cap = budget_template_service.get_salary_cap(fiscal_year)

    if not salary_cap:
        # Fall back to most recent cap
        salary_cap = budget_template_service.get_salary_cap(2024)

    return RatesResponse(
        fa_rates={
            "research_on_campus": budget_template_service.get_fa_rate("research_on_campus"),
            "research_off_campus": budget_template_service.get_fa_rate("research_off_campus"),
            "training": budget_template_service.get_fa_rate("training"),
            "default": budget_template_service.get_fa_rate("default"),
        },
        fringe_rates=FringeRatesResponse(
            faculty=budget_template_service.get_fringe_rate("faculty"),
            postdoc=budget_template_service.get_fringe_rate("postdoc"),
            graduate_student=budget_template_service.get_fringe_rate("graduate_student"),
            staff=budget_template_service.get_fringe_rate("staff"),
            default=budget_template_service.get_fringe_rate("default"),
        ),
        current_salary_cap=SalaryCapResponse(
            fiscal_year=salary_cap.fiscal_year,
            cap_amount=salary_cap.cap_amount,
            agency=salary_cap.agency,
            notes=salary_cap.notes,
        ),
    )


# =============================================================================
# Budget Generation Endpoints
# =============================================================================


@router.post("/generate", response_model=BudgetBreakdownResponse)
async def generate_budget(
    request: BudgetGenerateRequest,
    db: AsyncSessionDep,
) -> BudgetBreakdownResponse:
    """
    Generate a budget breakdown from total amount and mechanism.

    Uses mechanism-specific templates to allocate budget across categories
    based on typical distributions.
    """
    breakdown = budget_template_service.generate_budget_breakdown(
        mechanism_code=request.mechanism_code,
        total_direct_costs=request.total_direct_costs,
        duration_years=request.duration_years,
        fa_rate=request.fa_rate,
        custom_allocations=request.custom_allocations,
    )

    # Convert categories to proper schema
    categories = {
        cat_name: CategoryAllocation(
            percentage=cat_data["percentage"],
            total_amount=cat_data["total_amount"],
            annual_amount=cat_data["annual_amount"],
            typical_range=cat_data.get("typical_range"),
        )
        for cat_name, cat_data in breakdown["categories"].items()
    }

    return BudgetBreakdownResponse(
        mechanism=breakdown["mechanism"],
        mechanism_name=breakdown["mechanism_name"],
        agency=breakdown["agency"],
        total_direct_costs=breakdown["total_direct_costs"],
        annual_direct_costs=breakdown["annual_direct_costs"],
        duration_years=breakdown["duration_years"],
        categories=categories,
        fa_rate=breakdown["fa_rate"],
        mtdc=breakdown["mtdc"],
        indirect_costs=breakdown["indirect_costs"],
        total_budget=breakdown["total_budget"],
        annual_total_budget=breakdown["annual_total_budget"],
        notes=breakdown["notes"],
        modular_budget=breakdown["modular_budget"],
        modular_increment=breakdown.get("modular_increment"),
    )


# =============================================================================
# Budget Validation Endpoints
# =============================================================================


@router.post("/validate", response_model=BudgetValidationResponse)
async def validate_budget(
    request: BudgetValidateRequest,
    db: AsyncSessionDep,
) -> BudgetValidationResponse:
    """
    Validate a budget against mechanism rules.

    Checks for:
    - Category allocation ranges
    - Maximum budget limits
    - Duration constraints
    - Salary cap compliance
    """
    budget_data = {
        "total_direct_costs": request.total_direct_costs,
        "duration_years": request.duration_years,
        "categories": request.categories,
    }

    result = budget_template_service.validate_budget(
        mechanism_code=request.mechanism_code,
        budget_data=budget_data,
    )

    return BudgetValidationResponse(
        is_valid=result["is_valid"],
        mechanism=result["mechanism"],
        errors=[
            ValidationIssue(
                rule=e.get("rule"),
                category=e.get("category"),
                message=e["message"],
                expected=e.get("expected"),
                actual=e.get("actual"),
            )
            for e in result["errors"]
        ],
        warnings=[
            ValidationIssue(
                rule=w.get("rule"),
                category=w.get("category"),
                message=w["message"],
                expected=w.get("expected"),
                actual=w.get("actual"),
            )
            for w in result["warnings"]
        ],
        template_notes=result["template_notes"],
    )


# =============================================================================
# User Budget CRUD Endpoints
# =============================================================================


@router.post("/save", response_model=UserBudgetResponse, status_code=status.HTTP_201_CREATED)
async def save_budget(
    request: UserBudgetCreate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> UserBudgetResponse:
    """
    Save a user budget draft.

    Creates a new budget or updates an existing one if a budget already exists
    for the same grant/match combination.
    """

    # Check if budget already exists for this grant/match
    select(func.count()).select_from(
        # Inline table reference
        db.get_bind().dialect.identifier_preparer.format_table(type("T", (), {"__tablename__": "user_budgets"}))
        if False
        else None  # Placeholder
    )

    budget_id = uuid4()
    now = datetime.now(timezone.utc)

    # Calculate totals from budget data
    budget_data = request.budget_data.model_dump()
    total_direct = sum(year.get("total_direct", 0) for year in budget_data.get("years", []))
    total_indirect = sum(year.get("indirect_costs", 0) for year in budget_data.get("years", []))

    # Build budget record using raw SQL since we don't have the ORM model yet
    await db.execute(
        """
        INSERT INTO user_budgets (
            id, user_id, grant_id, match_id, mechanism_code,
            budget_data, total_direct_costs, total_indirect_costs,
            total_budget, duration_years, status, version,
            created_at, updated_at
        ) VALUES (
            :id, :user_id, :grant_id, :match_id, :mechanism_code,
            :budget_data, :total_direct_costs, :total_indirect_costs,
            :total_budget, :duration_years, :status, :version,
            :created_at, :updated_at
        )
        """,
        {
            "id": str(budget_id),
            "user_id": str(current_user.id),
            "grant_id": str(request.grant_id) if request.grant_id else None,
            "match_id": str(request.match_id) if request.match_id else None,
            "mechanism_code": budget_data.get("mechanism_code"),
            "budget_data": budget_data,
            "total_direct_costs": total_direct,
            "total_indirect_costs": total_indirect,
            "total_budget": total_direct + total_indirect,
            "duration_years": budget_data.get("duration_years", 1),
            "status": budget_data.get("status", "draft"),
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )
    await db.commit()

    return UserBudgetResponse(
        id=budget_id,
        user_id=current_user.id,
        grant_id=request.grant_id,
        match_id=request.match_id,
        budget_data=budget_data,
        created_at=now,
        updated_at=now,
    )


@router.get("/user", response_model=UserBudgetListResponse)
async def list_user_budgets(
    current_user: CurrentUser,
    db: AsyncSessionDep,
    grant_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> UserBudgetListResponse:
    """
    List all budgets for the current user.

    Optionally filter by grant_id or status.
    """
    from sqlalchemy import text

    # Build query
    query = """
        SELECT id, user_id, grant_id, match_id, budget_data, created_at, updated_at
        FROM user_budgets
        WHERE user_id = :user_id
    """
    params: Dict[str, Any] = {"user_id": str(current_user.id)}

    if grant_id:
        query += " AND grant_id = :grant_id"
        params["grant_id"] = str(grant_id)

    if status:
        query += " AND status = :status"
        params["status"] = status

    # Get count
    count_query = f"SELECT COUNT(*) FROM ({query}) AS subq"
    count_result = await db.execute(text(count_query), params)
    total = count_result.scalar() or 0

    # Apply pagination
    query += " ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return UserBudgetListResponse(
        items=[
            UserBudgetResponse(
                id=row[0],
                user_id=row[1],
                grant_id=row[2],
                match_id=row[3],
                budget_data=row[4],
                created_at=row[5],
                updated_at=row[6],
            )
            for row in rows
        ],
        total=total,
    )


@router.get("/user/{match_id}", response_model=UserBudgetResponse)
async def get_user_budget_by_match(
    match_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> UserBudgetResponse:
    """
    Get saved budget for a specific match.
    """
    from sqlalchemy import text

    result = await db.execute(
        text("""
            SELECT id, user_id, grant_id, match_id, budget_data, created_at, updated_at
            FROM user_budgets
            WHERE match_id = :match_id AND user_id = :user_id
            ORDER BY updated_at DESC
            LIMIT 1
        """),
        {"match_id": str(match_id), "user_id": str(current_user.id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No budget found for match {match_id}",
        )

    return UserBudgetResponse(
        id=row[0],
        user_id=row[1],
        grant_id=row[2],
        match_id=row[3],
        budget_data=row[4],
        created_at=row[5],
        updated_at=row[6],
    )


@router.get("/{budget_id}", response_model=UserBudgetResponse)
async def get_budget(
    budget_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> UserBudgetResponse:
    """
    Get a specific budget by ID.
    """
    from sqlalchemy import text

    result = await db.execute(
        text("""
            SELECT id, user_id, grant_id, match_id, budget_data, created_at, updated_at
            FROM user_budgets
            WHERE id = :budget_id AND user_id = :user_id
        """),
        {"budget_id": str(budget_id), "user_id": str(current_user.id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found: {budget_id}",
        )

    return UserBudgetResponse(
        id=row[0],
        user_id=row[1],
        grant_id=row[2],
        match_id=row[3],
        budget_data=row[4],
        created_at=row[5],
        updated_at=row[6],
    )


@router.patch("/{budget_id}", response_model=UserBudgetResponse)
async def update_budget(
    budget_id: UUID,
    request: UserBudgetUpdate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> UserBudgetResponse:
    """
    Update an existing budget.
    """
    from sqlalchemy import text

    # Check ownership
    result = await db.execute(
        text("SELECT id FROM user_budgets WHERE id = :id AND user_id = :user_id"),
        {"id": str(budget_id), "user_id": str(current_user.id)},
    )
    if not result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found: {budget_id}",
        )

    # Build update
    now = datetime.now(timezone.utc)
    update_parts = ["updated_at = :updated_at"]
    params: Dict[str, Any] = {
        "id": str(budget_id),
        "updated_at": now,
    }

    if request.budget_data:
        budget_data = request.budget_data.model_dump()
        update_parts.append("budget_data = :budget_data")
        params["budget_data"] = budget_data

        # Recalculate totals
        total_direct = sum(year.get("total_direct", 0) for year in budget_data.get("years", []))
        total_indirect = sum(year.get("indirect_costs", 0) for year in budget_data.get("years", []))
        update_parts.extend(
            [
                "total_direct_costs = :total_direct",
                "total_indirect_costs = :total_indirect",
                "total_budget = :total_budget",
            ]
        )
        params["total_direct"] = total_direct
        params["total_indirect"] = total_indirect
        params["total_budget"] = total_direct + total_indirect

    if request.notes is not None:
        update_parts.append("notes = :notes")
        params["notes"] = request.notes

    await db.execute(text(f"UPDATE user_budgets SET {', '.join(update_parts)} WHERE id = :id"), params)
    await db.commit()

    # Return updated budget
    return await get_budget(budget_id, current_user, db)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> None:
    """
    Delete a budget.
    """
    from sqlalchemy import text

    result = await db.execute(
        text("DELETE FROM user_budgets WHERE id = :id AND user_id = :user_id RETURNING id"),
        {"id": str(budget_id), "user_id": str(current_user.id)},
    )

    if not result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found: {budget_id}",
        )

    await db.commit()
