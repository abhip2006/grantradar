"""
Budget Templates Service
Provides pre-filled budget templates based on grant mechanism averages.

This service handles:
- Budget category definitions
- Typical budget allocations by mechanism
- Salary caps and distribution rules
- Budget validation rules
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Budget Categories
# =============================================================================


class BudgetCategory(str, Enum):
    """Standard budget categories for grant proposals."""

    PERSONNEL = "personnel"
    EQUIPMENT = "equipment"
    TRAVEL = "travel"
    SUPPLIES = "supplies"
    CONSULTANTS = "consultants"
    OTHER = "other"
    INDIRECT = "indirect"  # F&A costs


@dataclass
class CategoryDefinition:
    """Definition for a budget category."""

    code: str
    name: str
    description: str
    is_direct_cost: bool = True
    typical_percentage_min: float = 0.0
    typical_percentage_max: float = 100.0


BUDGET_CATEGORIES = {
    BudgetCategory.PERSONNEL: CategoryDefinition(
        code="personnel",
        name="Personnel",
        description="Salaries, wages, and fringe benefits for PI, co-investigators, postdocs, graduate students, and staff",
        is_direct_cost=True,
        typical_percentage_min=40.0,
        typical_percentage_max=80.0,
    ),
    BudgetCategory.EQUIPMENT: CategoryDefinition(
        code="equipment",
        name="Equipment",
        description="Equipment items costing $5,000 or more per unit with useful life of more than one year",
        is_direct_cost=True,
        typical_percentage_min=0.0,
        typical_percentage_max=30.0,
    ),
    BudgetCategory.TRAVEL: CategoryDefinition(
        code="travel",
        name="Travel",
        description="Domestic and international travel for conferences, collaborations, and fieldwork",
        is_direct_cost=True,
        typical_percentage_min=1.0,
        typical_percentage_max=10.0,
    ),
    BudgetCategory.SUPPLIES: CategoryDefinition(
        code="supplies",
        name="Supplies",
        description="Consumable materials, chemicals, reagents, software licenses, publication costs",
        is_direct_cost=True,
        typical_percentage_min=5.0,
        typical_percentage_max=25.0,
    ),
    BudgetCategory.CONSULTANTS: CategoryDefinition(
        code="consultants",
        name="Consultants/Subawards",
        description="Consultant fees, subcontracts, and collaborative agreements",
        is_direct_cost=True,
        typical_percentage_min=0.0,
        typical_percentage_max=40.0,
    ),
    BudgetCategory.OTHER: CategoryDefinition(
        code="other",
        name="Other Direct Costs",
        description="Participant support, animal care, human subjects costs, service center charges",
        is_direct_cost=True,
        typical_percentage_min=0.0,
        typical_percentage_max=20.0,
    ),
    BudgetCategory.INDIRECT: CategoryDefinition(
        code="indirect",
        name="Indirect Costs (F&A)",
        description="Facilities and Administrative costs - overhead charged on modified total direct costs (MTDC)",
        is_direct_cost=False,
        typical_percentage_min=40.0,
        typical_percentage_max=60.0,
    ),
}


# =============================================================================
# Salary Caps and Rates
# =============================================================================


@dataclass
class SalaryCapInfo:
    """Salary cap information for a fiscal year."""

    fiscal_year: int
    cap_amount: int
    agency: str
    notes: str


# NIH Salary Cap - Executive Level II
NIH_SALARY_CAPS = {
    2024: SalaryCapInfo(
        fiscal_year=2024,
        cap_amount=221900,
        agency="NIH",
        notes="Executive Level II salary cap effective January 2024",
    ),
    2023: SalaryCapInfo(
        fiscal_year=2023,
        cap_amount=212100,
        agency="NIH",
        notes="Executive Level II salary cap effective January 2023",
    ),
    2022: SalaryCapInfo(
        fiscal_year=2022,
        cap_amount=203700,
        agency="NIH",
        notes="Executive Level II salary cap effective January 2022",
    ),
}

# Default F&A rates (institutions typically have negotiated rates)
DEFAULT_FA_RATES = {
    "research_on_campus": 0.52,  # 52% typical
    "research_off_campus": 0.26,  # 26% typical
    "training": 0.08,  # 8% for training grants
    "default": 0.50,  # 50% default
}

# Fringe benefit rates (vary by institution and employee type)
DEFAULT_FRINGE_RATES = {
    "faculty": 0.30,  # 30% typical for faculty
    "postdoc": 0.25,  # 25% for postdocs
    "graduate_student": 0.10,  # 10% for grad students
    "staff": 0.35,  # 35% for staff
    "default": 0.30,
}


# =============================================================================
# Mechanism Budget Templates
# =============================================================================


@dataclass
class MechanismBudgetTemplate:
    """Budget template for a specific grant mechanism."""

    mechanism_code: str
    mechanism_name: str
    agency: str
    typical_annual_budget_min: int
    typical_annual_budget_max: int
    typical_duration_years: int
    modular_budget: bool
    modular_increment: Optional[int]
    max_annual_direct: Optional[int]
    category_allocations: dict[str, dict[str, float]]  # category -> {min, max, typical}
    notes: list[str]
    validation_rules: list[dict[str, Any]]


# NIH Mechanism Templates
NIH_BUDGET_TEMPLATES = {
    "R01": MechanismBudgetTemplate(
        mechanism_code="R01",
        mechanism_name="Research Project Grant",
        agency="NIH",
        typical_annual_budget_min=250000,
        typical_annual_budget_max=500000,
        typical_duration_years=5,
        modular_budget=True,
        modular_increment=25000,
        max_annual_direct=250000,
        category_allocations={
            "personnel": {"min": 50.0, "max": 80.0, "typical": 65.0},
            "equipment": {"min": 0.0, "max": 15.0, "typical": 5.0},
            "travel": {"min": 1.0, "max": 5.0, "typical": 2.5},
            "supplies": {"min": 10.0, "max": 25.0, "typical": 15.0},
            "consultants": {"min": 0.0, "max": 20.0, "typical": 5.0},
            "other": {"min": 0.0, "max": 10.0, "typical": 5.0},
        },
        notes=[
            "Modular budget for requests up to $250K direct costs/year",
            "Detailed budget required for requests over $250K",
            "Personnel typically the largest category",
            "Equipment needs strong justification",
        ],
        validation_rules=[
            {
                "rule": "max_annual_direct_costs",
                "value": 500000,
                "message": "Annual direct costs should not exceed $500K for standard R01",
            },
            {
                "rule": "personnel_minimum",
                "value": 40.0,
                "message": "Personnel costs are typically at least 40% of direct costs",
            },
        ],
    ),
    "R21": MechanismBudgetTemplate(
        mechanism_code="R21",
        mechanism_name="Exploratory/Developmental Research Grant",
        agency="NIH",
        typical_annual_budget_min=100000,
        typical_annual_budget_max=275000,
        typical_duration_years=2,
        modular_budget=True,
        modular_increment=25000,
        max_annual_direct=275000,
        category_allocations={
            "personnel": {"min": 45.0, "max": 75.0, "typical": 60.0},
            "equipment": {"min": 0.0, "max": 20.0, "typical": 8.0},
            "travel": {"min": 1.0, "max": 5.0, "typical": 2.0},
            "supplies": {"min": 15.0, "max": 35.0, "typical": 20.0},
            "consultants": {"min": 0.0, "max": 15.0, "typical": 5.0},
            "other": {"min": 0.0, "max": 10.0, "typical": 5.0},
        },
        notes=[
            "Total budget capped at $275K over 2 years",
            "No preliminary data required",
            "Focus on novel, untested ideas",
            "Cannot request renewal of R21",
        ],
        validation_rules=[
            {
                "rule": "max_total_direct_costs",
                "value": 275000,
                "message": "Total direct costs cannot exceed $275K over 2 years",
            },
            {"rule": "max_duration_years", "value": 2, "message": "R21 maximum duration is 2 years"},
        ],
    ),
    "R03": MechanismBudgetTemplate(
        mechanism_code="R03",
        mechanism_name="Small Grant Program",
        agency="NIH",
        typical_annual_budget_min=50000,
        typical_annual_budget_max=100000,
        typical_duration_years=2,
        modular_budget=True,
        modular_increment=25000,
        max_annual_direct=50000,
        category_allocations={
            "personnel": {"min": 40.0, "max": 70.0, "typical": 55.0},
            "equipment": {"min": 0.0, "max": 15.0, "typical": 5.0},
            "travel": {"min": 1.0, "max": 5.0, "typical": 2.0},
            "supplies": {"min": 15.0, "max": 40.0, "typical": 25.0},
            "consultants": {"min": 0.0, "max": 10.0, "typical": 3.0},
            "other": {"min": 0.0, "max": 15.0, "typical": 10.0},
        },
        notes=[
            "Total budget capped at $100K over 2 years",
            "Suitable for pilot studies or small discrete projects",
            "Cannot request renewal of R03",
        ],
        validation_rules=[
            {"rule": "max_annual_direct_costs", "value": 50000, "message": "Annual direct costs cannot exceed $50K"},
            {
                "rule": "max_total_direct_costs",
                "value": 100000,
                "message": "Total direct costs cannot exceed $100K over 2 years",
            },
        ],
    ),
    "K01": MechanismBudgetTemplate(
        mechanism_code="K01",
        mechanism_name="Mentored Research Scientist Development Award",
        agency="NIH",
        typical_annual_budget_min=150000,
        typical_annual_budget_max=200000,
        typical_duration_years=5,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 70.0, "max": 90.0, "typical": 80.0},
            "equipment": {"min": 0.0, "max": 5.0, "typical": 2.0},
            "travel": {"min": 2.0, "max": 8.0, "typical": 4.0},
            "supplies": {"min": 5.0, "max": 15.0, "typical": 8.0},
            "consultants": {"min": 0.0, "max": 5.0, "typical": 2.0},
            "other": {"min": 0.0, "max": 8.0, "typical": 4.0},
        },
        notes=[
            "Salary support is primary component (up to 75% effort)",
            "Research costs capped at $50K/year",
            "Requires 75% protected time for research",
            "Cannot hold R01 simultaneously",
        ],
        validation_rules=[
            {
                "rule": "max_research_costs",
                "value": 50000,
                "message": "Research costs capped at $50K/year for K awards",
            },
            {"rule": "min_effort", "value": 75.0, "message": "K awards require minimum 75% effort"},
        ],
    ),
    "K99/R00": MechanismBudgetTemplate(
        mechanism_code="K99/R00",
        mechanism_name="Pathway to Independence Award",
        agency="NIH",
        typical_annual_budget_min=90000,
        typical_annual_budget_max=249000,
        typical_duration_years=5,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=249000,
        category_allocations={
            "personnel": {"min": 65.0, "max": 85.0, "typical": 75.0},
            "equipment": {"min": 0.0, "max": 10.0, "typical": 5.0},
            "travel": {"min": 2.0, "max": 6.0, "typical": 3.0},
            "supplies": {"min": 5.0, "max": 20.0, "typical": 12.0},
            "consultants": {"min": 0.0, "max": 5.0, "typical": 2.0},
            "other": {"min": 0.0, "max": 5.0, "typical": 3.0},
        },
        notes=[
            "K99 phase: 1-2 years mentored, up to $90K/year research",
            "R00 phase: 3 years independent, up to $249K/year",
            "Must transition to independent position to activate R00",
            "For late-stage postdocs ready for faculty positions",
        ],
        validation_rules=[
            {"rule": "k99_max_research", "value": 90000, "message": "K99 phase research costs capped at $90K/year"},
            {"rule": "r00_max_direct", "value": 249000, "message": "R00 phase direct costs capped at $249K/year"},
        ],
    ),
    "F31": MechanismBudgetTemplate(
        mechanism_code="F31",
        mechanism_name="Predoctoral Fellowship",
        agency="NIH",
        typical_annual_budget_min=40000,
        typical_annual_budget_max=60000,
        typical_duration_years=3,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 80.0, "max": 95.0, "typical": 90.0},
            "travel": {"min": 0.0, "max": 5.0, "typical": 2.0},
            "supplies": {"min": 0.0, "max": 10.0, "typical": 5.0},
            "other": {"min": 0.0, "max": 10.0, "typical": 3.0},
        },
        notes=[
            "Stipend set by NIH (currently ~$28K/year)",
            "Includes tuition and fees allowance",
            "Institutional allowance for supplies, travel",
            "No equipment or consultant costs typically allowed",
        ],
        validation_rules=[
            {"rule": "max_duration_years", "value": 5, "message": "F31 maximum duration is 5 years"},
        ],
    ),
    "F32": MechanismBudgetTemplate(
        mechanism_code="F32",
        mechanism_name="Postdoctoral Fellowship",
        agency="NIH",
        typical_annual_budget_min=60000,
        typical_annual_budget_max=80000,
        typical_duration_years=3,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 85.0, "max": 95.0, "typical": 90.0},
            "travel": {"min": 0.0, "max": 5.0, "typical": 2.0},
            "supplies": {"min": 0.0, "max": 10.0, "typical": 5.0},
            "other": {"min": 0.0, "max": 5.0, "typical": 3.0},
        },
        notes=[
            "Stipend based on years of postdoc experience",
            "Includes institutional allowance",
            "Travel to one scientific meeting per year typical",
            "No indirect costs on fellowships",
        ],
        validation_rules=[
            {"rule": "max_duration_years", "value": 3, "message": "F32 maximum duration is 3 years"},
        ],
    ),
    "T32": MechanismBudgetTemplate(
        mechanism_code="T32",
        mechanism_name="Training Grant",
        agency="NIH",
        typical_annual_budget_min=200000,
        typical_annual_budget_max=500000,
        typical_duration_years=5,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 75.0, "max": 90.0, "typical": 85.0},
            "travel": {"min": 1.0, "max": 5.0, "typical": 3.0},
            "supplies": {"min": 2.0, "max": 10.0, "typical": 5.0},
            "other": {"min": 2.0, "max": 10.0, "typical": 7.0},
        },
        notes=[
            "Supports predoctoral and/or postdoctoral trainees",
            "Includes stipends, tuition, trainee travel",
            "8% F&A rate for training grants",
            "Requires institutional commitment",
        ],
        validation_rules=[
            {"rule": "max_fa_rate", "value": 8.0, "message": "Training grants are limited to 8% F&A rate"},
        ],
    ),
    "P01": MechanismBudgetTemplate(
        mechanism_code="P01",
        mechanism_name="Program Project Grant",
        agency="NIH",
        typical_annual_budget_min=500000,
        typical_annual_budget_max=2500000,
        typical_duration_years=5,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 50.0, "max": 75.0, "typical": 60.0},
            "equipment": {"min": 0.0, "max": 15.0, "typical": 8.0},
            "travel": {"min": 1.0, "max": 5.0, "typical": 3.0},
            "supplies": {"min": 10.0, "max": 25.0, "typical": 15.0},
            "consultants": {"min": 0.0, "max": 15.0, "typical": 5.0},
            "other": {"min": 2.0, "max": 15.0, "typical": 9.0},
        },
        notes=[
            "Multi-component, multi-investigator program",
            "Requires Administrative Core",
            "Multiple interrelated projects",
            "Significant preliminary data required",
        ],
        validation_rules=[
            {"rule": "min_projects", "value": 3, "message": "P01 requires at least 3 interrelated projects"},
        ],
    ),
    "U01": MechanismBudgetTemplate(
        mechanism_code="U01",
        mechanism_name="Research Project Cooperative Agreement",
        agency="NIH",
        typical_annual_budget_min=300000,
        typical_annual_budget_max=1000000,
        typical_duration_years=5,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 50.0, "max": 75.0, "typical": 60.0},
            "equipment": {"min": 0.0, "max": 15.0, "typical": 5.0},
            "travel": {"min": 2.0, "max": 8.0, "typical": 5.0},
            "supplies": {"min": 10.0, "max": 25.0, "typical": 15.0},
            "consultants": {"min": 0.0, "max": 20.0, "typical": 8.0},
            "other": {"min": 2.0, "max": 12.0, "typical": 7.0},
        },
        notes=[
            "Cooperative agreement with NIH involvement",
            "Usually part of a larger consortium",
            "Travel for consortium meetings required",
            "NIH program staff have substantial involvement",
        ],
        validation_rules=[],
    ),
}

# NSF Mechanism Templates
NSF_BUDGET_TEMPLATES = {
    "CAREER": MechanismBudgetTemplate(
        mechanism_code="CAREER",
        mechanism_name="Faculty Early Career Development Program",
        agency="NSF",
        typical_annual_budget_min=100000,
        typical_annual_budget_max=500000,
        typical_duration_years=5,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 45.0, "max": 70.0, "typical": 55.0},
            "equipment": {"min": 0.0, "max": 20.0, "typical": 10.0},
            "travel": {"min": 2.0, "max": 8.0, "typical": 5.0},
            "supplies": {"min": 10.0, "max": 25.0, "typical": 15.0},
            "consultants": {"min": 0.0, "max": 10.0, "typical": 3.0},
            "other": {"min": 5.0, "max": 20.0, "typical": 12.0},
        },
        notes=[
            "Must be untenured faculty within first 7 years",
            "Requires education/outreach component",
            "Minimum 5-year duration",
            "Budgets vary by directorate ($400K-$500K typical)",
        ],
        validation_rules=[
            {"rule": "min_duration_years", "value": 5, "message": "CAREER awards require minimum 5-year duration"},
            {
                "rule": "requires_education",
                "value": True,
                "message": "CAREER awards require education/outreach component",
            },
        ],
    ),
    "STANDARD": MechanismBudgetTemplate(
        mechanism_code="STANDARD",
        mechanism_name="Standard Grant",
        agency="NSF",
        typical_annual_budget_min=50000,
        typical_annual_budget_max=300000,
        typical_duration_years=3,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 40.0, "max": 70.0, "typical": 55.0},
            "equipment": {"min": 0.0, "max": 25.0, "typical": 10.0},
            "travel": {"min": 2.0, "max": 8.0, "typical": 4.0},
            "supplies": {"min": 10.0, "max": 30.0, "typical": 18.0},
            "consultants": {"min": 0.0, "max": 15.0, "typical": 5.0},
            "other": {"min": 2.0, "max": 15.0, "typical": 8.0},
        },
        notes=[
            "Most common NSF research grant type",
            "Budget varies significantly by directorate",
            "Typically 2-5 years duration",
            "Check specific program for budget guidance",
        ],
        validation_rules=[],
    ),
    "EAGER": MechanismBudgetTemplate(
        mechanism_code="EAGER",
        mechanism_name="Early-concept Grants for Exploratory Research",
        agency="NSF",
        typical_annual_budget_min=100000,
        typical_annual_budget_max=300000,
        typical_duration_years=2,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 45.0, "max": 70.0, "typical": 55.0},
            "equipment": {"min": 0.0, "max": 20.0, "typical": 8.0},
            "travel": {"min": 1.0, "max": 5.0, "typical": 3.0},
            "supplies": {"min": 15.0, "max": 35.0, "typical": 22.0},
            "consultants": {"min": 0.0, "max": 10.0, "typical": 4.0},
            "other": {"min": 2.0, "max": 12.0, "typical": 8.0},
        },
        notes=[
            "High-risk, high-reward exploratory research",
            "Total budget capped at $300K",
            "Maximum 2 years duration",
            "Requires program officer invitation/approval",
        ],
        validation_rules=[
            {"rule": "max_total_budget", "value": 300000, "message": "EAGER grants capped at $300K total"},
            {"rule": "max_duration_years", "value": 2, "message": "EAGER grants maximum 2 years"},
        ],
    ),
    "RAPID": MechanismBudgetTemplate(
        mechanism_code="RAPID",
        mechanism_name="Rapid Response Research",
        agency="NSF",
        typical_annual_budget_min=50000,
        typical_annual_budget_max=200000,
        typical_duration_years=1,
        modular_budget=False,
        modular_increment=None,
        max_annual_direct=None,
        category_allocations={
            "personnel": {"min": 40.0, "max": 65.0, "typical": 50.0},
            "equipment": {"min": 0.0, "max": 25.0, "typical": 12.0},
            "travel": {"min": 5.0, "max": 20.0, "typical": 12.0},
            "supplies": {"min": 15.0, "max": 35.0, "typical": 18.0},
            "consultants": {"min": 0.0, "max": 10.0, "typical": 3.0},
            "other": {"min": 2.0, "max": 10.0, "typical": 5.0},
        },
        notes=[
            "Time-sensitive research opportunities",
            "Total budget capped at $200K",
            "Maximum 1 year duration",
            "Requires program officer approval",
            "Higher travel costs typical for field research",
        ],
        validation_rules=[
            {"rule": "max_total_budget", "value": 200000, "message": "RAPID grants capped at $200K total"},
            {"rule": "max_duration_years", "value": 1, "message": "RAPID grants maximum 1 year"},
        ],
    ),
}

# Combined templates
ALL_BUDGET_TEMPLATES = {**NIH_BUDGET_TEMPLATES, **NSF_BUDGET_TEMPLATES}


# =============================================================================
# Budget Generation Service
# =============================================================================


class BudgetTemplateService:
    """Service for generating and validating budget templates."""

    def __init__(self):
        self.templates = ALL_BUDGET_TEMPLATES
        self.salary_caps = NIH_SALARY_CAPS
        self.fa_rates = DEFAULT_FA_RATES
        self.fringe_rates = DEFAULT_FRINGE_RATES

    def get_template(self, mechanism_code: str) -> Optional[MechanismBudgetTemplate]:
        """Get budget template for a mechanism."""
        return self.templates.get(mechanism_code.upper())

    def get_all_templates(self) -> dict[str, MechanismBudgetTemplate]:
        """Get all available budget templates."""
        return self.templates

    def get_templates_by_agency(self, agency: str) -> dict[str, MechanismBudgetTemplate]:
        """Get templates filtered by agency."""
        return {
            code: template for code, template in self.templates.items() if template.agency.upper() == agency.upper()
        }

    def get_salary_cap(self, fiscal_year: int = 2024, agency: str = "NIH") -> Optional[SalaryCapInfo]:
        """Get salary cap for a fiscal year."""
        return self.salary_caps.get(fiscal_year)

    def get_fa_rate(self, rate_type: str = "default") -> float:
        """Get F&A rate by type."""
        return self.fa_rates.get(rate_type, self.fa_rates["default"])

    def get_fringe_rate(self, employee_type: str = "default") -> float:
        """Get fringe benefit rate by employee type."""
        return self.fringe_rates.get(employee_type, self.fringe_rates["default"])

    def generate_budget_breakdown(
        self,
        mechanism_code: str,
        total_direct_costs: int,
        duration_years: int = 1,
        fa_rate: Optional[float] = None,
        custom_allocations: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        """
        Generate a budget breakdown based on mechanism template.

        Args:
            mechanism_code: Grant mechanism code (e.g., 'R01', 'CAREER')
            total_direct_costs: Total direct costs for the period
            duration_years: Number of years for the budget
            fa_rate: Custom F&A rate (uses default if not provided)
            custom_allocations: Custom category allocations (uses template if not provided)

        Returns:
            Dictionary with detailed budget breakdown
        """
        template = self.get_template(mechanism_code)
        if not template:
            return self._generate_generic_budget(total_direct_costs, duration_years, fa_rate)

        # Use custom allocations or template defaults
        allocations = custom_allocations or {
            cat: data["typical"] for cat, data in template.category_allocations.items()
        }

        # Normalize allocations to 100%
        total_allocation = sum(allocations.values())
        if total_allocation != 100.0:
            factor = 100.0 / total_allocation
            allocations = {k: v * factor for k, v in allocations.items()}

        # Calculate amounts per category
        annual_direct = total_direct_costs / duration_years
        categories = {}

        for category, percentage in allocations.items():
            amount = int(total_direct_costs * (percentage / 100.0))
            annual_amount = int(annual_direct * (percentage / 100.0))
            categories[category] = {
                "percentage": round(percentage, 1),
                "total_amount": amount,
                "annual_amount": annual_amount,
                "typical_range": template.category_allocations.get(category, {}),
            }

        # Calculate F&A costs
        effective_fa_rate = fa_rate if fa_rate is not None else self.get_fa_rate()

        # Calculate MTDC (Modified Total Direct Costs) - typically excludes equipment, tuition, subawards over $25K
        equipment_amount = categories.get("equipment", {}).get("total_amount", 0)
        mtdc = total_direct_costs - equipment_amount  # Simplified MTDC calculation
        indirect_costs = int(mtdc * effective_fa_rate)

        return {
            "mechanism": mechanism_code,
            "mechanism_name": template.mechanism_name,
            "agency": template.agency,
            "total_direct_costs": total_direct_costs,
            "annual_direct_costs": int(annual_direct),
            "duration_years": duration_years,
            "categories": categories,
            "fa_rate": round(effective_fa_rate * 100, 1),
            "mtdc": mtdc,
            "indirect_costs": indirect_costs,
            "total_budget": total_direct_costs + indirect_costs,
            "annual_total_budget": int((total_direct_costs + indirect_costs) / duration_years),
            "notes": template.notes,
            "modular_budget": template.modular_budget,
            "modular_increment": template.modular_increment,
        }

    def _generate_generic_budget(
        self,
        total_direct_costs: int,
        duration_years: int,
        fa_rate: Optional[float],
    ) -> dict[str, Any]:
        """Generate a generic budget when no template exists."""
        # Default allocations
        allocations = {
            "personnel": 60.0,
            "equipment": 5.0,
            "travel": 3.0,
            "supplies": 18.0,
            "consultants": 5.0,
            "other": 9.0,
        }

        annual_direct = total_direct_costs / duration_years
        categories = {}

        for category, percentage in allocations.items():
            amount = int(total_direct_costs * (percentage / 100.0))
            annual_amount = int(annual_direct * (percentage / 100.0))
            categories[category] = {
                "percentage": percentage,
                "total_amount": amount,
                "annual_amount": annual_amount,
            }

        effective_fa_rate = fa_rate if fa_rate is not None else self.get_fa_rate()
        equipment_amount = categories.get("equipment", {}).get("total_amount", 0)
        mtdc = total_direct_costs - equipment_amount
        indirect_costs = int(mtdc * effective_fa_rate)

        return {
            "mechanism": "GENERIC",
            "mechanism_name": "Generic Budget Template",
            "agency": "N/A",
            "total_direct_costs": total_direct_costs,
            "annual_direct_costs": int(annual_direct),
            "duration_years": duration_years,
            "categories": categories,
            "fa_rate": round(effective_fa_rate * 100, 1),
            "mtdc": mtdc,
            "indirect_costs": indirect_costs,
            "total_budget": total_direct_costs + indirect_costs,
            "annual_total_budget": int((total_direct_costs + indirect_costs) / duration_years),
            "notes": ["Generic template - check specific program guidelines for budget requirements"],
            "modular_budget": False,
            "modular_increment": None,
        }

    def validate_budget(
        self,
        mechanism_code: str,
        budget_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate a budget against mechanism rules.

        Args:
            mechanism_code: Grant mechanism code
            budget_data: Budget to validate

        Returns:
            Dictionary with validation results and any warnings/errors
        """
        template = self.get_template(mechanism_code)
        errors = []
        warnings = []

        total_direct = budget_data.get("total_direct_costs", 0)
        duration_years = budget_data.get("duration_years", 1)
        categories = budget_data.get("categories", {})

        # Calculate annual direct costs
        annual_direct = total_direct / duration_years if duration_years > 0 else total_direct

        if template:
            # Check against template validation rules
            for rule in template.validation_rules:
                rule_type = rule.get("rule", "")
                value = rule.get("value")
                message = rule.get("message", "")

                if rule_type == "max_annual_direct_costs" and annual_direct > value:
                    errors.append(
                        {
                            "rule": rule_type,
                            "message": message,
                            "expected": value,
                            "actual": annual_direct,
                        }
                    )
                elif rule_type == "max_total_direct_costs" and total_direct > value:
                    errors.append(
                        {
                            "rule": rule_type,
                            "message": message,
                            "expected": value,
                            "actual": total_direct,
                        }
                    )
                elif rule_type == "max_duration_years" and duration_years > value:
                    errors.append(
                        {
                            "rule": rule_type,
                            "message": message,
                            "expected": value,
                            "actual": duration_years,
                        }
                    )
                elif rule_type == "personnel_minimum":
                    personnel_pct = categories.get("personnel", {}).get("percentage", 0)
                    if personnel_pct < value:
                        warnings.append(
                            {
                                "rule": rule_type,
                                "message": message,
                                "expected": value,
                                "actual": personnel_pct,
                            }
                        )

            # Check category allocations against typical ranges
            for category, alloc_data in template.category_allocations.items():
                if category in categories:
                    actual_pct = categories[category].get("percentage", 0)
                    if actual_pct < alloc_data.get("min", 0):
                        warnings.append(
                            {
                                "category": category,
                                "message": f"{category.title()} allocation ({actual_pct}%) is below typical minimum ({alloc_data['min']}%)",
                                "expected_min": alloc_data["min"],
                                "actual": actual_pct,
                            }
                        )
                    elif actual_pct > alloc_data.get("max", 100):
                        warnings.append(
                            {
                                "category": category,
                                "message": f"{category.title()} allocation ({actual_pct}%) exceeds typical maximum ({alloc_data['max']}%)",
                                "expected_max": alloc_data["max"],
                                "actual": actual_pct,
                            }
                        )

        # General validations
        total_percentage = sum(cat_data.get("percentage", 0) for cat_data in categories.values())
        if abs(total_percentage - 100.0) > 0.5:
            errors.append(
                {
                    "rule": "total_percentage",
                    "message": f"Category percentages should sum to 100% (currently {total_percentage:.1f}%)",
                    "expected": 100.0,
                    "actual": total_percentage,
                }
            )

        # Check salary cap
        salary_cap = self.get_salary_cap()
        if salary_cap:
            personnel_amount = categories.get("personnel", {}).get("annual_amount", 0)
            if personnel_amount > salary_cap.cap_amount * 1.5:  # Rough check for reasonableness
                warnings.append(
                    {
                        "rule": "salary_cap",
                        "message": f"Personnel costs may exceed salary cap limits (NIH cap: ${salary_cap.cap_amount:,})",
                        "salary_cap": salary_cap.cap_amount,
                    }
                )

        return {
            "is_valid": len(errors) == 0,
            "mechanism": mechanism_code,
            "errors": errors,
            "warnings": warnings,
            "template_notes": template.notes if template else [],
        }


# Singleton service instance
budget_template_service = BudgetTemplateService()
