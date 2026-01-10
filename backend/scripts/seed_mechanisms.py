"""
Seed Grant Mechanisms Data
Populates the grant_mechanisms table with NIH and NSF mechanism information.

This script seeds the grant_mechanisms table with real data about grant mechanisms
(R01, R21, K awards, etc.) including success rates, typical budgets, and competition
levels based on published NIH and NSF statistics.

Usage:
    python -m backend.scripts.seed_mechanisms
"""

import asyncio
import uuid
from datetime import datetime, timezone

# Mechanism data based on NIH/NSF published statistics
MECHANISMS_DATA = [
    # NIH Research Grants
    {
        "code": "R01",
        "name": "Research Project Grant",
        "description": "The R01 is the original and historically oldest grant mechanism used by NIH. It provides support for health-related research and development.",
        "funding_agency": "NIH",
        "category": "research",
        "typical_duration_months": 60,
        "typical_budget_min": 250000,
        "typical_budget_max": 500000,
        "success_rate_overall": 0.21,
        "success_rate_new": 0.19,
        "success_rate_renewal": 0.35,
        "success_rate_resubmission": 0.32,
        "competition_level": "high",
        "estimated_applicants_per_cycle": 8000,
        "review_criteria": {"significance": 1, "investigators": 2, "innovation": 3, "approach": 4, "environment": 5},
        "tips": [
            "Include strong preliminary data",
            "Clearly state specific aims in 1 page",
            "Budget justification must align with aims",
            "Address potential pitfalls and alternatives",
        ],
    },
    {
        "code": "R21",
        "name": "Exploratory/Developmental Research Grant",
        "description": "The R21 provides support for early and conceptual stages of project development. Limited to 2 years and $275K total costs.",
        "funding_agency": "NIH",
        "category": "research",
        "typical_duration_months": 24,
        "typical_budget_min": 150000,
        "typical_budget_max": 275000,
        "success_rate_overall": 0.18,
        "success_rate_new": 0.17,
        "success_rate_resubmission": 0.25,
        "competition_level": "high",
        "estimated_applicants_per_cycle": 4000,
        "review_criteria": {"significance": 1, "investigators": 2, "innovation": 3, "approach": 4, "environment": 5},
        "tips": [
            "Focus on high-risk, high-reward ideas",
            "Preliminary data not required but helpful",
            "Emphasize innovation and novelty",
        ],
    },
    {
        "code": "R03",
        "name": "Small Grant Program",
        "description": "The R03 provides limited funding for small research projects such as pilot studies, feasibility studies, and secondary data analysis.",
        "funding_agency": "NIH",
        "category": "research",
        "typical_duration_months": 24,
        "typical_budget_min": 50000,
        "typical_budget_max": 100000,
        "success_rate_overall": 0.25,
        "success_rate_new": 0.24,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 1500,
        "tips": ["Good for new investigators building track record", "Focus on feasibility and pilot data collection"],
    },
    {
        "code": "R15",
        "name": "Academic Research Enhancement Award (AREA)",
        "description": "Provides support for research at institutions not receiving substantial federal research support, particularly minority institutions and Hispanic-serving institutions.",
        "funding_agency": "NIH",
        "category": "research",
        "typical_duration_months": 36,
        "typical_budget_min": 150000,
        "typical_budget_max": 200000,
        "success_rate_overall": 0.28,
        "success_rate_new": 0.27,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 800,
        "tips": [
            "Eligibility limited to specific institution types",
            "Good for building research infrastructure",
            "Requires faculty mentoring component for students",
        ],
    },
    # Career Development Awards
    {
        "code": "K01",
        "name": "Mentored Research Scientist Development Award",
        "description": "Provides support for an intensive, supervised career development experience in biomedical, behavioral, or clinical research.",
        "funding_agency": "NIH",
        "category": "career",
        "typical_duration_months": 60,
        "typical_budget_min": 100000,
        "typical_budget_max": 150000,
        "success_rate_overall": 0.35,
        "success_rate_new": 0.33,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 800,
        "tips": [
            "Strong mentor and mentoring plan essential",
            "Clear career development trajectory",
            "75% protected time required",
        ],
    },
    {
        "code": "K08",
        "name": "Mentored Clinical Scientist Development Award",
        "description": "Provides support for the development of outstanding clinician research scientists.",
        "funding_agency": "NIH",
        "category": "career",
        "typical_duration_months": 60,
        "typical_budget_min": 100000,
        "typical_budget_max": 150000,
        "success_rate_overall": 0.38,
        "success_rate_new": 0.36,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 600,
        "tips": ["Must have clinical degree (MD, DO, etc.)", "Balance clinical and research training"],
    },
    {
        "code": "K23",
        "name": "Mentored Patient-Oriented Research Career Development Award",
        "description": "Provides support for the career development of investigators who have made a commitment to patient-oriented research.",
        "funding_agency": "NIH",
        "category": "career",
        "typical_duration_months": 60,
        "typical_budget_min": 100000,
        "typical_budget_max": 150000,
        "success_rate_overall": 0.40,
        "success_rate_new": 0.38,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 700,
        "tips": ["Focus on patient-oriented research", "Strong institutional support letter needed"],
    },
    {
        "code": "K99",
        "name": "Pathway to Independence Award",
        "description": "Provides support for postdocs to transition to independent faculty positions. Includes K99 (mentored) and R00 (independent) phases.",
        "funding_agency": "NIH",
        "category": "career",
        "typical_duration_months": 60,
        "typical_budget_min": 100000,
        "typical_budget_max": 250000,
        "success_rate_overall": 0.32,
        "success_rate_new": 0.30,
        "competition_level": "high",
        "estimated_applicants_per_cycle": 1200,
        "tips": [
            "Must be within 4 years of terminal degree",
            "Strong publication record expected",
            "Clear path to faculty position",
        ],
    },
    # Fellowship Awards
    {
        "code": "F31",
        "name": "Predoctoral Individual NRSA",
        "description": "Provides support for promising doctoral candidates who will be performing dissertation research and training in scientific health-related fields.",
        "funding_agency": "NIH",
        "category": "training",
        "typical_duration_months": 36,
        "typical_budget_min": 35000,
        "typical_budget_max": 50000,
        "success_rate_overall": 0.28,
        "success_rate_new": 0.26,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 2000,
        "tips": ["Focus on training plan and career goals", "Strong sponsor and institutional support"],
    },
    {
        "code": "F32",
        "name": "Postdoctoral Individual NRSA",
        "description": "Provides support for promising postdoctoral candidates who wish to pursue research training.",
        "funding_agency": "NIH",
        "category": "training",
        "typical_duration_months": 36,
        "typical_budget_min": 55000,
        "typical_budget_max": 70000,
        "success_rate_overall": 0.30,
        "success_rate_new": 0.28,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 1800,
        "tips": ["Emphasize career development goals", "Show how training complements PhD training"],
    },
    # NSF Programs
    {
        "code": "CAREER",
        "name": "Faculty Early Career Development Program",
        "description": "NSF's most prestigious award for early-career faculty who have potential to serve as academic role models in research and education.",
        "funding_agency": "NSF",
        "category": "research",
        "typical_duration_months": 60,
        "typical_budget_min": 400000,
        "typical_budget_max": 800000,
        "success_rate_overall": 0.18,
        "success_rate_new": 0.17,
        "competition_level": "very_high",
        "estimated_applicants_per_cycle": 3000,
        "tips": [
            "Must be in tenure-track position",
            "Strong integration of research and education",
            "Broader impacts are critical",
        ],
    },
    {
        "code": "Standard",
        "name": "NSF Standard Research Grant",
        "description": "Standard research grants supporting a broad range of scientific activities across NSF directorates.",
        "funding_agency": "NSF",
        "category": "research",
        "typical_duration_months": 36,
        "typical_budget_min": 150000,
        "typical_budget_max": 500000,
        "success_rate_overall": 0.25,
        "success_rate_new": 0.23,
        "competition_level": "medium",
        "estimated_applicants_per_cycle": 5000,
        "tips": ["Focus on intellectual merit and broader impacts", "Align with NSF program priorities"],
    },
    {
        "code": "SBIR/STTR",
        "name": "Small Business Innovation Research / Small Business Technology Transfer",
        "description": "NSF program supporting small businesses and partnerships with academic institutions for innovation and technology development.",
        "funding_agency": "NSF",
        "category": "research",
        "typical_duration_months": 24,
        "typical_budget_min": 150000,
        "typical_budget_max": 225000,
        "success_rate_overall": 0.15,
        "success_rate_new": 0.12,
        "competition_level": "very_high",
        "estimated_applicants_per_cycle": 2000,
        "tips": [
            "Small business eligibility requirements apply",
            "Focus on commercialization potential",
            "Phase I and II structure",
        ],
    },
]


