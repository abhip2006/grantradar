"""
Seed Budget Templates Script
Seeds typical budget allocations for NIH and NSF mechanisms into the database.

Run this script to populate the budget_templates table with initial data.

Usage:
    python -m backend.scripts.seed_budget_templates
"""
import asyncio
import json
import logging
from uuid import uuid4

from backend.database import get_async_session
from backend.services.budget_templates import (
    ALL_BUDGET_TEMPLATES,
    BUDGET_CATEGORIES,
    NIH_SALARY_CAPS,
    DEFAULT_FA_RATES,
    DEFAULT_FRINGE_RATES,
    BudgetCategory,
)

logger = logging.getLogger(__name__)


# NIH Salary Cap (Executive Level II) - 2024
NIH_SALARY_CAP_2024 = 221900  # As of January 2024

# Typical F&A rates
FA_RATE_GUIDANCE = {
    "research_on_campus": 0.52,  # 50-55% typical for on-campus research
    "research_off_campus": 0.26,  # ~26% for off-campus
    "training": 0.08,  # 8% for training grants (T32, etc.)
}


# Budget template seed data organized by mechanism
BUDGET_TEMPLATE_SEED_DATA = []

# Generate seed data from the service templates
for mechanism_code, template in ALL_BUDGET_TEMPLATES.items():
    for category, allocations in template.category_allocations.items():
        typical_pct = allocations.get("typical", 0)
        min_pct = allocations.get("min", 0)
        max_pct = allocations.get("max", 100)

        # Calculate typical amounts based on template budget ranges
        avg_annual = (template.typical_annual_budget_min + template.typical_annual_budget_max) / 2
        typical_amount = int(avg_annual * (typical_pct / 100))
        min_amount = int(template.typical_annual_budget_min * (min_pct / 100))
        max_amount = int(template.typical_annual_budget_max * (max_pct / 100))

        # Category-specific notes
        notes = None
        if category == "personnel":
            notes = f"Includes PI, Co-Is, postdocs, graduate students, staff. Subject to NIH salary cap (${NIH_SALARY_CAP_2024:,} for 2024)."
        elif category == "equipment":
            notes = "Items >= $5,000 with useful life > 1 year. Excluded from MTDC for F&A calculation."
        elif category == "travel":
            notes = "Domestic and international travel for conferences, collaborations, field work."
        elif category == "supplies":
            notes = "Consumables, chemicals, reagents, software licenses, publication costs."
        elif category == "consultants":
            notes = "Consultant fees, subcontracts. First $25K of each subaward included in MTDC."
        elif category == "other":
            notes = "Participant support, animal care, human subjects costs, service center charges."

        BUDGET_TEMPLATE_SEED_DATA.append({
            "mechanism_code": mechanism_code,
            "category": category,
            "typical_percentage": typical_pct,
            "typical_amount_min": min_amount,
            "typical_amount_max": max_amount,
            "is_required": category == "personnel",  # Personnel is typically required
            "priority": {
                "personnel": 1,
                "supplies": 2,
                "equipment": 3,
                "travel": 4,
                "consultants": 5,
                "other": 6,
            }.get(category, 10),
            "notes": notes,
            "validation_rules": {
                "min_percentage": min_pct,
                "max_percentage": max_pct,
            } if min_pct > 0 or max_pct < 100 else None,
        })


async def seed_budget_templates():
    """Seed budget template data into the database."""
    async with get_async_session() as session:
        from sqlalchemy import text

        # Check if data already exists
        result = await session.execute(
            text("SELECT COUNT(*) FROM budget_templates")
        )
        count = result.scalar()

        if count and count > 0:
            logger.info(f"Budget templates table already has {count} records. Skipping seed.")
            return

        logger.info(f"Seeding {len(BUDGET_TEMPLATE_SEED_DATA)} budget template records...")

        # Insert each template
        for template_data in BUDGET_TEMPLATE_SEED_DATA:
            await session.execute(
                text("""
                    INSERT INTO budget_templates (
                        id, mechanism_code, category, typical_percentage,
                        typical_amount_min, typical_amount_max, is_required,
                        priority, notes, validation_rules, created_at, updated_at
                    ) VALUES (
                        :id, :mechanism_code, :category, :typical_percentage,
                        :typical_amount_min, :typical_amount_max, :is_required,
                        :priority, :notes, :validation_rules, NOW(), NOW()
                    )
                """),
                {
                    "id": str(uuid4()),
                    "mechanism_code": template_data["mechanism_code"],
                    "category": template_data["category"],
                    "typical_percentage": template_data["typical_percentage"],
                    "typical_amount_min": template_data["typical_amount_min"],
                    "typical_amount_max": template_data["typical_amount_max"],
                    "is_required": template_data["is_required"],
                    "priority": template_data["priority"],
                    "notes": template_data["notes"],
                    "validation_rules": json.dumps(template_data["validation_rules"]) if template_data["validation_rules"] else None,
                }
            )

        await session.commit()
        logger.info("Budget templates seeded successfully!")

        # Print summary
        print("\n" + "=" * 60)
        print("Budget Templates Seed Summary")
        print("=" * 60)
        print(f"\nTotal templates seeded: {len(BUDGET_TEMPLATE_SEED_DATA)}")

        # Group by mechanism
        mechanisms = {}
        for t in BUDGET_TEMPLATE_SEED_DATA:
            mech = t["mechanism_code"]
            if mech not in mechanisms:
                mechanisms[mech] = []
            mechanisms[mech].append(t["category"])

        print("\nMechanisms covered:")
        for mech, categories in sorted(mechanisms.items()):
            print(f"  - {mech}: {', '.join(sorted(categories))}")

        print("\n" + "-" * 60)
        print("NIH Salary Cap Reference:")
        for year, cap_info in sorted(NIH_SALARY_CAPS.items(), reverse=True):
            print(f"  {year}: ${cap_info.cap_amount:,} ({cap_info.notes})")

        print("\nF&A Rate Guidance:")
        for rate_type, rate in FA_RATE_GUIDANCE.items():
            print(f"  {rate_type}: {rate * 100:.0f}%")

        print("\nFringe Benefit Rates (typical):")
        for emp_type, rate in DEFAULT_FRINGE_RATES.items():
            print(f"  {emp_type}: {rate * 100:.0f}%")

        print("=" * 60 + "\n")


async def clear_budget_templates():
    """Clear all budget template data (for testing)."""
    async with get_async_session() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM budget_templates"))
        await session.commit()
        logger.info("Budget templates cleared.")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed budget templates")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.clear:
        await clear_budget_templates()

    await seed_budget_templates()


if __name__ == "__main__":
    asyncio.run(main())