async def seed_mechanisms():
    """Seed the grant_mechanisms table with mechanism data."""
    from backend.database import get_async_session
    from sqlalchemy import text
    import json

    async with get_async_session() as session:
        try:
            for mechanism in MECHANISMS_DATA:
                # Check if already exists
                result = await session.execute(
                    text("SELECT id FROM grant_mechanisms WHERE code = :code"), {"code": mechanism["code"]}
                )
                existing = result.fetchone()

                if existing:
                    print(f"Mechanism {mechanism['code']} already exists, skipping...")
                    continue

                # Insert new mechanism
                mechanism_id = uuid.uuid4()
                await session.execute(
                    text("""
                        INSERT INTO grant_mechanisms (
                            id, code, name, description, funding_agency, category,
                            typical_duration_months, typical_budget_min, typical_budget_max,
                            success_rate_overall, success_rate_new, success_rate_renewal,
                            success_rate_resubmission, competition_level,
                            estimated_applicants_per_cycle, review_criteria, tips,
                            last_updated, created_at
                        ) VALUES (
                            :id, :code, :name, :description, :funding_agency, :category,
                            :typical_duration_months, :typical_budget_min, :typical_budget_max,
                            :success_rate_overall, :success_rate_new, :success_rate_renewal,
                            :success_rate_resubmission, :competition_level,
                            :estimated_applicants_per_cycle, :review_criteria, :tips,
                            :last_updated, :created_at
                        )
                    """),
                    {
                        "id": mechanism_id,
                        "code": mechanism["code"],
                        "name": mechanism["name"],
                        "description": mechanism.get("description"),
                        "funding_agency": mechanism.get("funding_agency"),
                        "category": mechanism.get("category"),
                        "typical_duration_months": mechanism.get("typical_duration_months"),
                        "typical_budget_min": mechanism.get("typical_budget_min"),
                        "typical_budget_max": mechanism.get("typical_budget_max"),
                        "success_rate_overall": mechanism.get("success_rate_overall"),
                        "success_rate_new": mechanism.get("success_rate_new"),
                        "success_rate_renewal": mechanism.get("success_rate_renewal"),
                        "success_rate_resubmission": mechanism.get("success_rate_resubmission"),
                        "competition_level": mechanism.get("competition_level"),
                        "estimated_applicants_per_cycle": mechanism.get("estimated_applicants_per_cycle"),
                        "review_criteria": json.dumps(mechanism.get("review_criteria"))
                        if mechanism.get("review_criteria")
                        else None,
                        "tips": json.dumps(mechanism.get("tips")) if mechanism.get("tips") else None,
                        "last_updated": datetime.now(timezone.utc),
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                print(f"Inserted mechanism: {mechanism['code']} - {mechanism['name']}")

            await session.commit()
            print("\nSeed complete! Inserted mechanism data successfully.")

        except Exception as e:
            await session.rollback()
            print(f"Error seeding mechanisms: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_mechanisms())
